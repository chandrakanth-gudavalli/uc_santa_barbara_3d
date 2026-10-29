// UCSB in 3D: one Spark viewer, a catalog of scenes, and moves between them.
//
// Coordinates: every scene is in the same GPS frame, east-north-up metres (z up), so the camera keeps its pose
// across scenes and "Go down" / "Go up" land on the same spot. Each splat file holds its centres relative to an
// integer splat_origin (float16 precision); the mesh is placed back at that origin.
import * as THREE from "three";
import { SparkRenderer, SplatMesh, SparkControls } from "@sparkjsdev/spark";

const $ = (id) => document.getElementById(id);
const Z = new THREE.Vector3(0, 0, 1);
const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);
const MOVE_SPEED = { campus: 30, ground: 4, site: 12 };     // metres a second at 1x
// How far the camera may leave the photographs. The model is only trustworthy near where photos were taken:
//   near   - within REACH x the local photo spacing of a photo position, looking within NEAR_DEG of its direction
//   photos - standing exactly at a photo position, looking within PHOTO_DEG of its direction; step between photos
//   free   - anywhere
const MODES = ["photos", "near", "free"];
const REACH = 0.75, MIN_R = 1.0, MAX_R = 20, NEAR_DEG = 20, PHOTO_DEG = 10;
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

const catalog = await (await fetch("./scenes.json")).json();
const params = new URLSearchParams(location.search);
const assetBase = params.get("assets") || catalog.assetBase;
const byClip = Object.fromEntries(catalog.scenes.map((s) => [s.clip, s]));
const poseCache = {};
const loadPoses = (clip) => (poseCache[clip] ??= fetch(`./scenes/${clip}.json`).then((r) => r.json()));

// ---- renderer, camera, controls
const canvas = $("view");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x06141e);
// Level of detail: each scene's splats get an LoD tree, built in a background worker after download (`lod: true`), and
// Spark draws a per-device budget of them (1-1.5 M on phones), spent mostly in front of the camera (the cone
// settings). Building the tree adds ~12 s to a 3 M-splat load and a desktop GPU draws the full set as fast, so it is
// on for touch devices only; ?lod=1 / ?lod=0 forces it, ?detail=<x> scales the budget.
const LOD = params.has("lod") ? params.get("lod") !== "0" : matchMedia("(pointer: coarse)").matches;
const spark = new SparkRenderer({ renderer, lodSplatScale: parseFloat(params.get("detail")) || 1.0,
                                  coneFov0: 70, coneFov: 120, behindFoveate: 0.2, coneFoveate: 0.4 });
scene.add(spark);
const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 6000);
camera.up.copy(Z);
scene.add(camera);
const controls = new SparkControls({ canvas });

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

// ---- state
const state = { clip: null, poses: null, mesh: null, view: -1, tween: null, flight: null, nextFlight: null, speed: 1,
                loading: false, mode: MODES.includes(params.get("mode")) ? params.get("mode")
                  : (MODES.includes(store.get("ucsb3d.mode")) ? store.get("ucsb3d.mode") : "photos") };

function poseOf(fr) {
  const p = V(fr.c), f = V(fr.f);
  const up = Math.abs(f.z) > 0.97 ? V(fr.u) : Z;            // a straight-down drone photo: keep its own roll
  const d = new THREE.PerspectiveCamera(); d.up.copy(up); d.position.copy(p); d.lookAt(p.clone().add(f));
  return { p, q: d.quaternion.clone() };
}

function lookPose(eye, target) {
  const d = new THREE.PerspectiveCamera(); d.up.copy(Z); d.position.copy(eye); d.lookAt(target);
  return { p: eye.clone(), q: d.quaternion.clone() };
}

function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

function goTo(pose, seconds = 1.4) {
  stopFlight();
  state.tween = { p0: camera.position.clone(), q0: camera.quaternion.clone(), p1: pose.p, q1: pose.q,
                  t0: performance.now(), dur: seconds * 1000 };
}

