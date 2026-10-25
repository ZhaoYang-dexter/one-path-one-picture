"""LinkedIn poster: where the worst path's delay goes, plus the eval results.

  python3 tools/make_poster.py [out.png]      (run from the repo root; needs Playwright + Chromium)

Every number on the poster is read from the parser or the graded eval files.
"""
import html, json, os, pathlib, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, ".")
from stapath.parser import parse_report, _split, data_stages, summary

ROOT = pathlib.Path(".").resolve()
FONTS = ROOT / "tools/fonts"
REPORT = "reports/gcd_4ns_top40.rpt"

text = (ROOT / REPORT).read_text()
path = parse_report(text)[0]
sm = summary(path)
raw = "\n".join(_split(text)[0][:34])

# ---- timeline segments: group the 5-cell maj3 ripple chain, keep everything else per cell
stages = [s for s in data_stages(path) if s.delay > 0]
segs, i = [], 0
while i < len(stages):
    j = i
    while j < len(stages) and stages[j].cell_type == stages[i].cell_type:
        j += 1
    run = stages[i:j] if j - i >= 3 else stages[i:i + 1]
    segs.append(run); i += len(run)

T = 5.0                                 # axis length in ns
req = path.required
arr = path.arrival
chain = next(g for g in segs if len(g) > 1)
chain_d = round(sum(s.delay for s in chain), 3)
worst = max(stages, key=lambda s: s.delay)


def pct(t):
    return 100 * t / T


bars, t = [], 0.0
for g in segs:
    d = round(sum(s.delay for s in g), 3)
    cls = "chain" if g is chain else "hot" if g[0] is worst else "plain"
    bars.append(f'<div class="seg {cls}" style="left:{pct(t):.3f}%;width:{pct(d):.3f}%"></div>')
    t += d

callouts = f"""
<div class="call c-chain" style="left:{pct(sum(s.delay for g in segs[:segs.index(chain)] for s in g)):.2f}%;width:{pct(chain_d):.2f}%">
  <div class="tick"></div><b>{len(chain)} × {chain[0].cell_type}</b><span>ripple-carry chain</span><em>{chain_d:.3f} ns · {100*chain_d/sm['data_path_delay']:.0f}% of the path</em></div>
<div class="call c-hot" style="left:{pct(worst.time - worst.delay):.2f}%">
  <div class="tick"></div><b>{worst.instance} {worst.cell_type}</b><span>fanout {worst.fanout}, slew {worst.slew:.3f} ns</span><em>{worst.delay:.3f} ns · {100*worst.delay/sm['data_path_delay']:.0f}%</em></div>
"""

runs = [("Claude Haiku", "reading the raw report", "eval/results_prompt_only_haiku.graded.json"),
        ("Claude Haiku", "calling the parser tools", "eval/results_tool_calling_haiku.graded.json"),
        ("Claude Sonnet", "reading the raw report", "eval/results_prompt_only_sonnet.graded.json")]
stats = ""
for model, how, f in runs:
    g = json.load(open(ROOT / f))
    wrong = sum(len(r["wrong"]) for r in g["rows"])
    total = g["paths"] * len(g["field_accuracy"])
    cells = "".join(f'<i class="{"bad" if k < wrong else ""}"></i>' for k in range(total))
    stats += f"""<div class="stat"><div class="big">{wrong}<small>/{total}</small></div>
      <div class="who"><b>{model}</b> {how}</div><div class="grid180">{cells}</div></div>"""


def face(name, file, weight):
    return f"@font-face{{font-family:'{name}';src:url('file://{FONTS / file}') format('woff2');font-weight:{weight};}}"


