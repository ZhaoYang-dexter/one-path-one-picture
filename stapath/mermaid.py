"""Deterministic Mermaid renderer: every label comes from the parser, nothing from the model."""
from .parser import Path, data_stages, data_path_delay, launch_latency, capture_latency, summary

HOT, WARM = 20.0, 10.0
BUF_CELLS = ("buf_", "clkbuf_", "inv_", "clkinv_")


def _cell(s):
    return s.cell_type


def _is_buf(s):
    return _cell(s).startswith(BUF_CELLS)


def _groups(stages):
    """Collapse runs of 3+ back-to-back buffers/inverters, or of 3+ identical cells
    (e.g. a maj3 ripple-carry chain), into one group so the chain reads as one block."""
    def same(a, b):
        return (_is_buf(a) and _is_buf(b)) or _cell(a) == _cell(b)
    out, i = [], 0
    while i < len(stages):
        j = i + 1
        while j < len(stages) and same(stages[i], stages[j]):
            j += 1
        if j - i >= 3:
            out.append(stages[i:j]); i = j
        else:
            out.append([stages[i]]); i += 1
    return out


def render(p: Path) -> str:
    total = data_path_delay(p) or 1.0
    sm = summary(p)
    L = ['%%{init: {"flowchart": {"wrappingWidth": 360}}}%%', "flowchart TB"]
    klass = {"hot": [], "warm": [], "cool": [], "clk": []}

    def clock_block(name, title, stages):
        ids = []
        L.append(f'  subgraph {name}["{title}"]')
        L.append("    direction LR")
        clk = [s for s in stages if s.instance not in (p.startpoint, p.endpoint) and s.cell not in ("in",)]
        if not clk:
            L.append(f'    {name}0["ideal clock"]'); ids.append(f"{name}0")
        for k, s in enumerate(clk):
            nid = f"{name}{k+1}"
            L.append(f'    {nid}["{s.instance}<br/>{_cell(s)} · {s.delay:.3f} ns"]'); ids.append(nid)
        for a, b in zip(ids, ids[1:]):
            L.append(f"    {a} --> {b}")
        L.append("  end")
        klass["clk"].extend(ids)

    clock_block("LC", f"Launch clock · latency {launch_latency(p):.3f} ns", p.launch + p.data[:1])

    L.append(f'  subgraph DP["Data path · {total:.3f} ns · {sm["n_stages"]} cell stages"]')
    L.append("    direction TB")
    prev = None
    stages = data_stages(p)
    last = stages[-1] if stages else None
    for k, g in enumerate(_groups(stages)):
        nid = f"D{k+1}"
        d = round(sum(s.delay for s in g), 3)
        share = 100 * d / total
        if len(g) > 1:
            kind = "buffer chain" if _is_buf(g[0]) else "chain"
            label = f"{len(g)} x {_cell(g[0])} {kind} · {g[0].instance} to {g[-1].instance}<br/>{d:.3f} ns · {share:.0f}%"
        else:
            s = g[0]
            extra = []
            if s.fanout and s.fanout > 8: extra.append(f"fanout {s.fanout}")
            if s.slew >= 0.5: extra.append(f"slew {s.slew:.3f}")
            tag = " · " + " · ".join(extra) if extra else ""
            arc = " CK→Q" if s.instance == p.startpoint and s.pin.endswith(("/Q", "/QN", "/Q_N")) else ""
            if s is last and s.instance == p.endpoint and "/" in s.pin:
                label = f"{s.pin} · endpoint<br/>{d:.3f} ns · {share:.0f}%"
            else:
                label = f"{s.pin if s.cell in ('in','out') else s.instance} · {_cell(s)}{arc}{tag}<br/>{d:.3f} ns · {share:.0f}%"
        L.append(f'    {nid}["{label}"]')
        if prev: L.append(f"    {prev} --> {nid}")
        prev = nid
        klass["hot" if share >= HOT else "warm" if share >= WARM else "cool"].append(nid)
    L.append("  end")

    clock_block("CC", f"Capture clock · latency {capture_latency(p):.3f} ns", p.capture)

    sign = "−" if p.slack < 0 else "+"
    L.append(f'  S["slack {sign}{abs(p.slack):.3f} ns · {p.status}<br/>required {p.required:.3f} · arrival {p.arrival:.3f}"]')
    L += ["  LC --> DP", "  DP --> S", "  CC --> S",
          "  classDef hot  fill:#fde2e1,stroke:#c0392b,color:#7a1d14,stroke-width:2px",
          "  classDef warm fill:#fff1d6,stroke:#d68910,color:#6e4a07",
          "  classDef cool fill:#eef1f4,stroke:#8a96a3,color:#2c3640",
          "  classDef clk  fill:#e6f0fb,stroke:#3b78c4,color:#163a63",
          f"  classDef res fill:{'#c0392b' if p.slack < 0 else '#2e8b57'},stroke:#333,color:#ffffff,stroke-width:2px"]
    for k, ids in klass.items():
        if ids: L.append(f"  class {','.join(ids)} {k}")
    L += ["  class S res",
          "  style LC fill:#f7f9fc,stroke:#b8c6d8", "  style CC fill:#f7f9fc,stroke:#b8c6d8",
          "  style DP fill:#fbfbfa,stroke:#c9ccd1"]
    return "\n".join(L) + "\n"