// ---- scene geometry helpers
function centre(P) { return V(P.centre); }
function radius(P) {
  const c = centre(P);
  const d = P.frames.map((f) => Math.hypot(f.c[0] - c.x, f.c[1] - c.y)).sort((a, b) => a - b);
  return Math.max(d[Math.floor(d.length * 0.6)] || 30, 15);
}
function overviewPose(P, group) {
  const c = centre(P), R = radius(P);
  // from the south, about the drone's own height (or 0.6 R up for a walk): inside the captured area, not past it
  const lift = group === "ground" ? 0.6 * R + 8 : Math.max(0.55 * R, P.cam_height - c.z);
  return lookPose(new THREE.Vector3(c.x, c.y - 0.9 * R, c.z + lift), c);
}
function prepare(P) {
  // each photo's camera rotation, and how far from it the camera may go: REACH x the distance to its nearest
  // neighbour in the same band (a walk's photos are metres apart, a drone's tens of metres)
  if (P._q) return P;
  P._p = P.frames.map((f) => V(f.c));
  P._q = P.frames.map((f) => poseOf(f).q);
  const nn = P.frames.map((f, i) => {
    let d = Infinity;
    P.frames.forEach((g, j) => { if (j !== i && (g.e || "") === (f.e || "")) d = Math.min(d, P._p[i].distanceTo(P._p[j])); });
    return d;
  });
  const bands = {};
  P.frames.forEach((f, i) => (bands[f.e || ""] ??= []).push(nn[i]));
  const med = Object.fromEntries(Object.entries(bands).map(([b, v]) => [b, v.sort((a, c) => a - c)[v.length >> 1]]));
  P._r = P.frames.map((f) => Math.min(MAX_R, Math.max(MIN_R, REACH * med[f.e || ""])));
  return P;
}
function nearest3d(P, p) {
  let best = 0, bd = Infinity;
  for (let i = 0; i < P._p.length; i++) { const d = P._p[i].distanceToSquared(p); if (d < bd) { bd = d; best = i; } }
  return best;
}
function centralFrame(P) {
  // the overview in the restricted modes: the photo nearest the middle, from the air when there is a choice
  const c = centre(P), air = P.frames.some((f) => f.e === "air");
  return nearestFrame(P.frames, c, (f) => !air || f.e === "air").i;
}
const _fwd = new THREE.Vector3(), _ref = new THREE.Vector3(), _tmp = new THREE.Vector3(), _q = new THREE.Quaternion();
function constrain() {
  const P = state.poses; if (!P || state.mode === "free") return;
  const photos = state.mode === "photos";
  if (photos && state.view < 0) state.view = nearest3d(P, camera.position);
  const i = photos ? state.view : nearest3d(P, camera.position);
  // position: on the photo (photos), or back inside its reach (near)
  if (photos) camera.position.lerp(P._p[i], 0.5);
  else {
    _tmp.subVectors(camera.position, P._p[i]);
    const d = _tmp.length(), r = P._r[i];
    if (d > r) camera.position.lerp(_tmp.multiplyScalar(r / d).add(P._p[i]), 0.35);
  }
  // direction: back inside the cone round the photo's own direction
  const max = THREE.MathUtils.degToRad(photos ? PHOTO_DEG : NEAR_DEG);
  _fwd.set(0, 0, -1).applyQuaternion(camera.quaternion);
  _ref.set(0, 0, -1).applyQuaternion(P._q[i]);
  const ang = _fwd.angleTo(_ref);
  if (ang > max) { _q.copy(camera.quaternion).slerp(P._q[i], Math.min(1, (ang - max) / ang) * 0.35); camera.quaternion.copy(_q); }
}

function groundPointAhead() {
  // where the view's centre ray meets the ground under the current scene
  const f = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
  const gz = state.poses ? state.poses.centre[2] : 0;
  const p = camera.position;
  if (f.z < -0.05) { const t = (gz - p.z) / f.z; return new THREE.Vector3(p.x + f.x * t, p.y + f.y * t, gz); }
  return new THREE.Vector3(p.x + f.x * 30, p.y + f.y * 30, gz);
}

