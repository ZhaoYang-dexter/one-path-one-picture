"""Build the before/after comparison image: raw timing report vs. Mermaid picture + diagnosis.

Usage: python3 tools/make_compare.py examples/setup_violation.rpt examples/setup_violation.svg \
           examples/setup_violation_diagnosis.md assets/before_after.png
"""
import html, re, sys, pathlib
from playwright.sync_api import sync_playwright

rpt, svg, diag, out = (pathlib.Path(p) for p in sys.argv[1:5])

report = html.escape(rpt.read_text())
svg_markup = svg.read_text()
lines = [re.sub(r"^\d+\.\s*", "", l) for l in diag.read_text().splitlines() if l.strip()]
lines = [re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(l).replace("&#x27;", "'")) for l in lines]
diag_html = "".join(f"<li>{l}</li>" for l in lines)

page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1600px; height: 2000px; background: #ffffff; font-family: Inter, "Helvetica Neue", Arial, sans-serif;
        color: #1d232b; padding: 56px 56px 40px; display: flex; flex-direction: column; }}
h1 {{ font-size: 46px; font-weight: 700; letter-spacing: -0.5px; }}
.sub {{ font-size: 24px; color: #5b6673; margin: 10px 0 34px; }}
.cols {{ display: grid; grid-template-columns: 720px 1fr; gap: 40px; flex: 1; min-height: 0; }}
.tag {{ font-size: 18px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 14px; }}
.before .tag {{ color: #8a96a3; }} .after .tag {{ color: #c0392b; }}
pre {{ font-family: "DejaVu Sans Mono", Menlo, monospace; font-size: 12.6px; line-height: 1.62; color: #3a434d;
       background: #f4f5f7; border: 1px solid #e1e4e8; border-radius: 10px; padding: 18px 16px; overflow: hidden; flex: 1; }}
.before {{ display: flex; flex-direction: column; min-height: 0; }}
.after {{ display: flex; flex-direction: column; min-height: 0; }}
.fig {{ flex: 1; min-height: 0; display: flex; justify-content: center; }}
.fig svg {{ height: 100% !important; width: auto !important; max-width: 100%; }}
ol {{ margin-top: 22px; padding: 22px 26px 22px 50px; background: #fdf3f2; border-left: 5px solid #c0392b; border-radius: 8px;
      font-size: 19.5px; line-height: 1.45; }}
ol li + li {{ margin-top: 8px; }}
code {{ font-family: "DejaVu Sans Mono", Menlo, monospace; font-size: 0.88em; background: #fbe3e0; padding: 1px 5px; border-radius: 4px; }}
.foot {{ margin-top: 26px; font-size: 18px; color: #8a96a3; display: flex; justify-content: space-between; }}
</style></head><body>
<h1>One timing path, one picture</h1>
<div class="sub">A single prompt turns a raw <b>report_checks</b> path into a diagram and a three-sentence diagnosis.</div>
<div class="cols">
  <div class="before"><div class="tag">Before · raw STA report</div><pre>{report}</pre></div>
  <div class="after"><div class="tag">After · one prompt</div>
    <div class="fig">{svg_markup}</div>
    <ol>{diag_html}</ol>
  </div>
</div>
<div class="foot"><span>Example path on public sky130 cells · OpenSTA format</span><span>Red ≥ 20% of data path · amber 10–20%</span></div>
</body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 2000}, device_scale_factor=1)
    pg.set_content(page)
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(out), full_page=False)
    b.close()
print("wrote", out)
