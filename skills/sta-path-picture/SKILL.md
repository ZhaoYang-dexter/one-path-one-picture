---
name: sta-path-picture
description: Turn a path from an OpenSTA report_checks file into a verified Mermaid diagram and a three-sentence diagnosis. Use when the user shares a static timing report, asks why a path fails timing, or wants a timing path drawn.
---

# STA path picture

The numbers in a timing diagnosis must come from the report, not from the model's reading of it.
So: tools compute, you reason.

## Steps

1. Find the paths: `python3 -m stapath list <report>`
2. For the path the user cares about (default: worst slack), get the numbers:
   - `python3 -m stapath summary <report> --path N`
   - `python3 -m stapath stages <report> --path N`
3. Draw it: `python3 -m stapath mermaid <report> --path N`. Do not hand-edit the numbers in the diagram.
4. Write exactly three sentences:
   - the biggest contributor and why (delay, share, slew, fanout from `stages`);
   - the clock check: launch vs capture latency and the skew (`summary`), or the second contributor;
   - the first fix to try, and how much delay it targets compared with the slack.
   Every number you write must appear in the tool output, or be a sum or difference of tool numbers.
5. If a stage of the data path looks evenly spread (no stage at 20% or more), say so: the path is
   limited by logic depth, not by one cell, and point at restructuring rather than sizing.

## Input format

OpenSTA:
```tcl
report_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3
```
The older layout with separate `(net)` lines is also accepted.

## As an MCP server

The same tools are available over MCP: `python3 -m stapath.mcp_server` (tools `list_paths`,
`path_summary`, `path_stages`, `path_mermaid`).
