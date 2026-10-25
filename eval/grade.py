"""Grade model answers against parser ground truth.

  python3 eval/grade.py eval/paths.rpt eval/results_<mode>.json
Numbers must match to 0.0015 ns (0.15 for percentages). Instance names may be any of the
tied stages. Prints per-field accuracy and writes <results>.graded.json.
"""
import json, sys, re
sys.path.insert(0, ".")
from stapath.parser import parse_report, summary, data_stages, cell_stages

FIELDS = ["slack", "data_path_delay", "n_stages", "worst_stage", "worst_stage_delay",
          "worst_stage_share_pct", "max_fanout_stage", "max_fanout", "max_slew"]


def truth(p):
    s = summary(p)
    st = data_stages(p)
    mx = max(x.delay for x in st)
    fo = [x for x in st if x.fanout is not None]
    mf = max(x.fanout for x in fo)
    s["worst_stage"] = {x.instance for x in st if x.delay == mx}
    s["max_fanout_stage"] = {x.instance for x in fo if x.fanout == mf}
    return s


def ok(field, want, got):
    if got is None: return False
    if isinstance(want, set):
        return str(got).strip() in want or str(got).split("/")[0].strip() in want
    try: got = float(got)
    except (TypeError, ValueError): return False
    tol = 0.15 if field.endswith("pct") else 0 if field in ("n_stages", "max_fanout") else 0.0015
    return abs(got - want) <= tol + 1e-9


def diag_numbers(block: str, p, text: str):
    """Numbers with 2+ decimals quoted in a diagnosis must match a value in the path's report
    block or its derived summary, after rounding to the quoted precision.
    Returns (checked, supported)."""
    nums = re.findall(r"(?<![\w.])-?\d+\.\d{2,}(?![\w.])", text or "")
    pool = [abs(float(x)) for x in re.findall(r"-?\d+\.\d+", block)]
    pool += [abs(v) for v in summary(p).values() if isinstance(v, float)]
    ok_ = 0
    for n in nums:
        d = len(n.split(".")[1])
        if any(abs(round(v, d) - abs(float(n))) < 1e-9 for v in pool):
            ok_ += 1
    return len(nums), ok_


def main(rpt, res):
    text_all = open(rpt).read()
    paths = parse_report(text_all)
    from stapath.parser import _split
    blocks = ["\n".join(b) for b in _split(text_all)]
    raw = open(res).read()
    m = re.search(r"\[.*\]", raw, re.S)
    answers = {a.get("index"): a for a in json.loads(m.group(0))}
    per_field = {f: 0 for f in FIELDS}
    rows, all_right = [], 0
    dn_checked = dn_ok = 0
    for p in paths:
        t, a = truth(p), answers.get(p.index, {})
        row = {f: ok(f, t[f], a.get(f)) for f in FIELDS}
        for f, v in row.items(): per_field[f] += v
        all_right += all(row.values())
        c, k = diag_numbers(blocks[p.index], p, a.get("diagnosis", ""))
        dn_checked += c; dn_ok += k
        rows.append(dict(index=p.index, correct=row,
                         wrong={f: [sorted(t[f]) if isinstance(t[f], set) else t[f], a.get(f)] for f, v in row.items() if not v}))
    n = len(paths)
    total = sum(per_field.values())
    report = dict(results=res, paths=n, field_accuracy={f: round(100 * v / n, 1) for f, v in per_field.items()},
                  overall_field_accuracy=round(100 * total / (n * len(FIELDS)), 1),
                  paths_fully_correct=all_right,
                  diagnosis_numbers_checked=dn_checked, diagnosis_numbers_supported=dn_ok, rows=rows)
    json.dump(report, open(res.replace(".json", ".graded.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