fonts = "".join([face("Plex Cond", "ibm-plex-sans-condensed-latin-500-normal.woff2", 500),
                 face("Plex Cond", "ibm-plex-sans-condensed-latin-600-normal.woff2", 600),
                 face("Plex Cond", "ibm-plex-sans-condensed-latin-700-normal.woff2", 700),
                 face("Plex Sans", "ibm-plex-sans-latin-400-normal.woff2", 400),
                 face("Plex Sans", "ibm-plex-sans-latin-500-normal.woff2", 500),
                 face("Plex Mono", "ibm-plex-mono-latin-400-normal.woff2", 400)])

ticks = "".join(f'<div class="ax" style="left:{pct(x):.2f}%"><span>{x:.0f} ns</span></div>' if x < 4 else f'<div class="ax" style="left:{pct(x):.2f}%"></div>' for x in range(0, 6))

page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{fonts}
:root {{
  --bg:#0f1830;        /* layout-viewer night blue */
  --grid:#18244a;      /* routing grid */
  --ink:#eef2fb; --ink2:#a9b5d1; --ink3:#6f7ea3;
  --met1:#5b8def;      /* metal-1 blue: ordinary cells */
  --poly:#ff5d52;      /* poly red: the culprit */
  --li:#f2b84b;        /* amber: second contributor */
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:1200px; height:1500px; color:var(--ink); font-family:'Plex Sans',sans-serif; position:relative; overflow:hidden;
  background:
    linear-gradient(var(--grid) 1px, transparent 1px) 0 0/24px 24px,
    linear-gradient(90deg, var(--grid) 1px, transparent 1px) 0 0/24px 24px,
    var(--bg); }}