// ---- the flythrough: a smooth looping path, played when the page opens
const FLIGHT_SPEED = { campus: 12, site: 12, ground: 2.2 };   // metres a second at 1x
function flightPath(P, S) {
  const air = P.frames.filter((f) => f.e !== "ground");
  if (S.group !== "ground" && air.length) {
    // an oblique loop at the drone's height, inside the area its photos cover: an ellipse on the photo positions'
    // principal axes at 1.1 standard deviations, looking in and down at a smaller one on the ground
    const n = air.length, mx = air.reduce((a, f) => a + f.c[0], 0) / n, my = air.reduce((a, f) => a + f.c[1], 0) / n;
    let sxx = 0, syy = 0, sxy = 0;
    air.forEach((f) => { const dx = f.c[0] - mx, dy = f.c[1] - my; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; });
    sxx /= n; syy /= n; sxy /= n;
    const th = 0.5 * Math.atan2(2 * sxy, sxx - syy), tr = (sxx + syy) / 2, dd = Math.sqrt(((sxx - syy) / 2) ** 2 + sxy ** 2);
    const s1 = Math.sqrt(tr + dd), s2 = Math.sqrt(Math.max(tr - dd, 1));
    const e1 = [Math.cos(th), Math.sin(th)], e2 = [-Math.sin(th), Math.cos(th)];
    const z = air.map((f) => f.c[2]).sort((a, b) => a - b)[n >> 1], gz = P.centre[2];
    const ring = (k, sc, h) => { const a = (2 * Math.PI * k) / 12, u = sc * s1 * Math.cos(a), v = sc * s2 * Math.sin(a);
      return new THREE.Vector3(mx + u * e1[0] + v * e2[0], my + u * e1[1] + v * e2[1], h); };
    const eye = [], look = [];
    for (let k = 0; k < 12; k++) { eye.push(ring(k, 1.1, z)); look.push(ring(k + 1.5, 0.35, gz)); }
    return { eye: new THREE.CatmullRomCurve3(eye, true, "centripetal"), look: new THREE.CatmullRomCurve3(look, true, "centripetal"),
             loop: true, speed: FLIGHT_SPEED[S.group] };
  }
  // a building walk: glide along the photographer's route, looking where the photos looked (smoothed)
  const fr = P.frames, step = Math.max(1, Math.ceil(fr.length / 60)), eye = [], look = [];
  for (let i = 0; i < fr.length; i += step) {
    const f = new THREE.Vector3();
    for (let j = Math.max(0, i - 2 * step); j <= Math.min(fr.length - 1, i + 2 * step); j++) f.add(V(fr[j].f));
    f.z *= 0.3; f.normalize();
    eye.push(V(fr[i].c)); look.push(V(fr[i].c).addScaledVector(f, 10));
  }
  const gap = eye[0].distanceTo(eye[eye.length - 1]), hop = eye[0].distanceTo(eye[1] || eye[0]);
  const loop = gap < 3 * Math.max(hop, 1);
  return { eye: new THREE.CatmullRomCurve3(eye, loop, "centripetal"), look: new THREE.CatmullRomCurve3(look, loop, "centripetal"),
           loop, speed: FLIGHT_SPEED.ground };
}
function flightPose(F, u) {
  const t = F.loop ? ((u % 1) + 1) % 1 : 1 - Math.abs((((u % 2) + 2) % 2) - 1);   // a walk that doesn't close: there and back
  return lookPose(F.eye.getPointAt(t), F.look.getPointAt(t));
}
function startFlight() {
  const F = flightPath(state.poses, byClip[state.clip]);
  F.len = F.eye.getLength(); F.u = 0;
  goTo(flightPose(F, 0), 1.6);                              // glide onto the path, then fly it
  state.nextFlight = F; state.view = -1; $("view-label").textContent = "Flythrough";
  $("fly").setAttribute("aria-pressed", "true"); $("fly").textContent = "❚❚ Pause";
}
function stopFlight() {
  if (!state.flight && !state.nextFlight) return;
  state.flight = state.nextFlight = null;
  $("fly").setAttribute("aria-pressed", "false"); $("fly").textContent = "▶ Flythrough";
}
function takeControl() {
  // the visitor dragged, scrolled or pressed a key: stop flying, and in the restricted modes settle on the nearest photo
  if (!state.flight && !state.nextFlight) return;
  stopFlight(); state.tween = null;
  if (state.mode !== "free" && state.poses) setView(nearest3d(state.poses, camera.position), 1.2);
}

