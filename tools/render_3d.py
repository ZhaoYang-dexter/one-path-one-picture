"""Screenshot a path3d HTML page (headless Chromium, software WebGL).

  python3 tools/render_3d.py page.html out.png [width height] [az el dist]
"""
import os, sys, json
from playwright.sync_api import sync_playwright

page_path, out = sys.argv[1], sys.argv[2]
w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1600, 1200)
view = dict(az=float(sys.argv[5]), el=float(sys.argv[6]), dist=float(sys.argv[7])) if len(sys.argv) > 7 else None
chrome = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=chrome if os.path.exists(chrome) else None,
                          args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                "--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
    pg.add_init_script("window.__STATIC__ = true;" + (f"window.__VIEW__ = {json.dumps(view)};" if view else ""))
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + os.path.abspath(page_path))
    pg.wait_for_function("window.__READY__ === true", timeout=60000)
    pg.wait_for_timeout(800)
    pg.screenshot(path=out)
    b.close()
print("wrote", out, "errors:", errs)
