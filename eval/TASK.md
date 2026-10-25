# Eval task (same questions in every mode)

For EVERY timing path, return one JSON object. Return a JSON array of 20 objects, nothing else.

| key | meaning |
|---|---|
| `index` | path number, 0-based, in report order |
| `slack` | slack in ns, signed |
| `data_path_delay` | data arrival time minus the time at the launch flop's CLK pin (clocks are ideal here, so this equals the data arrival time) |
| `n_stages` | number of logic cell stages: count the launch flop's CLK→Q arc and every cell after it; do NOT count the CLK pin line, the endpoint pin line (`.../D`) or an output port line (`(out)`) |
| `worst_stage` | instance name (e.g. `_295_`) of the data-path stage with the largest Delay |
| `worst_stage_delay` | that Delay in ns |
| `worst_stage_share_pct` | worst_stage_delay / data_path_delay × 100, one decimal |
| `max_fanout_stage` | instance name of the data-path stage with the largest Fanout |
| `max_fanout` | that Fanout |
| `max_slew` | largest Slew among data-path stages (CLK→Q onward, endpoint pin included), ns |
| `diagnosis` | one sentence: what limits this path |
