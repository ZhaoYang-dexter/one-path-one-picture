"""Command-line tools over an OpenSTA report. Output is JSON (or Mermaid for `mermaid`).

  python3 -m stapath list     REPORT            one line per path: index, start, end, slack
  python3 -m stapath summary  REPORT --path N   slack, arrival, required, latencies, worst stage, max fanout
  python3 -m stapath stages   REPORT --path N   per-stage delay, slew, fanout, share of data path
  python3 -m stapath mermaid  REPORT --path N   diagram generated from the numbers above
"""
import argparse, json, sys
from .parser import parse_report, summary, stage_table
from .mermaid import render


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stapath", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "summary", "stages", "mermaid"])
    ap.add_argument("report")
    ap.add_argument("--path", type=int, default=0)
    a = ap.parse_args(argv)
    paths = parse_report(open(a.report).read())
    if a.cmd == "list":
        print(json.dumps([dict(index=p.index, startpoint=p.startpoint, endpoint=p.endpoint, slack=p.slack, status=p.status) for p in paths], indent=1))
        return
    p = paths[a.path]
    if a.cmd == "summary": print(json.dumps(summary(p), indent=1))
    elif a.cmd == "stages": print(json.dumps(stage_table(p), indent=1))
    else: sys.stdout.write(render(p))


if __name__ == "__main__":
    main()