// ---- loading a scene
async function loadScene(clip, { view = null, keepCamera = false, then = null } = {}) {
  if (state.loading) return;
  stopFlight();
  const S = byClip[clip];
  if (!S) return toast(`Unknown scene: ${clip}`);
  state.loading = true;
  $("loading").hidden = false; $("loading-name").textContent = S.title;
  $("loading-bar").style.width = "0%";
  $("loading-sub").textContent = `${(S.gaussians / 1e6).toFixed(1)} million Gaussians · ${Math.round(S.mb)} MB`;
  try {
    const P = prepare(await loadPoses(clip));
    const mesh = new SplatMesh({
      url: assetBase + P.splat,
      lod: LOD,
      onProgress: (e) => {
        if (e && e.lengthComputable && e.total) {
          const pct = (e.loaded / e.total) * 100;
          $("loading-bar").style.width = `${pct.toFixed(1)}%`;
          $("loading-sub").textContent = e.loaded < e.total
            ? `${(e.loaded / 1e6).toFixed(0)} of ${(e.total / 1e6).toFixed(0)} MB`
            : (LOD ? "Building level of detail…" : "Preparing…");
        }
      },
    });
    mesh.position.set(P.splat_origin[0], P.splat_origin[1], P.splat_origin[2]);
    await mesh.initialized;
    if (state.mesh) { scene.remove(state.mesh); state.mesh.dispose(); }
    scene.add(mesh);
    Object.assign(state, { clip, poses: P, mesh, view: -1 });
    camera.fov = P.vfov; camera.near = S.group === "ground" ? 0.05 : 0.3; camera.updateProjectionMatrix();
    controls.fpsMovement.moveSpeed = MOVE_SPEED[S.group] * state.speed;
    renderMenu(); renderControls();
    if (then) then(P);
    else if (view !== null && P.frames[view]) setView(view, 0);
    else if (!keepCamera && state.mode !== "free") setView(centralFrame(P), 0);
    else if (!keepCamera) { const o = overviewPose(P, S.group); camera.position.copy(o.p); camera.quaternion.copy(o.q); }
    updateHash();
  } catch (err) {
    console.error(err);
    toast(`Could not load ${S.title}: ${err.message || err}`);
  } finally {
    state.loading = false; $("loading").hidden = true;
  }
}

function setView(k, seconds = 1.4) {
  const P = state.poses; if (!P) return;
  const n = P.frames.length; k = ((k % n) + n) % n;
  state.view = k;
  const pose = poseOf(P.frames[k]);
  if (seconds > 0) goTo(pose, seconds); else { camera.position.copy(pose.p); camera.quaternion.copy(pose.q); }
  $("view-label").textContent = `Photo ${k + 1} / ${n}`;
  updateHash();
}

// ---- up and down between levels
function nearestFrame(frames, pt, filter = () => true) {
  let best = -1, bd = Infinity;
  frames.forEach((f, i) => {
    if (!filter(f)) return;
    const d = Math.hypot(f.c[0] - pt.x, f.c[1] - pt.y);
    if (d < bd) { bd = d; best = i; }
  });
  return { i: best, d: bd };
}

async function goDown() {
  const S = byClip[state.clip], P = state.poses, pt = groundPointAhead();
  if (P.frames.some((f) => f.e)) {                           // a ground + air scene: its own ground photos
    const { i } = nearestFrame(P.frames, pt, (f) => f.e === "ground");
    if (i >= 0) return setView(i, 2.2);
  }
  let best = null;
  for (const g of S.ground) {
    const GP = await loadPoses(g);
    const r = nearestFrame(GP.frames, pt, (f) => !f.e || f.e === "ground");
    if (byClip[g].group === "site") r.d += 120;            // a building walk's own model is sharper: prefer it
    if (r.i >= 0 && (!best || r.d < best.d)) best = { clip: g, ...r };
  }
  if (!best || best.d > 250) return toast("No ground-level model near here. Try over a building.");
  const target = best;
  await loadScene(target.clip, { then: () => setView(target.i, 2.2) });
}

