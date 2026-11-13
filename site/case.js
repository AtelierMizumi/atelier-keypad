// Exploded view of the Atelier6K acrylic case.
//
// Geometry comes from assets/case.json (written by case/generate.py) and the
// PCB model from assets/atelier6k.glb (exported by KiCad). Model space is in
// millimetres: origin at the board centre, PCB top surface at z = 0, +z up.
//
// URL parameters, used for the static renders in docs/images:
//   explode=0..1  az=deg  el=deg  dist=mm  caps=0|1  labels=0|1  ui=0  theme=light
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const q = new URLSearchParams(location.search);
// ?rev=1 shows the rev 1 board and its case (FR4 plate, MCU module under the PCB).
const TAG = q.get('rev') === '1' ? '-rev1' : '';
const num = (k, d) => (q.has(k) ? parseFloat(q.get(k)) : d);
const flag = (k, d) => (q.has(k) ? q.get(k) !== '0' : d);
if (q.get('theme') === 'light') document.body.classList.add('light');
if (!flag('ui', true)) document.body.classList.add('bare');

const stage = document.getElementById('stage');
const labelsEl = document.getElementById('labels');
const statusEl = document.getElementById('status');
const slider = document.getElementById('explode');
const capsBox = document.getElementById('caps');
const tagsBox = document.getElementById('tags');
slider.value = num('explode', 1);
capsBox.checked = flag('caps', true);
tagsBox.checked = flag('labels', true);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
stage.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.position.set(80, 160, 120);
scene.add(key);

const camera = new THREE.PerspectiveCamera(28, 1, 1, 4000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

// Everything is built z-up, then tipped over into three's y-up world.
const world = new THREE.Group();
world.rotation.x = -Math.PI / 2;
scene.add(world);

const EXPLODE_STEP = 15; // mm between neighbouring parts at full explode
const parts = [];        // { group, order, label, sub, anchorZ, optional }

function addPart(name, order, label, sub, anchorZ, optional = false) {
  const group = new THREE.Group();
  group.name = name;
  world.add(group);
  const part = { group, order, label, sub, anchorZ, optional, el: null };
  if (label) {
    part.el = document.createElement('div');
    part.el.className = 'label';
    const b = document.createElement('b'); b.textContent = label;
    const span = document.createElement('span'); span.textContent = sub;
    part.el.append(b, span);
    labelsEl.appendChild(part.el);
  }
  parts.push(part);
  return group;
}

const ACRYLIC = {
  clear: { color: 0xbfe6ff, opacity: 0.22, roughness: 0.06, edge: 0xdff4ff },
  frosted: { color: 0xf4f7f9, opacity: 0.62, roughness: 0.75, edge: 0xffffff },
  fr4: { color: 0x2f7d4a, opacity: 0.93, roughness: 0.55, edge: 0xbfe8c8 },
};

function shapeFrom(outer, holes) {
  const shape = new THREE.Shape(outer.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of holes) shape.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  return shape;
}

function acrylicLayer(layer, renderOrder) {
  const style = ACRYLIC[layer.material] || ACRYLIC.clear;
  const geom = new THREE.ExtrudeGeometry(shapeFrom(layer.outer, layer.holes),
    { depth: layer.thickness, bevelEnabled: false, curveSegments: 1 });
  const mat = new THREE.MeshPhysicalMaterial({
    color: style.color, transparent: true, opacity: style.opacity, roughness: style.roughness,
    metalness: 0, clearcoat: layer.material === 'clear' ? 1 : 0, clearcoatRoughness: 0.05,
    side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 1.2,
  });
  const mesh = new THREE.Mesh(geom, mat);
  mesh.renderOrder = renderOrder;
  // Laser-cut edges catch the light; drawing them keeps each layer readable.
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom, 35),
    new THREE.LineBasicMaterial({ color: style.edge, transparent: true, opacity: 0.85 }));
  edges.renderOrder = renderOrder + 0.5;
  const g = new THREE.Group();
  g.add(mesh, edges);
  g.position.z = layer.z0;
  return g;
}

const std = (color, roughness = 0.5, metalness = 0) => new THREE.MeshStandardMaterial({ color, roughness, metalness });

function box(w, d, h, mat) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, d, h), mat);
  m.position.z = h / 2;
  return m;
}

function cyl(rTop, rBottom, h, segs, mat) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, h, segs), mat);
  m.rotation.x = Math.PI / 2; // cylinder axis along z
  m.position.z = h / 2;
  return m;
}

