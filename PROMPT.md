# The prompt

Copy everything inside the block, then paste one timing path from `report_checks` (OpenSTA) or `report_timing` (PrimeTime) at the end.

```text
You are a senior STA engineer. Below is ONE timing path from a static timing report.

Produce exactly two things.

1) A Mermaid diagram (```mermaid fenced block) that follows these rules:
   - Use `flowchart LR`.
   - Three subgraphs: "Launch clock", "Data path", "Capture clock".
   - One node per cell arc, in path order. Node label: instance name, cell type
     without the library prefix, and the arc delay, e.g. "_0418_<br/>nand2_1<br/>1.05 ns".
     Put "fanout N" on the label when the driven net's fanout is above 8.
   - Collapse 3 or more back-to-back buffers/inverters into one node labelled
     "N x buf_1 chain<br/><total delay> ns".
   - Colour each data-path node by its share of the data-path delay
     (data arrival time minus launch clock latency):
       classDef hot   fill:#fde2e1,stroke:#c0392b,color:#7a1d14   (>= 20%)
       classDef warm  fill:#fff1d6,stroke:#d68910,color:#6e4a07   (10% to 20%)
       classDef cool  fill:#eef1f4,stroke:#8a96a3,color:#2c3640   (< 10%)
   - Add one final node with the slack, required time and arrival time.
   - Use only numbers that appear in the report, or sums of them. Do not invent values.

2) A diagnosis of exactly three sentences:
   - Sentence 1: the single biggest contributor and why (delay, slew, fanout).
   - Sentence 2: the second contributor, or why the clock is or is not the problem
     (state launch and capture latency and the resulting skew).
   - Sentence 3: the first fix to try, and how much delay it targets compared with
     the violation.

No other text.

<paste the timing path here>
```

## Why these rules

- **Fixed structure** (three subgraphs, one node per arc) means every path comes out looking the same, so two pictures can be compared side by side.
- **Colour by share of data-path delay**, not by absolute delay, so the hot spot stands out on fast and slow paths alike.
- **Buffer-chain collapsing** keeps the picture short and makes a chain show up as one obvious block.
- **"Only numbers from the report"** is the most important line. Without it, models tend to round or make up delays.
- **Three sentences, fixed roles** keeps the output to something an engineer actually reads.
