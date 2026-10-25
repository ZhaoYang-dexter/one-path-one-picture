"""Parse OpenSTA `report_checks -format full_clock_expanded -fields {slew cap fanout}` output.

Every number returned here is read straight from the report or is a sum/difference of
report numbers. The LLM never has to do arithmetic on raw text.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict

NUM = r"-?\d+\.\d+"
# cell arc line: [fanout cap] slew delay time ^|v pin (cell)
ARC = re.compile(rf"^\s*(?:(\d+)\s+({NUM})\s+)?({NUM})\s+({NUM})\s+({NUM})\s+([\^v])\s+(\S+)\s+\(([^)]+)\)\s*$")
# old-style separate net line: fanout cap ... name (net)
NET = re.compile(rf"^\s*(\d+)\s+({NUM})\s+\S+\s+\(net\)\s*$")
# two-number line: delay time description
INFO = re.compile(rf"^\s*(?:{NUM}\s+)?({NUM})\s+({NUM})\s+([A-Za-z].*\S)\s*$")
ONE = re.compile(rf"^\s*({NUM})\s+(data arrival time|data required time|slack \((MET|VIOLATED)\))\s*$")


@dataclass
class Stage:
    pin: str
    cell: str
    transition: str
    delay: float
    time: float
    slew: float
    fanout: int | None = None
    cap: float | None = None

    @property
    def instance(self) -> str:
        return self.pin.rsplit("/", 1)[0] if "/" in self.pin else self.pin

    @property
    def cell_type(self) -> str:
        return re.sub(r"^sky130_fd_sc_\w+?__", "", self.cell)


@dataclass
class Path:
    index: int
    startpoint: str
    endpoint: str
    path_group: str
    path_type: str
    launch: list = field(default_factory=list)       # clock stages before the startpoint clock pin
    data: list = field(default_factory=list)         # stages from launch clock pin/port to endpoint
    capture: list = field(default_factory=list)
    launch_info: dict = field(default_factory=dict)  # clock edge, input external delay ...
    capture_info: dict = field(default_factory=dict) # edge, uncertainty, setup ...
    arrival: float = 0.0
    required: float = 0.0
    slack: float = 0.0
    status: str = ""


def _split(text: str) -> list[str]:
    blocks, cur = [], []
    for line in text.splitlines():
        if line.startswith("Startpoint:") and cur:
            blocks.append(cur); cur = []
        cur.append(line)
    if cur:
        blocks.append(cur)
    return [b for b in blocks if b and b[0].startswith("Startpoint:")]


def parse_report(text: str) -> list[Path]:
    paths = []
    for i, lines in enumerate(_split(text)):
        hdr = {}
        for l in lines[:6]:
            if ":" in l:
                k, v = l.split(":", 1)
                hdr[k.strip()] = v.strip()
        p = Path(index=i,
                 startpoint=hdr.get("Startpoint", "").split(" (")[0],
                 endpoint=hdr.get("Endpoint", "").split(" (")[0],
                 path_group=hdr.get("Path Group", ""), path_type=hdr.get("Path Type", ""))
        section, last = "launch", None
        for l in lines:
            m = ARC.match(l)
            if m:
                fo, cap, slew, d, t, tr, pin, cell = m.groups()
                st = Stage(pin, cell, tr, float(d), float(t), float(slew),
                           int(fo) if fo else None, float(cap) if cap else None)
                if section == "launch":
                    # the startpoint clock pin / input port closes the launch clock section
                    if pin == p.startpoint or pin.startswith(p.startpoint + "/") or cell == "in" and pin == p.startpoint:
                        section = "data"
                    elif cell != "in" and not pin.endswith("/CLK") and p.launch and p.launch[-1].pin.endswith("/CLK"):
                        section = "data"
                if section == "capture" or (section == "data" and p.arrival):
                    section = "capture"; p.capture.append(st)
                elif section == "data":
                    p.data.append(st)
                else:
                    p.launch.append(st)
                last = st
                continue
            m = NET.match(l)
            if m and last is not None:
                last.fanout, last.cap = int(m.group(1)), float(m.group(2))
                continue
            m = ONE.match(l)
            if m:
                v, what = float(m.group(1)), m.group(2)
                if what == "data arrival time" and not p.arrival: p.arrival = v; section = "capture"
                elif what == "data required time": p.required = v
                elif what.startswith("slack"): p.slack, p.status = v, m.group(3)
                continue
            m = INFO.match(l)
            if m:
                d, t, desc = float(m.group(1)), float(m.group(2)), m.group(3)
                target = p.launch_info if section in ("launch", "data") and not p.arrival else p.capture_info
                key = re.sub(r"\s*\(.*\)", "", desc).strip()
                if key.startswith("clock ") and ("rise edge" in desc or "fall edge" in desc):
                    key = "clock edge"
                target[key] = d
        # input-port paths: the port arc itself is the first data stage
        if not p.data and p.launch:
            p.data, p.launch = p.launch, []
        paths.append(p)
    return paths


# ---------- derived quantities (the "tools") ----------

def _launch_clock_pin(p: Path):
    """The startpoint's clock pin (CLK, CK, CP ...): first data arc, followed by the same instance's output."""
    if len(p.data) >= 2 and p.data[0].instance == p.startpoint and p.data[1].instance == p.startpoint \
            and "/" in p.data[0].pin:
        return p.data[0]
    return None

def launch_latency(p: Path) -> float:
    """Clock arrival at the launching flop's clock pin, relative to the launch edge."""
    ck = _launch_clock_pin(p)
    return round(ck.time - p.launch_info.get("clock edge", 0.0), 3) if ck else 0.0