function mxSwitch() {
  // Simplified Cherry MX: 14 mm lower housing through the plate, upper housing, stem.
  const g = new THREE.Group();
  const lower = box(13.9, 13.9, 5.0, std(0x23272b, 0.55));
  const upper = cyl(11.2 / Math.SQRT2, 15.4 / Math.SQRT2, 6.4, 4, std(0x2c3136, 0.45));
  upper.rotation.y = Math.PI / 4;
  upper.position.z = 5.0 + 3.2;
  const stem = box(5.6, 4.2, 3.6, std(0xc0392b, 0.4));
  stem.position.z = 11.4 + 1.8;
  g.add(lower, upper, stem);
  return g;
}

function keycap() {
  const cap = cyl(12.6 / Math.SQRT2, 18.0 / Math.SQRT2, 8.0, 4, std(0xf2efe6, 0.6));
  cap.rotation.y = Math.PI / 4;
  cap.position.z = 10.0 + 4.0;
  const g = new THREE.Group();
  g.add(cap);
  return g;
}

function screw(length) {
  const g = new THREE.Group();
  const steel = std(0x1c1c1e, 0.35, 0.9);
  const shank = cyl(1.5, 1.5, length, 20, steel);
  shank.position.z = -length / 2;
  const head = new THREE.Mesh(new THREE.SphereGeometry(2.85, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), steel);
  head.rotation.x = Math.PI / 2;
  head.scale.z = 1; head.scale.y = 0.58;
  g.add(shank, head);
  return g;
}

function nut(thickness) {
  return cyl(5.5 / Math.sqrt(3), 5.5 / Math.sqrt(3), thickness, 6, std(0xb8bcc2, 0.3, 1.0));
}

async function build() {
  const data = await (await fetch(`assets/case${TAG}.json`)).json();
  const L = Object.fromEntries(data.layers.map((l) => [l.name, l]));
  const top = L['plate'].z0 + L['plate'].thickness;
  const baseTop = L['base'].z0 + L['base'].thickness;
  const mm = (l) => (l.material === 'fr4' ? `${l.thickness} mm FR4, ordered as a PCB` : `${l.thickness} mm ${l.material} acrylic`);

  const feet = addPart('feet', -4, 'Rubber feet', '4 × Ø8 mm, cover the nut pockets', L['base'].z0 - 1);
  for (const [x, y] of data.screws) {
    const f = cyl(4, 4, 2, 24, std(0x111111, 0.9));
    f.position.set(x, y, L['base'].z0 - 2 + 1);
    feet.add(f);
  }

  addPart('base', -3, 'Base', mm(L['base']), L['base'].z0 + 1.5).add(acrylicLayer(L['base'], 1));

  const nuts = addPart('nuts', -2, 'M3 nuts', '4 ×, captive in the base', baseTop - 1.2);
  for (const [x, y] of data.screws) {
    const n = nut(data.screw.nut_thickness);
    n.position.set(x, y, baseTop - data.screw.nut_thickness / 2);
    nuts.add(n);
  }

  addPart('bottom-frame', -1, 'Bottom frame', mm(L['bottom-frame']), L['bottom-frame'].z0 + 2.5)
    .add(acrylicLayer(L['bottom-frame'], 2));

  const pcb = addPart('pcb', 0, 'PCB', `${data.pcb.thickness} mm, hot-swap sockets underneath`, -data.pcb.thickness / 2);

  addPart('top-frame', 1, 'Top frame', mm(L['top-frame']), 1).add(acrylicLayer(L['top-frame'], 3));
  if (data.washer) {
    const washers = addPart('washers', 1.5, 'M3 washers', `4 ×, ${data.washer} mm, set the plate height`, L['plate'].z0);
    for (const [x, y] of data.screws) {
      const w = cyl(3.5, 3.5, data.washer, 24, std(0xc9ccd1, 0.35));
      w.position.set(x, y, L['plate'].z0 - data.washer / 2);
      washers.add(w);
    }
  }
  addPart('plate', 2, 'Switch plate', mm(L['plate']), L['plate'].z0 + 1.5).add(acrylicLayer(L['plate'], 4));

  const switches = addPart('switches', 3, 'MX switches', '6 ×, 5-pin, hot-swap', 7, true);
  const caps = addPart('keycaps', 3.7, 'Keycaps', '6 × 1u', 14, true);
  for (const [x, y] of data.switches) {
    const s = mxSwitch(); s.position.set(x, y, 0); switches.add(s);
    const c = keycap(); c.position.set(x, y, 0); caps.add(c);
  }

  const screws = addPart('screws', 5.8, `M3 × ${data.screw.length} screws`, '4 ×, button head, from the top', top - 4);
  for (const [x, y] of data.screws) {
    const s = screw(data.screw.length); s.position.set(x, y, top); screws.add(s);
  }

  // KiCad exports the board in metres, y-up, with its bottom face on the origin plane.
  const gltf = await new GLTFLoader().loadAsync(`assets/atelier6k${TAG}.glb`);
  const board = gltf.scene;
  board.scale.setScalar(1000);
  const holder = new THREE.Group();
  holder.rotation.x = Math.PI / 2; // undo the world tilt: glTF is already y-up
  holder.add(board);
  holder.position.z = num('pcbz', -data.pcb.thickness);
  pcb.add(holder);
  window.__pcbBox = new THREE.Box3().setFromObject(board);

  if (data.module) {
    // The KiCad model has no 3D body for the MCU module: draw a stand-in under the board.
    const [mx, my] = data.module;
    const under = -data.pcb.thickness;
    const body = new THREE.Mesh(new THREE.BoxGeometry(18, 23.5, 1), std(0x1b3a6b, 0.6));
    body.position.set(mx, my - 11.75, under - 0.5);
    const usb = new THREE.Mesh(new THREE.BoxGeometry(8.94, 7.35, 3.2), std(0xc9ccd1, 0.3));
    usb.position.set(mx, my - 3.2, under - 1 - 1.6);
    pcb.add(body, usb);
  }

  statusEl.remove();
  return data;
}

