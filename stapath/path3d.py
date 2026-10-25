"""3D view of one timing path on the real placement and routing.

  python3 -m stapath.path3d REPORT DEF LEF out.html [--path N] [--three URL --orbit URL]

x, y are the placed cell and routed wire coordinates from the DEF (microns); z is the metal layer.
Every number shown comes from the timing report (parser) or the DEF.
"""
from __future__ import annotations
import argparse, json, re
from .parser import parse_report, summary, data_stages, _launch_clock_pin
from .defparse import read_def, read_lef_sizes, wire_length_by_layer

SKIP_CELLS = re.compile(r"^(FILLCELL|TAPCELL|PHY_|WELLTAP|DECAP)", re.I)


def _layer_index(layer: str) -> int:
    m = re.search(r"(\d+)$", layer)
    return int(m.group(1)) if m else 1


def build_scene(report_text: str, def_text: str, lef_text: str, index: int = 0) -> dict:
    p = parse_report(report_text)[index]
    sm = summary(p)
    d = read_def(def_text, read_lef_sizes(lef_text))

    # driver pin -> net, from DEF connectivity
    drv = {}
    for n in d.nets.values():
        for inst, pin in n.conns:
            drv[(inst, pin)] = n

    def net_of(pin_path: str):
        if "/" in pin_path:
            inst, pin = pin_path.rsplit("/", 1)
            return drv.get((inst, pin))
        return drv.get(("PIN", pin_path))

    def segs(n):
        out = []
        for w in n.wires:
            z = _layer_index(w.layer)
            for a, b in zip(w.pts, w.pts[1:]):
                out.append([z, round(a[0], 3), round(a[1], 3), round(b[0], 3), round(b[1], 3)])
        return out

    def vias(n):
        return [[_layer_index(v.layer), round(v.x, 3), round(v.y, 3)] for v in n.vias]

    total = sm["data_path_delay"] or 1.0
    stages = data_stages(p)
    ck = _launch_clock_pin(p)
    path_insts, stage_rows, path_nets = set(), [], []
    for k, s in enumerate(stages):
        c = d.comps.get(s.instance)
        is_end = (k == len(stages) - 1)
        if c:
            path_insts.add(c.name)
            stage_rows.append(dict(inst=c.name, cell=c.cell, x=c.x, y=c.y, w=c.w, h=c.h, delay=s.delay,
                                   arrival=s.time, share=round(100 * s.delay / total, 1),
                                   role="end" if is_end else ("start" if k == 0 else "mid")))
        if not is_end:
            n = net_of(s.pin)
            if n:
                L = sum(wire_length_by_layer(n).values())
                path_nets.append(dict(name=n.name, driver=s.instance, t=s.time, length=round(L, 1),
                                      segs=segs(n), vias=vias(n)))

    clock_nets, clock_cells = [], []
    for sec in (p.launch + ([ck] if ck else []), [x for x in p.capture if x.instance != p.endpoint]):
        for s in sec:
            n = net_of(s.pin)
            if n and n.name not in {c["name"] for c in clock_nets}:
                clock_nets.append(dict(name=n.name, segs=segs(n), vias=vias(n)))
            c = d.comps.get(s.instance)
            if c and c.name not in path_insts and c.name not in {x["inst"] for x in clock_cells}:
                clock_cells.append(dict(inst=c.name, cell=c.cell, x=c.x, y=c.y, w=c.w, h=c.h, delay=s.delay))

    cells = [[round(c.x, 3), round(c.y, 3), round(c.w, 3), round(c.h, 3)]
             for c in d.comps.values() if not SKIP_CELLS.match(c.cell) and c.name not in path_insts and c.w]
    used = {n["name"] for n in path_nets} | {n["name"] for n in clock_nets}
    bg = [s for n in d.nets.values() if n.name not in used for s in segs(n)]
    return dict(design=d.name, die=d.die, summary=sm, stages=stage_rows, path_nets=path_nets,
                clock_nets=clock_nets, clock_cells=clock_cells, cells=cells, bg=bg,
                max_layer=max([s[0] for s in bg] + [1]))