async function goUp() {
  const S = byClip[state.clip], P = state.poses;
  const here = camera.position.clone();
  const look = groundPointAhead();
  if (P.frames.some((f) => f.e)) {                           // a ground + air scene: rise inside it
    const air = P.frames.filter((f) => f.e === "air");
    const h = air.length ? air.map((f) => f.c[2]).sort((a, b) => a - b)[air.length >> 1] : here.z + 80;
    if (state.mode !== "free") return setView(nearestFrame(P.frames, here, (f) => f.e === "air").i, 2.4);
    return goTo(upPose(here, look, h), 2.4);
  }
  if (!S.aerial) return;
  const AP = prepare(await loadPoses(S.aerial));
  await loadScene(S.aerial, { keepCamera: true, then: () => (state.mode !== "free"
    ? setView(nearestFrame(AP.frames, here).i, 2.4) : goTo(upPose(here, look, AP.cam_height), 2.4)) });
}

function upPose(here, look, height) {
  // rise above where you stand and look back down at it, from a little behind
  const back = new THREE.Vector3(here.x - look.x, here.y - look.y, 0);
  if (back.lengthSq() < 1) back.set(0, -1, 0);
  back.normalize().multiplyScalar(0.6 * (height - here.z));
  return lookPose(new THREE.Vector3(here.x + back.x, here.y + back.y, height), new THREE.Vector3(here.x, here.y, look.z));
}

// ---- UI
function renderMenu() {
  const el = $("scenes");
  const groups = [["campus", "Campus · aerial"], ["ground", "Buildings · ground"], ["site", "Ground + air"]];
  el.innerHTML = groups.map(([g, name]) =>
    `<h2>${name}</h2>` + catalog.scenes.filter((s) => s.group === g).map((s) =>
      `<button class="scene${s.clip === state.clip ? " on" : ""}" data-clip="${s.clip}">
         <div class="t">${s.title}</div><div class="s">${s.subtitle}</div>
         <div class="m">${s.photos} photos · ${(s.gaussians / 1e6).toFixed(1)} M Gaussians · ${Math.round(s.mb)} MB</div>
       </button>`).join("")).join("");
  el.querySelectorAll(".scene").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.clip !== state.clip) loadScene(b.dataset.clip);
    if (window.innerWidth < 860) toggleMenu(false);
  }));
  document.querySelectorAll(".groups .chip[data-group]").forEach((c) =>
    c.classList.toggle("on", byClip[state.clip]?.group === c.dataset.group));
}

function renderControls() {
  const S = byClip[state.clip], P = state.poses;
  $("scene-name").textContent = S ? `${S.title} · ${S.subtitle}` : "";
  $("view-label").textContent = state.view >= 0 ? `Photo ${state.view + 1} / ${P.frames.length}` : `${P.frames.length} photo views`;
  const ud = $("updown");
  const mixed = P.frames.some((f) => f.e);
  if (S.group === "campus" && S.ground.length) { ud.hidden = false; ud.textContent = "↓ Go down"; ud.onclick = goDown; }
  else if (S.group === "ground" && S.aerial) { ud.hidden = false; ud.textContent = "↑ Go up"; ud.onclick = goUp; }
  else if (mixed) {
    ud.hidden = false;
    const high = camera.position.z - P.centre[2] > 20;
    ud.textContent = high ? "↓ Go down" : "↑ Go up"; ud.onclick = high ? goDown : goUp;
  } else ud.hidden = true;
}

function toggleMenu(show) {
  const el = $("scenes");
  show = show ?? el.classList.contains("hidden");
  el.classList.toggle("hidden", !show);
  $("menu-btn").setAttribute("aria-expanded", String(show));
}

let toastTimer = 0;
function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 4000);
}

let hashTimer = 0;
function updateHash() {
  clearTimeout(hashTimer);
  hashTimer = setTimeout(() => {
    const h = `#${state.clip}${state.view >= 0 ? `/${state.view + 1}` : ""}`;
    if (location.hash !== h) history.replaceState(null, "", h);
  }, 200);
}

