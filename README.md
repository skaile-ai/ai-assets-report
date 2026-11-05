# ai-assets-report

skaile library of agent skills that build one static HTML report from live data or code, published under `@skaile-ai`.

| Skill | Description |
|---|---|
| `report` | Orchestrator: size and profile asked up front or autopilot, question outline, reader notes, one static HTML report. |
| `report-prose` | Readable, argued prose for every report: claim and reason first, few links, lists as supplement. |
| `report-table` | Dumps, key detection, badge-filtered trees, interactive tables. |
| `report-flow` | Levelled DFD diagrams of code and pipelines. |
| `report-diagram` | Dependency canvas and mermaid notations. |
| `report-charts` | Bars and Vega-Lite charts with cross-filter. |
| `report-video` | Chaptered, narrated manim explainers with a brand look. |

## Use

```bash
skaile source add skaile-ai/ai-assets-report
skaile add skill:@skaile-ai/report
```

`report` requires the other six skills, so one `add` deploys the family. The skills find their scripts relative to their own directory (`<skill-dir>`), so they work in every harness skaile deploys to.

Needs `python3` (stdlib only). `report-video` also needs manim and ffmpeg; narration uses ElevenLabs (`ELEVENLABS_API_KEY`) or macOS `say`.

## Abilities

`report` asks which questions the report answers, then uses only the abilities those questions need.

| Ability | Skill | Block / mechanism |
|---|---|---|
| Question outline: the user picks the questions by chapter, one section per question | report | `ask` + `questions` in `<stem>.choice.json`, checked by `--check-choice` |
| Profiles (explanation, structure, inventory, critique, comparison, exploration, change, web-research) | report | top-level `profile`, skeleton seeds the outline |
| Sizes (small, medium, detailed, technical): question, sentence and ability budgets asked up front | report | `size` in `<stem>.choice.json`, checked by `--check-choice` and lint |
| Entity tree with badge filter | report-table | `tree` |
| Explanation blocks | report | `argument`, `example`, `compare`, `callout` |
| Source notes | report | `[@…]` → numbered notes, inline under `technical` |
| Static table | report-table | `table` |
| Sortable, searchable, paged table with CSV | report-table | `data` (simple-datatables) |
| Global find box | report | automatic with `tree` or `data` |
| Reader notes: mark text or a section, comment, copy for the agent | report | page script + `data-src` pointers |
| Autopilot: no questions, recommendations taken | report | `"mode": "autopilot"` in `<stem>.choice.json`, checked by `--check-choice` |
| Levelled DFD diagrams | report-flow | `flow`, `lineage`, `states` |
| Dependency canvas | report-diagram | `map` |
| Sequence, class, ER, gantt, mindmap, sankey, railroad | report-diagram | `mermaid` (link-checked `click` targets) |
| Simple bars | report-charts | `bars` |
| Charts with tooltips and selections | report-charts | `vega` (Vega-Lite) |
| Chart click filters a table | report-charts | `data.listen` |
| Badge toggle filters a chart | report-charts | tree `drives` a `vega` id |
| Explainer video with chapters, captions and voice | report-video | `video` + `brand.py`, `narrate.py`, `stitch.py` |
| Readable prose | report-prose | rules 1-14, always on |
| Stats computed from the dump | report | `stats` `{count}`, `{rows}`, `{value, source}` |
| Lint (link density, lists without a lead, list-heavy sections, badge skew, missing `at` under technical, …) | report | `build.py`, `--strict` |
| Change documents | report | `since` + previous `report.json` |

Every report is one HTML file built by the stdlib `report/build.py`; the extra libraries load from pinned CDNs and the page stays readable offline.

## Develop

```bash
cd report && python3 -m unittest discover -s report -p 'test_readability.py'
for m in report report-table report-flow report-diagram report-charts report-video; do
  python3 report/report/build.py report/$m/example.json /tmp/$m.html --strict
done
```

`skaile.manifest.yaml` is the publish inventory; `skaile library index ai-assets-report` keeps it in step with the files on disk.

## License

MIT, see [LICENSE](LICENSE).