HTML = r"""<title>Timing Path 3D</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;700&display=swap">
<style>
/* single dark look: a layout-viewer night scene; the scene fills the viewport, HUD floats over it */
:root { --bg:#0f1830; --ink:#eef2fb; --ink2:#a9b5d1; --ink3:#6f7ea3; --poly:#ff5d52; --li:#f2b84b; --met1:#5b8def; --clk:#4fd1c5;
  --tipbg:rgba(15,24,48,.92); --tipline:#33416b; color-scheme:dark; }
html,body { margin:0; height:100%; background:var(--bg); color:var(--ink); font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif; overflow:hidden; }
#c { position:fixed; inset:0; width:100%; height:100%; display:block; }
.hud { position:fixed; left:max(16px, calc(28px + env(safe-area-inset-left, 0px))); top:calc(24px + env(safe-area-inset-top, 0px)); max-width:min(520px, calc(100vw - 56px)); pointer-events:none; }
.hud h1 { margin:0; font-size:clamp(26px,4vw,44px); line-height:1.05; font-weight:700; letter-spacing:-.5px; }
.hud p { margin:10px 0 0; font-size:clamp(13px,1.6vw,17px); line-height:1.45; color:var(--ink2); }
.key { position:fixed; left:max(16px, calc(28px + env(safe-area-inset-left, 0px))); right:max(16px, env(safe-area-inset-right, 0px)); bottom:calc(24px + env(safe-area-inset-bottom, 0px)); display:flex; flex-wrap:wrap; gap:8px 18px; font-size:14px; color:var(--ink2); pointer-events:none; max-width:calc(100vw - 56px); }
.key span { display:inline-flex; align-items:center; gap:8px; }
.key i { width:22px; height:6px; border-radius:3px; display:inline-block; }
.num { position:fixed; right:max(16px, calc(28px + env(safe-area-inset-right, 0px))); top:calc(24px + env(safe-area-inset-top, 0px)); text-align:right; pointer-events:none; }
.num b { display:block; font-size:clamp(28px,4.5vw,54px); line-height:1; color:var(--poly); }
.num span { font-size:14px; color:var(--ink2); }
.tip { position:fixed; pointer-events:none; padding:8px 10px; border-radius:6px; background:var(--tipbg); border:1px solid var(--tipline); color:var(--ink);
  font-size:13px; line-height:1.4; display:none; white-space:nowrap; }
@media (max-width:640px){ .num{ top:auto; bottom:calc(96px + env(safe-area-inset-bottom, 0px)); } .key{ font-size:12px; } }
@media (prefers-reduced-motion: reduce){ * { scroll-behavior:auto; } }
</style>
<canvas id="c" aria-label="3D view of the timing path"></canvas>
<div class="hud"><h1>One timing path, in 3D</h1>
<p id="sub"></p></div>
<div class="num"><b id="slack"></b><span id="slackl"></span></div>
<div class="key">
  <span><i style="background:linear-gradient(90deg,#3f7bff,#a66bff,#ff5d52)"></i>signal wire, coloured by arrival time</span>
  <span><i style="background:var(--clk)"></i>clock tree</span>
  <span><i style="background:#2b3a66"></i>other cells and wires</span>
  <span id="hint">height = metal layer · drag to rotate, hover a cell</span>
</div>
<div class="tip" id="tip"></div>
<script src="__THREE__"></script>
<script src="__ORBIT__"></script>
<script>
const S = __DATA__;
const LZ = 2.4;                       // microns of height per metal layer (exaggerated for legibility)
const W = S.die[2], H = S.die[3], cx = W/2, cy = H/2;
const sm = S.summary;
document.getElementById('sub').textContent =
  `Worst setup path of ${S.design} (Nangate45, placed and routed). ${sm.startpoint} → ${sm.endpoint}: ` +
  `${sm.n_stages} cell stages, ${sm.data_path_delay.toFixed(3)} ns of data path. x and y are the real placement and routing in microns; height is the metal layer.`;
document.getElementById('slack').textContent = `${sm.slack < 0 ? '−' : '+'}${Math.abs(sm.slack).toFixed(3)} ns`;
document.getElementById('slackl').textContent = `slack · arrival ${sm.arrival.toFixed(3)} vs required ${sm.required.toFixed(3)} ns`;

if (window.__STATIC__) document.getElementById('hint').textContent = 'height = metal layer';
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color('#0f1830');
scene.fog = new THREE.Fog('#0f1830', 260, 520);
const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 2000);
const P = (x, y, z) => new THREE.Vector3(x - cx, z, -(y - cy));

// die plate and grid
const plate = new THREE.Mesh(new THREE.BoxGeometry(W, 0.6, H), new THREE.MeshStandardMaterial({color:'#131f3d', roughness:.9}));
plate.position.set(0, -0.3, 0); scene.add(plate);
const grid = new THREE.GridHelper(Math.max(W, H), 40, '#22305a', '#1a2648'); grid.position.y = 0.01; scene.add(grid);

// background cells (instanced)
const cellGeo = new THREE.BoxGeometry(1, 1, 1);
const bgMat = new THREE.MeshStandardMaterial({color:'#2b3a66', roughness:.8});
const inst = new THREE.InstancedMesh(cellGeo, bgMat, S.cells.length);
const m4 = new THREE.Matrix4();
S.cells.forEach((c, i) => { m4.compose(P(c[0] + c[2]/2, c[1] + c[3]/2, 0.25), new THREE.Quaternion(), new THREE.Vector3(c[2]*0.92, 0.5, c[3]*0.92)); inst.setMatrixAt(i, m4); });
scene.add(inst);

// background wires: one line segment set per layer
const byLayer = {};
S.bg.forEach(s => { (byLayer[s[0]] = byLayer[s[0]] || []).push(s); });
Object.entries(byLayer).forEach(([z, list]) => {
  const pos = [];
  list.forEach(s => { const a = P(s[1], s[2], z*LZ), b = P(s[3], s[4], z*LZ); pos.push(a.x, a.y, a.z, b.x, b.y, b.z); });
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  scene.add(new THREE.LineSegments(g, new THREE.LineBasicMaterial({color:'#3a4c80', transparent:true, opacity:.28})));
});

// arrival-time colour ramp: blue -> amber -> red over the data path
const t0 = S.stages.length ? S.stages[0].arrival - S.stages[0].delay : 0, t1 = sm.arrival;
const ramp = [new THREE.Color('#3f7bff'), new THREE.Color('#a66bff'), new THREE.Color('#ff5d52')];
function tcol(t){ const u = Math.max(0, Math.min(1, (t - t0)/(t1 - t0 || 1))); return u < .5 ? ramp[0].clone().lerp(ramp[1], u*2) : ramp[1].clone().lerp(ramp[2], (u-.5)*2); }

function tube(a, b, r, mat){
  const d = new THREE.Vector3().subVectors(b, a), len = d.length(); if (len < 1e-3) return null;
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 10), mat);
  m.position.copy(a).add(b).multiplyScalar(.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), d.normalize()); scene.add(m); return m;
}
function drawNet(n, mat, r){
  n.segs.forEach(s => tube(P(s[1], s[2], s[0]*LZ), P(s[3], s[4], s[0]*LZ), r, mat));
  n.vias.forEach(v => tube(P(v[1], v[2], v[0]*LZ), P(v[1], v[2], (v[0]+1)*LZ), r*0.8, mat));
}
const clkMat = new THREE.MeshStandardMaterial({color:'#3fb8ae', emissive:'#12504b', emissiveIntensity:.5, roughness:.5, transparent:true, opacity:.75});
S.clock_nets.forEach(n => drawNet(n, clkMat, 0.11));
const pickables = [];
S.path_nets.forEach(n => {
  const c = tcol(n.t);
  const mat = new THREE.MeshStandardMaterial({color:c, emissive:c, emissiveIntensity:.3, roughness:.45});
  drawNet(n, mat, 0.34);
});

// path cells: extruded blocks, height by share of the data-path delay
S.stages.forEach(s => {
  const hgt = 0.8 + s.share * 0.22;
  const col = s.share >= 20 ? '#ff5d52' : s.share >= 10 ? '#f2b84b' : '#5b8def';
  const mesh = new THREE.Mesh(cellGeo, new THREE.MeshStandardMaterial({color:col, emissive:col, emissiveIntensity:.2, roughness:.55}));
  mesh.scale.set(Math.max(s.w, .8), hgt, Math.max(s.h, .8)); mesh.position.copy(P(s.x + s.w/2, s.y + s.h/2, hgt/2));
  mesh.userData = s; scene.add(mesh); pickables.push(mesh);
});
S.clock_cells.forEach(s => {
  const mesh = new THREE.Mesh(cellGeo, clkMat); mesh.scale.set(s.w, 1.2, s.h); mesh.position.copy(P(s.x + s.w/2, s.y + s.h/2, .6));
  mesh.userData = Object.assign({clock:true}, s); scene.add(mesh); pickables.push(mesh);
});

// labels for start, end and the slowest stage
function label(text, pos, color){
  const cv = document.createElement('canvas'), k = 4; cv.width = 512*k/2; cv.height = 64*k/2;
  const g = cv.getContext('2d'); g.scale(k/2, k/2); g.font = '600 30px "IBM Plex Sans", Arial'; g.fillStyle = color; g.fillText(text, 8, 40);
  const tex = new THREE.CanvasTexture(cv); tex.anisotropy = 4;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:tex, depthTest:false, transparent:true}));
  sp.scale.set(20, 2.5, 1); sp.position.copy(pos); sp.center.set(0, 0); scene.add(sp);
}
const worst = S.stages.slice().sort((a, b) => b.delay - a.delay)[0];
const st = S.stages[0], en = S.stages[S.stages.length - 1];
label(`launch ${st.inst}`, P(st.x, st.y, 9), '#eef2fb');
label(`capture ${en.inst}`, P(en.x, en.y, 9), '#eef2fb');
const longest = S.path_nets.slice().sort((a, b) => b.length - a.length)[0];
if (longest && longest.segs.length) {
  let far = longest.segs[0], best = -1;
  longest.segs.forEach(sg => [[sg[1], sg[2]], [sg[3], sg[4]]].forEach(q => {
    const d2 = (q[0] - en.x) ** 2 + (q[1] - en.y) ** 2; if (d2 > best) { best = d2; far = [sg[0], q[0], q[1]]; } }));
  label(`${longest.driver} net ${longest.name}: ${longest.length} µm`, P(far[1], far[2], far[0]*LZ + 3), '#f2b84b');
}

scene.add(new THREE.HemisphereLight('#c9d6ff', '#0b1226', .6));
const dl = new THREE.DirectionalLight('#ffffff', .55); dl.position.set(-60, 120, 80); scene.add(dl);

const controls = new THREE.OrbitControls(camera, canvas);
const xs = S.stages.map(s => s.x), ys = S.stages.map(s => s.y);
const bx0 = Math.min(...xs), bx1 = Math.max(...xs), by0 = Math.min(...ys), by1 = Math.max(...ys);
const ext = Math.max(bx1 - bx0, by1 - by0, 30);
controls.target.copy(P((bx0 + bx1)/2, (by0 + by1)/2, 3)); controls.enableDamping = true; controls.autoRotate = !matchMedia('(prefers-reduced-motion: reduce)').matches && !window.__STATIC__;
controls.autoRotateSpeed = .5;
const view = window.__VIEW__ || {az: 1.0, el: 0.8, dist: 2.6};
function place(){
  const r = ext * view.dist / Math.min(1, camera.aspect), t = controls.target;
  camera.position.set(t.x + r*Math.sin(view.az)*Math.cos(view.el), t.y + r*Math.sin(view.el), t.z + r*Math.cos(view.az)*Math.cos(view.el));
  camera.lookAt(controls.target);
}
function resize(){ const w = innerWidth, h = innerHeight; renderer.setSize(w, h, false); camera.aspect = w/h; camera.updateProjectionMatrix(); }
addEventListener('resize', () => { resize(); });
resize(); place(); controls.update();
resize(); place();

const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = document.getElementById('tip');
canvas.addEventListener('pointermove', e => {
  mouse.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1); ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(pickables)[0];
  if (!hit) { tip.style.display = 'none'; return; }
  const s = hit.object.userData;
  tip.innerHTML = s.clock ? `<b>${s.inst}</b> ${s.cell} · clock tree<br>${s.delay.toFixed(3)} ns`
    : `<b>${s.inst}</b> ${s.cell}<br>delay ${s.delay.toFixed(3)} ns · ${s.share}% of data path<br>arrival ${s.arrival.toFixed(3)} ns`;
  tip.style.display = 'block'; tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 14) + 'px';
});
(function loop(){ controls.update(); renderer.render(scene, camera); window.__READY__ = true; requestAnimationFrame(loop); })();
</script>"""


