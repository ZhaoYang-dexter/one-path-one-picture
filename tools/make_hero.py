"""Build the LinkedIn image: real OpenSTA path -> tool-drawn diagram + diagnosis, plus eval results.

  python3 tools/make_hero.py   (run from the repo root; needs Playwright + Chromium)
"""
import html, json, re, sys, pathlib, os
from playwright.sync_api import sync_playwright
sys.path.insert(0, ".")
from stapath.parser import _split

ROOT = pathlib.Path(".")
block = "\n".join(_split((ROOT / "reports/gcd_4ns_top40.rpt").read_text())[0])
block = block[: block.index("data required time")].rsplit("\n", 1)[0]  # launch side is enough
block += "\n  ...\n                                    -0.935   slack (VIOLATED)"
svg = (ROOT / "examples/gcd_worst_path.svg").read_text()
diag = [re.sub(r"^\d+\.\s*", "", l) for l in (ROOT / "examples/gcd_worst_path_diagnosis.md").read_text().splitlines() if l.strip()]
diag = "".join("<li>" + re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(l, quote=False)) + "</li>" for l in diag)

runs = [("Claude Haiku · reads the raw report", "eval/results_prompt_only_haiku.graded.json"),
        ("Claude Haiku · calls the parser tools", "eval/results_tool_calling_haiku.graded.json"),
        ("Claude Sonnet · reads the raw report", "eval/results_prompt_only_sonnet.graded.json")]
bars = ""
for label, f in runs:
    g = json.load(open(f))
    wrong = sum(len(r["wrong"]) for r in g["rows"])
    total = g["paths"] * len(g["field_accuracy"])
    dots = "".join('<i class="x"></i>' for _ in range(wrong)) or '<span class="none">none</span>'
    bars += f"""<div class="row"><div class="lab">{label}</div><div class="num"><b>{wrong}</b> / {total} wrong</div><div class="dots">{dots}</div></div>"""

page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root {{ --ink:#1d232b; --ink2:#5b6673; --muted:#8a96a3; --line:#e1e4e8; --accent:#c0392b; --bar:#3b6ea8; }}
* {{ box-sizing:border-box; margin:0; }}
body {{ width:1600px; height:2000px; background:#fff; color:var(--ink); font-family:Inter,"Helvetica Neue",Arial,sans-serif;
       padding:54px 56px 36px; display:flex; flex-direction:column; }}
h1 {{ font-size:50px; font-weight:750; letter-spacing:-0.8px; }}
.sub {{ font-size:23px; color:var(--ink2); margin:12px 0 30px; }}
.main {{ display:grid; grid-template-columns: 860px 1fr; gap:36px; flex:1; min-height:0; }}
.tag {{ font-size:17px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:var(--muted); margin-bottom:12px; }}
.tag.red {{ color:var(--accent); }}
pre {{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:12.4px; line-height:1.42; color:#3a434d; background:#f4f5f7;
       border:1px solid var(--line); border-radius:10px; padding:16px 16px; overflow:hidden; }}
.left {{ display:flex; flex-direction:column; min-height:0; }}
ol {{ margin-top:22px; padding:20px 24px 20px 48px; background:#fdf3f2; border-left:5px solid var(--accent); border-radius:8px;
      font-size:18px; line-height:1.42; }}
ol li + li {{ margin-top:8px; }}
code {{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:.86em; background:#fbe3e0; padding:1px 5px; border-radius:4px; }}
.right {{ display:flex; flex-direction:column; min-height:0; }}
.fig {{ flex:1; min-height:0; display:flex; justify-content:center; }}
.fig svg {{ height:100% !important; width:auto !important; max-width:100%; }}
.eval {{ margin-top:26px; border-top:1px solid var(--line); padding-top:20px; }}
.eval h2 {{ font-size:23px; font-weight:700; margin-bottom:6px; }}
.eval .note {{ font-size:17px; color:var(--ink2); margin-bottom:16px; }}
.row {{ display:grid; grid-template-columns: 380px 150px 1fr; align-items:center; gap:14px; margin:10px 0; }}\n.num {{ font-size:18px; color:var(--ink2); }} .num b {{ font-size:24px; color:var(--ink); }}\n.dots {{ display:flex; gap:6px; }} .x {{ width:14px; height:14px; border-radius:50%; background:var(--accent); display:inline-block; }}\n.none {{ font-size:16px; color:var(--muted); }}
.lab {{ font-size:19px; }}
.track {{ height:22px; background:#eef1f4; border-radius:4px; position:relative; }}
.bar {{ height:22px; background:var(--bar); border-radius:0 4px 4px 0; }}
.val {{ font-size:18px; color:var(--ink2); }} .val b {{ color:var(--ink); }}
.axis {{ display:grid; grid-template-columns: 430px 1fr 360px; gap:18px; font-size:14px; color:var(--muted); }}
.axis div:nth-child(2) {{ display:flex; justify-content:space-between; }}
.take {{ margin-top:14px; font-size:18.5px; line-height:1.4; }}
.foot {{ margin-top:14px; font-size:16px; color:var(--muted); display:flex; justify-content:space-between; }}
</style></head><body>
<h1>Can an LLM read a timing report?</h1>
<div class="sub">I tested it on real OpenSTA output, then moved the arithmetic and the drawing into tools.</div>
<div class="main">
  <div class="left"><div class="tag">Input · real report_checks path</div><pre>{html.escape(block)}</pre>
    <div class="tag red" style="margin-top:22px">Diagnosis · every number from the tools</div><ol>{diag}</ol>
    <div class="eval">
      <h2>Eval · 20 real paths × 9 fields = 180 answers</h2>
      <div class="note">Graded automatically against the parser: slack, data-path delay, stage count, worst stage, its delay and share, max-fanout stage and fanout, max slew.</div>
      {bars}
      <div class="take">Models read the report better than I expected. The win is that every number now comes from a tool, so every number is checkable. The grader even caught a bug in my own parser.</div>
    </div></div>
  <div class="right"><div class="tag red">Diagram · generated by code, not by the model</div><div class="fig">{svg}</div></div>
</div>
<div class="foot"><span>OpenSTA · public gcd design, sky130hd, routed with SPEF, clock tightened to 4 ns</span><span>github.com/ZhaoYang-dexter/one-path-one-picture</span></div>
</body></html>"""

out = sys.argv[1] if len(sys.argv) > 1 else "assets/llm_reads_timing.png"
chrome = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=chrome if os.path.exists(chrome) else None, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 2000})
    pg.set_content(page); pg.wait_for_timeout(300); pg.screenshot(path=out); b.close()
print("wrote", out)