$("menu-btn").addEventListener("click", () => toggleMenu());
document.querySelectorAll(".groups .chip[data-group]").forEach((c) => c.addEventListener("click", () => {
  const first = catalog.scenes.find((s) => s.group === c.dataset.group);
  toggleMenu(true);
  if (first && byClip[state.clip]?.group !== c.dataset.group) loadScene(first.clip);
}));
$("prev").addEventListener("click", () => setView(state.view < 0 ? 0 : state.view - 1));
$("next").addEventListener("click", () => setView(state.view + 1));
$("view-label").addEventListener("click", () => setView(state.view < 0 ? 0 : state.view));
$("overview").addEventListener("click", () => {
  if (state.mode !== "free") return setView(centralFrame(state.poses));
  state.view = -1; renderControls(); goTo(overviewPose(state.poses, byClip[state.clip].group)); updateHash();
});
$("fly").addEventListener("click", () => {
  if (state.flight || state.nextFlight) return takeControl();
  if (state.poses) startFlight();
});
canvas.addEventListener("pointerdown", takeControl);
canvas.addEventListener("wheel", takeControl, { passive: true });
$("speed").addEventListener("change", (e) => {
  state.speed = parseFloat(e.target.value);
  if (state.clip) controls.fpsMovement.moveSpeed = MOVE_SPEED[byClip[state.clip].group] * state.speed;
});
function setMode(m) {
  state.mode = m; store.set("ucsb3d.mode", m); $("mode").value = m;
  stopFlight();
  if (m === "photos" && state.poses) setView(state.view >= 0 ? state.view : nearest3d(state.poses, camera.position));
}
$("mode").addEventListener("change", (e) => setMode(e.target.value));
$("help-btn").addEventListener("click", () => {
  const h = $("help"); h.hidden = !h.hidden; $("help-btn").setAttribute("aria-pressed", String(!h.hidden));
});
$("fs").addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen?.();
});
const closeAbout = () => { $("about").hidden = true; store.set("ucsb3d.seen", "1"); };
$("about-close").addEventListener("click", closeAbout);
$("about-go").addEventListener("click", closeAbout);
$("about-btn").addEventListener("click", () => { $("about").hidden = !$("about").hidden; });
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "SELECT") return;
  if (!["[", "]", "Escape"].includes(e.key)) takeControl();
  if (e.key === "[") setView(state.view < 0 ? 0 : state.view - 1);
  if (e.key === "]") setView(state.view + 1);
  if (e.key === "Escape") { $("about").hidden = true; $("help").hidden = true; }
});

// ---- frame loop
let lastUd = 0;
let lastNow = 0;
renderer.setAnimationLoop((now) => {
  const dt = Math.min(0.1, (now - (lastNow || now)) / 1000); lastNow = now;
  if (state.tween) {
    const T = state.tween, t = Math.min(1, (now - T.t0) / T.dur), k = ease(t);
    camera.position.lerpVectors(T.p0, T.p1, k);
    camera.quaternion.slerpQuaternions(T.q0, T.q1, k);
    if (t >= 1) { state.tween = null; if (state.nextFlight) { state.flight = state.nextFlight; state.nextFlight = null; } }
  } else if (state.flight) {
    const F = state.flight;
    F.u += (dt * F.speed * state.speed) / F.len;
    const pose = flightPose(F, F.u);
    camera.position.copy(pose.p); camera.quaternion.copy(pose.q);
  } else {
    controls.update(camera);
    constrain();
  }
  if (state.poses && now - lastUd > 500) { lastUd = now; if (state.poses.frames.some((f) => f.e)) renderControls(); }
  renderer.render(scene, camera);
});

// ---- start
if (!store.get("ucsb3d.seen")) $("about").hidden = false; else $("about").hidden = true;
$("mode").value = state.mode; $("fly").textContent = "▶ Flythrough";
if (window.innerWidth < 860) toggleMenu(false);
const [hClip, hView] = decodeURIComponent(location.hash.slice(1)).split("/");
await loadScene(byClip[hClip] ? hClip : catalog.scenes[0].clip, { view: hView ? parseInt(hView, 10) - 1 : null });
// opening the page without a scene in the link plays the flythrough, as JHU in 3D does; ?autoplay=0 / =1 overrides
if (state.poses && (params.get("autoplay") === "1" || (!byClip[hClip] && params.get("autoplay") !== "0"))) {
  startFlight();
  toast("Flythrough playing · drag, scroll or press a key to take over");
}

