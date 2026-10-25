"""Minimal DEF/LEF reader: placed components, pins, and routed net geometry.

Enough for gcd_nangate45_route.def from the OpenROAD test data: COMPONENTS, PINS, NETS with
ROUTED/NEW wire segments and vias. Coordinates are returned in microns.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class Comp:
    name: str
    cell: str
    x: float
    y: float
    orient: str
    w: float = 0.0
    h: float = 0.0


@dataclass
class Pin:
    name: str
    net: str
    direction: str
    x: float
    y: float
    layer: str


@dataclass
class Wire:
    layer: str
    pts: list          # [(x, y), ...] in microns


@dataclass
class Via:
    layer: str         # lower routing layer the via sits on
    name: str
    x: float
    y: float


@dataclass
class Net:
    name: str
    conns: list = field(default_factory=list)   # [(inst or "PIN", pin)]
    wires: list = field(default_factory=list)
    vias: list = field(default_factory=list)


@dataclass
class Design:
    name: str
    dbu: int
    die: tuple
    comps: dict
    pins: dict
    nets: dict


def _sections(text, name):
    m = re.search(rf"^{name}\s+\d+\s*;(.*?)^END {name}", text, re.S | re.M)
    return m.group(1) if m else ""


def read_lef_sizes(lef_text: str) -> dict:
    sizes, cur = {}, None
    for line in lef_text.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "MACRO":
            cur = t[1]
        elif t[0] == "SIZE" and cur:
            sizes[cur] = (float(t[1]), float(t[3]))
        elif t[0] == "END" and len(t) > 1 and t[1] == cur:
            cur = None
    return sizes


def read_def(def_text: str, lef_sizes: dict | None = None) -> Design:
    dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", def_text).group(1))
    die = tuple(int(v) / dbu for v in re.search(r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", def_text).groups())
    name = re.search(r"^DESIGN (\S+)", def_text, re.M).group(1)

    comps = {}
    for st in _sections(def_text, "COMPONENTS").split(";"):
        m = re.search(r"-\s+(\S+)\s+(\S+).*?\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", st, re.S)
        if m:
            n, cell, x, y, o = m.groups()
            w, h = (lef_sizes or {}).get(cell, (0.0, 0.0))
            comps[n] = Comp(n, cell, int(x) / dbu, int(y) / dbu, o, w, h)

    pins = {}
    for st in _sections(def_text, "PINS").split(";"):
        m = re.search(r"-\s+(\S+)\s+\+\s+NET\s+(\S+)\s+\+\s+DIRECTION\s+(\S+)", st)
        if not m:
            continue
        lay = re.search(r"\+\s+LAYER\s+(\S+)", st)
        pl = re.search(r"\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)", st)
        pins[m.group(1)] = Pin(m.group(1), m.group(2), m.group(3),
                               int(pl.group(1)) / dbu if pl else 0.0, int(pl.group(2)) / dbu if pl else 0.0,
                               lay.group(1) if lay else "")

    nets = {}
    body = _sections(def_text, "NETS")
    for st in re.split(r";\s*\n", body):
        st = st.strip()
        if not st.startswith("-"):
            continue
        head = re.match(r"-\s+(\S+)", st)
        net = Net(head.group(1))
        conn_part = st.split("+", 1)[0]
        net.conns = re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", conn_part)
        if "ROUTED" in st:
            route = st[st.index("ROUTED") + len("ROUTED"):]
            for chunk in re.split(r"\bNEW\b", route):
                toks = chunk.replace("(", " ( ").replace(")", " ) ").split()
                if not toks:
                    continue
                layer, pts, via, i = toks[0], [], None, 1
                while i < len(toks):
                    if toks[i] == "(":
                        x, y = toks[i + 1], toks[i + 2]
                        # skip an optional extension value before ")"
                        j = i + 3
                        while toks[j] != ")":
                            j += 1
                        px = pts[-1][0] if x == "*" else int(x) / dbu
                        py = pts[-1][1] if y == "*" else int(y) / dbu
                        pts.append((px, py)); i = j + 1
                    elif toks[i] in ("+", "SHAPE", "STRIPE", "MASK", "RECT"):
                        i += 2 if toks[i] != "+" else 1
                    else:
                        via = toks[i]; i += 1
                if len(pts) >= 2:
                    net.wires.append(Wire(layer, pts))
                if via and pts:
                    net.vias.append(Via(layer, via, *pts[-1]))
        nets[net.name] = net
    return Design(name, dbu, die, comps, pins, nets)


def wire_length_by_layer(net: Net) -> dict:
    out = {}
    for w in net.wires:
        L = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(w.pts, w.pts[1:]))
        out[w.layer] = out.get(w.layer, 0.0) + L
    return out


def read_layer_rc(rc_text: str) -> dict:
    """Parse OpenROAD `set_layer_rc -layer L -resistance R -capacitance C` lines (per micron)."""
    rc = {}
    for m in re.finditer(r"^set_layer_rc\s+-layer\s+(\S+)\s+-resistance\s+(\S+)\s+-capacitance\s+(\S+)", rc_text, re.M):
        rc[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return rc


def safe_net_name(s: str) -> str:
    """DEF net names may carry escaped brackets, dots and $; map them to plain identifiers."""
    s = s.replace("\\", "")
    return s if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s) else "n_" + re.sub(r"[^A-Za-z0-9_]", "_", s)


def to_verilog(d: Design) -> str:
    """Structural Verilog from DEF connectivity (cells with no signal connections are skipped)."""
    by_inst: dict[str, list] = {}
    for n in d.nets.values():
        for inst, pin in n.conns:
            if inst != "PIN":
                by_inst.setdefault(inst, []).append((pin, n.name))

    port_bits = {p.net for p in d.pins.values() if re.fullmatch(r".+\[\d+\]", p.net)}

    def esc(s):
        if s in port_bits:                       # bus bit of a top-level port: keep bit-select form
            return s
        return safe_net_name(s)

    ports = sorted(d.pins.values(), key=lambda p: p.name)
    busses: dict[str, list] = {}
    scalars = []
    for p in ports:
        m = re.fullmatch(r"(.+)\[(\d+)\]", p.name)
        if m:
            busses.setdefault(m.group(1), []).append((int(m.group(2)), p.direction))
        else:
            scalars.append((p.name, p.direction))
    L = [f"module {d.name} ("]
    L.append(",\n".join("  " + n for n in [s for s, _ in scalars] + list(busses)) + ");")
    for n, dr in scalars:
        L.append(f"  {dr.lower()} {n};")
    for b, idx in busses.items():
        L.append(f"  {idx[0][1].lower()} [{max(i for i, _ in idx)}:{min(i for i, _ in idx)}] {b};")
    port_nets = {p.net for p in ports}
    for n in d.nets:
        if n not in port_nets:
            L.append(f"  wire {safe_net_name(n)};")
    for inst, conns in sorted(by_inst.items()):
        c = d.comps.get(inst)
        if not c:
            continue
        args = ", ".join(f".{pin}({esc(net)})" for pin, net in conns)
        L.append(f"  {c.cell} {esc(inst)} ({args});")
    L.append("endmodule")
    return "\n".join(L) + "\n"