function applyExplode(t) {
  for (const p of parts) p.group.position.z = p.order * EXPLODE_STEP * t;
}

function frame(data, t) {
  // Aim at the middle of the (possibly exploded) stack.
  const zs = parts.filter((p) => p.group.visible).map((p) => p.anchorZ + p.order * EXPLODE_STEP * t);
  const zMid = (Math.min(...zs) + Math.max(...zs)) / 2;
  const span = Math.max(...zs) - Math.min(...zs);
  controls.target.set(num('tx', 0), zMid, 0);
  const az = THREE.MathUtils.degToRad(num('az', -32));
  const el = THREE.MathUtils.degToRad(num('el', 24));
  const dist = num('dist', 0) || 215 + span * 1.75;
  camera.position.set(
    dist * Math.cos(el) * Math.sin(az),
    zMid + dist * Math.sin(el),
    dist * Math.cos(el) * Math.cos(az));
  controls.update();
}

const v = new THREE.Vector3();
const CORNERS = [[40.64, 36.83], [40.64, -36.83], [-40.64, 36.83], [-40.64, -36.83]];
function placeLabels(t) {
  const show = tagsBox.checked && t > 0.35;
  const w = stage.clientWidth, h = stage.clientHeight;
  const shift = num('labelx', 0);
  for (const p of parts) {
    if (!p.el) continue;
    // Anchor on whichever outline corner is furthest right on screen.
    const z = p.anchorZ + p.group.position.z;
    let best = null;
    for (const [cx, cy] of CORNERS) {
      v.set(cx, cy, z).applyMatrix4(world.matrixWorld).project(camera);
      if (!best || v.x > best.x) best = { x: v.x, y: v.y };
    }
    p.el.style.left = `${(best.x * 0.5 + 0.5) * w + 12 + shift}px`;
    p.el.style.top = `${(-best.y * 0.5 + 0.5) * h}px`;
    p.el.classList.toggle('on', show && p.group.visible);
  }
}

function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

build().then((data) => {
  const setVisible = () => {
    for (const p of parts) if (p.optional) p.group.visible = capsBox.checked;
  };
  const update = (reframe) => {
    const t = parseFloat(slider.value);
    applyExplode(t);
    if (reframe) frame(data, t);
  };
  setVisible();
  resize();
  update(true);

  slider.addEventListener('input', () => update(true));
  capsBox.addEventListener('change', () => { setVisible(); update(true); });
  window.addEventListener('resize', resize);

  let frames = 0;
  renderer.setAnimationLoop(() => {
    controls.update();
    world.updateMatrixWorld(true);
    renderer.render(scene, camera);
    placeLabels(parseFloat(slider.value));
    if (++frames === 5) window.__ready = true;
  });
}).catch((err) => {
  statusEl.textContent = `Could not load the model: ${err.message}`;
  console.error(err);
});
