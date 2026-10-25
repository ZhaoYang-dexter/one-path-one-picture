"""MCP server exposing the timing-path tools to any MCP client (Claude Code, Claude Desktop, ...).

  python3 -m stapath.mcp_server          # stdio transport

Works with the MCP Python SDK 2.x (MCPServer) and 1.x (FastMCP).
"""
from __future__ import annotations
from .parser import parse_report, summary, stage_table
from .mermaid import render

try:                                   # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

server = _Server(
    name="stapath",
    instructions=("Tools over an OpenSTA report_checks file. Every number they return is read from the "
                  "report or computed from it. Quote these numbers; never estimate timing values yourself."),
)

_cache: dict[str, tuple[float, list]] = {}


def _paths(report: str):
    import os
    mtime = os.path.getmtime(report)
    if report not in _cache or _cache[report][0] != mtime:
        _cache[report] = (mtime, parse_report(open(report).read()))
    return _cache[report][1]


@server.tool()
def list_paths(report: str) -> list[dict]:
    """List every path in the report: index, startpoint, endpoint, slack, status."""
    return [dict(index=p.index, startpoint=p.startpoint, endpoint=p.endpoint, slack=p.slack, status=p.status)
            for p in _paths(report)]


@server.tool()
def path_summary(report: str, index: int = 0) -> dict:
    """Slack, arrival, required, data-path delay, clock latencies and skew, worst stage, max fanout and slew."""
    return summary(_paths(report)[index])


@server.tool()
def path_stages(report: str, index: int = 0) -> list[dict]:
    """Per-stage table: pin, instance, cell, delay, arrival, slew, fanout, cap, share of data-path delay."""
    return stage_table(_paths(report)[index])


@server.tool()
def path_mermaid(report: str, index: int = 0) -> str:
    """Mermaid diagram of the path, coloured by each stage's share of the data-path delay."""
    return render(_paths(report)[index])


if __name__ == "__main__":
    server.run()