def render_html(scene: dict, three: str, orbit: str, standalone: bool = True) -> str:
    """standalone=True wraps the page in its own document; False gives the fragment an Artifact expects."""
    body = (HTML.replace("__DATA__", json.dumps(scene, separators=(",", ":")))
            .replace("__THREE__", three).replace("__ORBIT__", orbit))
    if not standalone:
        return body
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n'
            + body + "\n</body></html>")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report"); ap.add_argument("def_file"); ap.add_argument("lef"); ap.add_argument("out")
    ap.add_argument("--path", type=int, default=0)
    ap.add_argument("--three", default="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js")
    ap.add_argument("--orbit", default="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js")
    ap.add_argument("--json", help="also write the scene data here")
    ap.add_argument("--fragment", action="store_true", help="write the page without <html>/<head>/<body> (for Claude Artifacts)")
    a = ap.parse_args(argv)
    sc = build_scene(open(a.report).read(), open(a.def_file).read(), open(a.lef).read(), a.path)
    if a.json:
        json.dump(sc, open(a.json, "w"))
    open(a.out, "w").write(render_html(sc, a.three, a.orbit, standalone=not a.fragment))
    print(f"wrote {a.out}: {len(sc['stages'])} path cells, {len(sc['path_nets'])} path nets, "
          f"{len(sc['clock_nets'])} clock nets, {len(sc['cells'])} other cells, {len(sc['bg'])} background segments")


if __name__ == "__main__":
    main()