def capture_latency(p: Path) -> float:
    edge = p.capture_info.get("clock edge", 0.0)
    clk_pins = [s for s in p.capture if s.instance == p.endpoint and "/" in s.pin]
    return round(clk_pins[-1].time - edge, 3) if clk_pins else 0.0


def data_stages(p: Path) -> list[Stage]:
    """Stages after the startpoint (CLK->Q onward, or the input port onward)."""
    ck = _launch_clock_pin(p)
    return [s for s in p.data if s is not ck]


def cell_stages(p: Path) -> list[Stage]:
    """Logic cells between startpoint and endpoint: drops the input port and the endpoint pin."""
    st = data_stages(p)
    if st and (st[-1].cell == "out" or st[-1].instance == p.endpoint):
        st = st[:-1]                       # the endpoint pin / output port line is not a cell stage
    return [s for s in st if s.cell != "in"]


def data_path_delay(p: Path) -> float:
    start = p.data[0].time - p.data[0].delay if p.data else 0.0
    ck = _launch_clock_pin(p)
    if ck is not None:
        start = ck.time
    return round(p.arrival - start, 3)


def stage_table(p: Path) -> list[dict]:
    total = data_path_delay(p) or 1.0
    rows = []
    for s in data_stages(p):
        rows.append(dict(pin=s.pin, instance=s.instance, cell=s.cell_type, transition=s.transition,
                         delay=s.delay, arrival=s.time, slew=s.slew, fanout=s.fanout, cap=s.cap,
                         share_pct=round(100 * s.delay / total, 1)))
    return rows


def summary(p: Path) -> dict:
    st = data_stages(p)
    worst = max(st, key=lambda s: s.delay) if st else None
    fo = [s for s in st if s.fanout is not None]
    maxfo = max(fo, key=lambda s: s.fanout) if fo else None
    return dict(
        index=p.index, startpoint=p.startpoint, endpoint=p.endpoint, status=p.status,
        slack=p.slack, arrival=p.arrival, required=p.required,
        data_path_delay=data_path_delay(p), n_stages=len(cell_stages(p)),
        launch_latency=launch_latency(p), capture_latency=capture_latency(p),
        skew_against_path=round(launch_latency(p) - capture_latency(p), 3),
        setup=-p.capture_info.get("library setup time", 0.0),
        uncertainty=-p.capture_info.get("clock uncertainty", 0.0),
        worst_stage=worst.instance if worst else None,
        worst_stage_cell=worst.cell_type if worst else None,
        worst_stage_delay=worst.delay if worst else None,
        worst_stage_share_pct=round(100 * worst.delay / (data_path_delay(p) or 1), 1) if worst else None,
        max_fanout_stage=maxfo.instance if maxfo else None,
        max_fanout=maxfo.fanout if maxfo else None,
        max_slew_stage=max(st, key=lambda s: s.slew).instance if st else None,
        max_slew=max(s.slew for s in st) if st else None,
    )


def to_dict(p: Path) -> dict:
    d = asdict(p)
    d["summary"] = summary(p)
    return d