.raw {{ position:absolute; right:-40px; top:28px; width:640px; font:11.5px/1.55 'Plex Mono',monospace; color:#8ea0cc; opacity:.22;
  white-space:pre; transform:rotate(-0deg);
  -webkit-mask-image:linear-gradient(90deg, transparent 0%, #000 35%, #000 70%, transparent 100%),linear-gradient(180deg,#000 55%,transparent 100%);
  -webkit-mask-composite: source-in; }}
.wrap {{ position:relative; padding:76px 72px 0; }}
h1 {{ font-family:'Plex Cond'; font-weight:700; font-size:92px; line-height:.98; letter-spacing:-1.5px; max-width:760px; }}
.lede {{ margin-top:26px; font-size:24px; line-height:1.45; color:var(--ink2); max-width:640px; }}

.chart {{ margin-top:92px; }}
.chart h2 {{ font-family:'Plex Cond'; font-weight:600; font-size:30px; }}
.chart p {{ margin-top:8px; font-size:19px; color:var(--ink2); }}
.track {{ position:relative; height:64px; margin-top:150px; }}
.seg {{ position:absolute; top:0; height:64px; border-radius:3px; border-right:3px solid var(--bg); }}
.seg.plain {{ background:var(--met1); opacity:.55; }}
.seg.chain {{ background:var(--poly); box-shadow:0 0 28px rgba(255,93,82,.45); }}
.seg.hot {{ background:var(--li); }}
.budget {{ position:absolute; top:-14px; bottom:-40px; border-left:2px dashed var(--ink); }}
.budget span {{ position:absolute; bottom:-34px; right:10px; white-space:nowrap; font-size:17px; color:var(--ink); }}
.over {{ position:absolute; top:-8px; height:80px; border-radius:4px;
  background:repeating-linear-gradient(135deg, rgba(255,93,82,.28) 0 6px, transparent 6px 12px); outline:1px solid rgba(255,93,82,.6); }}
.over span {{ position:absolute; bottom:-46px; left:12px; white-space:nowrap; font-family:'Plex Cond'; font-weight:700; font-size:24px; color:var(--poly); }}
.axis {{ position:relative; height:40px; margin-top:12px; }}
.ax {{ position:absolute; top:0; height:8px; border-left:1px solid var(--ink3); }}
.ax span {{ position:absolute; top:12px; left:-14px; font-size:14px; color:var(--ink3); white-space:nowrap; }}
.call {{ position:absolute; bottom:82px; font-size:16px; line-height:1.35; color:var(--ink2); }}
.call .tick {{ position:absolute; left:0; bottom:-20px; height:20px; border-left:1px solid var(--ink3); }}
.call b {{ display:block; font-family:'Plex Cond'; font-weight:600; font-size:21px; color:var(--ink); }}
.call em {{ display:block; font-style:normal; }}
.c-chain b {{ color:var(--poly); }} .c-hot b {{ color:var(--li); }}
.c-chain .tick, .c-hot .tick {{ border-color:currentColor; }}
.c-chain {{ color:var(--ink2); }} .c-hot {{ white-space:nowrap; }}

.results {{ margin-top:96px; }}
.results h2 {{ font-family:'Plex Cond'; font-weight:600; font-size:30px; }}
.results p {{ margin-top:8px; font-size:19px; color:var(--ink2); max-width:900px; }}
.stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:44px; margin-top:34px; }}
.big {{ font-family:'Plex Cond'; font-weight:700; font-size:76px; line-height:1; }}
.big small {{ font-size:28px; font-weight:500; color:var(--ink3); margin-left:4px; }}
.who {{ margin-top:8px; font-size:18px; color:var(--ink2); }} .who b {{ color:var(--ink); font-weight:500; }}
.grid180 {{ display:grid; grid-template-columns:repeat(20, 1fr); gap:4px; margin-top:20px; width:330px; }}
.grid180 i {{ display:block; aspect-ratio:1; border-radius:2px; background:#2b3a66; }}
.grid180 i.bad {{ background:var(--poly); }}

.twist {{ margin-top:40px; padding-left:22px; border-left:3px solid var(--poly); font-size:22px; line-height:1.45; color:var(--ink); max-width:880px; }}
.foot {{ position:absolute; left:72px; right:72px; bottom:44px; display:flex; justify-content:space-between; align-items:baseline;
  font-size:17px; color:var(--ink3); }}
.foot b {{ color:var(--ink); font-weight:500; font-size:19px; }}
</style></head><body>
<div class="raw">{html.escape(raw)}</div>
<div class="wrap">
  <h1>Can an LLM read a timing report?</h1>
  <div class="lede">I gave three Claude setups 20 real OpenSTA paths and graded 180 answers each against a parser.</div>

  <div class="chart">
    <h2>Where the worst path's {sm['data_path_delay']:.3f} ns go</h2>
    <p>gcd on sky130hd, routed, clock tightened to 4 ns. Each bar is one cell, drawn by the parser.</p>
    <div class="track">{''.join(bars)}
      <div class="over" style="left:{pct(req):.2f}%;width:{pct(arr-req):.2f}%"><span>−{abs(path.slack):.3f} ns slack</span></div>
      <div class="budget" style="left:{pct(req):.2f}%"><span>required {req:.3f} ns</span></div>
      {callouts}
    </div>
    <div class="axis">{ticks}</div>
  </div>

  <div class="results">
    <h2>Wrong answers out of 180</h2>
    <p>Slack, data-path delay, stage count, worst stage and its share, max-fanout stage, max slew. Each square is one answer.</p>
    <div class="stats">{stats}</div>
    <div class="twist">The grader also caught a bug in my own parser. On a self-loop path, all three models counted 11 stages and my code said 10. The models were right.</div>
  </div>
</div>
<div class="foot"><span>Tools compute the numbers. The model writes the reasoning.</span><b>github.com/ZhaoYang-dexter/one-path-one-picture</b></div>
</body></html>"""

out = sys.argv[1] if len(sys.argv) > 1 else "assets/poster.png"
chrome = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=chrome if os.path.exists(chrome) else None, args=["--no-sandbox", "--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1200, "height": 1500}, device_scale_factor=2)
    html_file = ROOT / "tools/.poster.html"
    html_file.write_text(page)
    pg.goto(f"file://{html_file}"); pg.wait_for_timeout(500)
    pg.screenshot(path=out); b.close()
    html_file.unlink()
print("wrote", out)
