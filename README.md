# ai-assets-report

skaile library of agent skills that build one static HTML report from live data or code, published under `@skaile-ai`.

| Skill | Description |
|---|---|
| `report` | Orchestrator: autopilot by default or size, profile and questions asked up front; lede, contents, reader notes, one static HTML report. |
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
| Entity tree with badge filter; a category's `default` value hides its chip so rows show only exceptions | report-table | `tree`, `badges.<cat>.default` |
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
| Readable prose | report-prose | rules 1-15, always on |
| Stats computed from the dump | report | `stats` `{count}`, `{rows}`, `{value, source}` |
| Lint (link density, lists without a lead, list-heavy sections, opening sentences, badge skew without `default`, one badge colour with two meanings, prose narrating its figure, "So …" recaps, repeated numbers, undiscussed stats, missing `at` under technical, …; catalogue in `python3 report/report/build.py --help`) | report | `build.py`, `--strict` |
| Change documents | report | `since` + previous `report.json` |

Every report is one HTML file built by the stdlib `report/build.py`; the extra libraries load from pinned CDNs and the page stays readable offline.

## Files

In `report/report/`:

- `SKILL.md`: the workflow; `references/` holds the `report.json` schema, brands, reader notes and the web-research profile.
- `template.html`: layout, type scale, badge shapes, tree filter, tabs, contents, link highlight, diagram interaction (hover, legend toggle, zoom), `map` and `board` controllers, `data`/`vega`/`mermaid` init, find box, reader notes. The theme tokens come from the brand. Alpine, the fonts and the extension libraries load from CDNs; offline the plain tables, `bars` and mermaid source show, the page keeps working.
- `brands/`: built-in brands (`skaile.json` with its logo, `github.json`). `lucide.json`: the icon set. `blocks/`: CSS and the browser runtime of `concepts` and `mock`, inlined into `<head>` once when a report uses them.
- `build.py`: renderer, choice checker, link checker and linter, stdlib only. It fails on unknown refs, nodes, kinds, icons, terms, state keys, badge defaults and listen targets, unbalanced child flows, links without a target, anchors rendered twice and invalid brands. `python3 build.py --help` lists every lint and its fix.
- `example.json`: one block of every type with its data in `example.data/` (the `board` screenshot is `example.data/board-screen.jpg`); the `video` block comes from `report-video/example.media/demo.block.json`. Build it from any directory: the `video` `src`/`poster`/`track` resolve next to the output HTML, else next to `report.json` (here `../report-video/example.media/`); the page gets `src` and `poster` rewritten relative to the output, and the `track` inlined as a `data:text/vtt` URI (not path-rewritten). `python3 build.py example.json example.html` prints `lint: 0 findings` (`example.html` is gitignored).
- `test_readability.py`: behavioural tests on the rendered HTML (citations, footnotes, source links and bibliography, explanation blocks, link and list lints, tree rows, media validation and path rewriting, reader-depth wrappers and control, report-wide find markers and landmarks, responsive table labels, `board` validation and links, brands, `concepts` and `mock` validation, lede, contents and the redundancy lints). Run the suite with the command under **Develop**.

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
