# ai-assets-report

skaile library of agent skills that build one static HTML report from live data or code, published under `@skaile-ai`.

| Skill | Description |
|---|---|
| `report-html` | Orchestrator: size and profile asked up front, question outline, one static HTML report. |
| `report-prose` | Readable, argued prose for every report: claim and reason first, few links, lists as supplement. |
| `report-table` | Dumps, key detection, badge-filtered trees, interactive tables. |
| `report-flow` | Levelled DFD diagrams of code and pipelines. |
| `report-diagram` | Dependency canvas and mermaid notations. |
| `report-charts` | Bars and Vega-Lite charts with cross-filter. |
| `report-video` | Chaptered, narrated manim explainers with a brand look. |

## Use

```bash
skaile source add skaile-ai/ai-assets-report
skaile add skill:@skaile-ai/report-html
```

`report-html` requires the other six skills, so one `add` deploys the family. The skills find their scripts relative to their own directory (`<skill-dir>`), so they work in every harness skaile deploys to.

Needs `python3` (stdlib only). `report-video` also needs manim and ffmpeg; narration uses ElevenLabs (`ELEVENLABS_API_KEY`) or macOS `say`.

## Abilities

`report-html` asks which questions the report answers, then uses only the abilities those questions need.

| Ability | Skill | Block / mechanism |
|---|---|---|
| Question outline: the user picks the questions by chapter, one section per question | report-html | `ask` + `questions` in `<stem>.choice.json`, checked by `--check-choice` |
| Profiles (explanation, structure, inventory, critique, comparison, exploration, change, web-research) | report-html | top-level `profile`, skeleton seeds the outline |
| Sizes (small, medium, detailed, technical): question, sentence and ability budgets asked up front | report-html | `size` in `<stem>.choice.json`, checked by `--check-choice` and lint |
| Entity tree with badge filter | report-table | `tree` |
| Explanation blocks | report-html | `argument`, `example`, `compare`, `callout` |
| Source notes | report-html | `[@…]` → numbered notes, inline under `technical` |
| Static table | report-table | `table` |
| Sortable, searchable, paged table with CSV | report-table | `data` (simple-datatables) |
| Global find box | report-html | automatic with `tree` or `data` |
| Levelled DFD diagrams | report-flow | `flow`, `lineage`, `states` |
| Dependency canvas | report-diagram | `map` |
| Sequence, class, ER, gantt, mindmap, sankey, railroad | report-diagram | `mermaid` (link-checked `click` targets) |
| Simple bars | report-charts | `bars` |
| Charts with tooltips and selections | report-charts | `vega` (Vega-Lite) |
| Chart click filters a table | report-charts | `data.listen` |
| Badge toggle filters a chart | report-charts | tree `drives` a `vega` id |
| Explainer video with chapters, captions and voice | report-video | `video` + `brand.py`, `narrate.py`, `stitch.py` |
| Readable prose | report-prose | rules 1-14, always on |
| Stats computed from the dump | report-html | `stats` `{count}`, `{rows}`, `{value, source}` |
| Lint (link density, lists without a lead, list-heavy sections, badge skew, missing `at` under technical, …) | report-html | `build.py`, `--strict` |
| Change documents | report-html | `since` + previous `report.json` |

Every report is one HTML file built by the stdlib `report-html/build.py`; the extra libraries load from pinned CDNs and the page stays readable offline.

## Develop

```bash
cd report && python3 -m unittest discover -s report-html -p 'test_readability.py'
for m in html table flow diagram charts video; do
  python3 report/report-html/build.py report/report-$m/example.json /tmp/$m.html --strict
done
```

`skaile.manifest.yaml` is the publish inventory; `skaile library index ai-assets-report` keeps it in step with the files on disk.

## License

MIT, see [LICENSE](LICENSE).
