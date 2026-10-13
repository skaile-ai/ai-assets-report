---
name: report-html
description: "Build one static HTML report (data sheet, pipeline explanation, dependency map, inventory, coverage) from live data or code. Use for 'report', 'overview page', 'data sheet', 'how does X work as a page'. Orchestrates report-table, report-flow, report-diagram, report-charts, report-video."
metadata:
  version: 0.1.0
  publisher: mortegro
---

# report-html <question>

Answer `<question>` with one static HTML file: data-sheet style (GitHub Primer light, JetBrains Mono), every entity linked to every place it appears, badges that filter the tree on click. Collect data into `report.json`, render it with `build.py`; the template owns all styling.

## Process

1. **Pin the question and the data source.** Name the entities it is about and the 2-4 badge categories that classify them. Ask only if the question names no source.
   - **Dump freshness.** A dump is stale when its sources are newer than it or a path it cites no longer exists. Re-run it, or write `dump-<stem>.py` beside the report. The dump reads facts from files and never hard-codes code facts. Say in chat that it was re-run.
2. **Pick the profile.** Match the question against the table below, first hit wins. The profile fixes the skeleton and the pre-checked extensions. Set it as top-level `profile`.

   |Profile|Trigger words|Skeleton after the answer|Pre-checked|
   |---|---|---|---|
   |`explanation`|how does X work, what happens when, pipeline, run, import|L0 `flow` → `tabs`: per stage an L1 `flow` + `states` → `lineage` of types → data stores `table`|flow, tree|
   |`structure`|code structure, architecture, modules, features, layers|feature `table` → `tree` driving a layer `map`/`flow` → `tabs` per feature (entity card + runtime `flow`) → API `table`|tree, flow, map|
   |`inventory`|what exists, which repos/packages/screens, what depends on what, stale, missing|`tree` driving a `map` (deps) or the content tree → coverage `table`s → gaps `bullets`|tree, map, charts|
   |`critique`|review, critique, audit, what breaks, what is wrong, rate|findings `tree` (`sev`) driving a stage `flow` → `bars` per stage → findings `data` table (id, severity, evidence, location, recommendation; `key: "id"` links each row to its tree entity) → scorecard `table` → workarounds `table`|tree, data, flow, charts|
   |`comparison`|compare, X vs Y, which should we use, alternatives, options|candidates `tree` (badges: origin, licence, status) → criteria × candidates `table` (numeric, `{badge}` cells) → `vega` of the numeric criteria → verdict `steps` → sources `table` (url, read date)|tree, charts|
   |`exploration`|how many, distribution, over time, per month, outliers, which rows|`stats` from the dump → `vega` charts with a point selection → `data` tables listening to them → findings `bullets`|data, charts|
   |`change`|what changed, diff, since version|previous `report.json` + `since`; keeps its profile|as before|

   The skeleton is a list of block types, not a template: cut a slot where the data has nothing for it and say so in chat. Pre-checked lists feature keys from the table below.
3. **Recommend features.** Collect the signals (row counts, enum/number/date fields, the question's words), then make ONE `ask` call with two questions. (a) `profile`, single choice, `recommended` = the match. (b) `features`, `multi: true`, one option per row below that has a signal, option description = the signal with its number. `recommended` is a single index, so list the pre-checked rows first (the profile's pre-checked set plus every signal-triggered row), append ` ✓` to their label and start their description with `pre-checked: <reason>`. Each option label starts with its feature key in backticks. Start question (b) with `Profile: <p> (matched "<word>"); sections: <skeleton block types>`. Without an `ask` tool: print the same list in chat and wait for the answer. After the answer, map each selected option label to the backticked key at its start; ignore ` ✓`. Write the keys to `<stem>.choice.json` beside `report.json` as `{"profile": "<p>", "features": ["<key>", ...]}`. The find box is not an option: it appears automatically whenever a `tree` or `data` block exists.

   |Key|Feature (skill)|Pre-checked when|Signal to show|
   |---|---|---|---|
   |`tree`|Badges and tree (`report-table`): blocks `tree`, `table`, top-level `badges`|a dump with ≥ 1 collection exists|collection and row counts|
   |`data`|Interactive tables `data` (`report-table`)|a collection has > 30 rows|largest collection, its rows|
   |`charts`|Charts `vega`, `bars` (`report-charts`)|an enum field with ≥ 3 values, a numeric or a date field exists|the field names|
   |`crossfilter`|Chart → table cross-filter (`listen` on `data`/`vega`)|`data` and `charts` both checked|none|
   |`badge-chart`|Badge → chart|`tree` and `charts` checked, chart rows carry entity ids|none|
   |`flow`|Code flow `flow`/`lineage`/`states` (`report-flow`)|the question asks how code works, what becomes what, which states|the matched phrase|
   |`map`|Dependency `map` (`report-diagram`)|the question names repos, packages, services, modules, or a link table has > 15 nodes|node count|
   |`mermaid`|Mermaid (`report-diagram`)|the question asks for call order, classes, tables/keys, schedule, concept tree, grammar|the notation|
   |`video`|Video (`report-video`)|the user asks for a video, animation, explainer; otherwise offered unchecked ("renders in minutes, needs manim")|none|

   **Unchecked skeleton blocks.** When the skeleton names a block whose feature is unchecked, render the plain form and name the swap in chat:

   |Block|Plain form|
   |---|---|
   |`flow`, `lineage`|`steps`|
   |`states`|`bullets`|
   |`tree`|no `tree`, no `table`, no top-level `badges`; tables become `tabs` of entity cards, one tab per entity; entities get `tree: false`|
   |`vega`, `bars`|`stats` + `bullets`|
   |`map`|`bullets` of edges|
   |`mermaid`|`steps`|

   STE prose (`skill://report-asd-ste100`) is always on and not an option.
4. **Run the chosen extensions.** Read `skill://report-<x>` for each and follow its "Under report-html" branch: it returns blocks and entities, no build. Order inside a section: the answer first, then the `tree`, the diagrams it `drives`, `flow`/`mermaid`, charts and `data` tables, `video` last. A chart or diagram never precedes the prose that explains it.
5. **Shape `report.json`** (schema below). Entities and `[[links]]` are core regardless of the chosen features; without the `tree` feature, entities get `tree: false`. One entity per thing a reader may jump to; state each link once, in `parent` or `refs`; `build.py` computes the back-links. Prose per `skill://report-asd-ste100`. Every number comes from the dump or the code.
6. **Build:** `python3 ~/.agents/skills/report-html/build.py report.json <out>.html --check-choice <stem>.choice.json [--strict]`. It aborts on an unknown ref, parent, badge or colour: fix the data, not the check. `--check-choice` fails when the report holds a block (or top-level `badges`) of an unchosen feature key and prints `choice: <key> chosen=<yes|no> used=<yes|no>` per key; keys without a block (`crossfilter`, `badge-chart`, `find`) are reported, never fail. It must pass. Every `lint:` line is fixed or justified in chat: `orphan`, `prose … 0 links`, `badge <cat>=<val>` (value on > 85 % or < 5 % of the entities: make it a `meta` line or a column), `badge <cat>: mirrors tree level` (the values restate the nesting: drop the category), `kind … lacks meta`, `tree after the diagram it drives`, `stat … literal`. A bare-number stat from an older report gets a migration hint; give it a dump before `--strict`. A missing `at` on an edge is an error in the `explanation` and `structure` profiles. `--strict` turns every lint line into an error.
7. **Verify in a browser** at 1280 px and 390 px: `scrollWidth == 390`, no console errors, one link jumps and highlights, a link into a closed tab opens it; when badges exist, one badge toggle changes the counter. With no extension chosen: these base checks, plus every tab opens and every `[[link]]` resolves. Otherwise add the "Verify" list of every chosen extension.
8. **Location:** `<repo>/.scratch/reports/<topic>-<YYYY-MM-DD>[-vN].html`. All siblings share the stem: `<stem>.json`, `<stem>.choice.json`, `<stem>.data/` (dump), `<stem>.build/` (detector output), `<stem>.media/`. Earlier versions stay untouched. `open <file>`; give the answer in chat, not only the file.

## report.json

```
title, lang, profile, meta: [line], numbered: true, since?, data_dir?
stats: [[label, {count: "<collection>", where?: {field: value}} | {rows: "<table|data id>"} | {value, source}]]
badges: { <cat>: { label, shape: square|round|pill|dashed|text, filter: any|hide,
                   values: { <val>: { label?, color, desc? } } } }
entities: [{ id, title, label?, parent?, order?, tree?: false, muted?,
             badges: { <cat>: [val] }, meta: [inline], refs: [id] }]
sections: [{ title, sub?, id?, change?, blocks: [block] }]
```

- `stats`: `count` reads `<report stem>.data/<collection>.json` (or `data_dir`); a bare number fails.
- `shape`: one per category. `filter: any` keeps a node while one of its values is on; `hide` drops a node with a switched-off value. `color`: purple blue green gray orange pink teal yellow red navy brown ink.
- `tree: false`: link target only. Render places: a table row `anchor`, a tab `entity`. Without a `table`, gather link-only entities in one `tabs` block. Each entity renders in one place.
- Inline text: `` `code` ``, `[[id]]`, `[[id|label]]`. One `lang`; identifiers stay as in the code.
- Generic blocks: `p` (`text`); `bullets`, `steps` (`items: [inline]`); `tabs` (`id`, `label`, `tabs: [{entity? | label, summary?, blocks}]`, `kind?`, `numbered?`; three or more blocks of one kind go in one `tabs`, each tab opens with its `entity` card or a `summary`; the tab label falls back to the entity `label`, then `title`, backticks stripped); `html` (`html`, escape hatch).
- **Change document** (what changed): start from the previous `report.json`, set `change: new|changed|removed` on the smallest part that differs (node, edge, row, item; a tab or section only when all of it changed) and top-level `since`. Removed parts stay, struck through. Do not mark inside a `new` or `removed` part. `change` is allowed on sections, blocks, tabs, entities, table rows, list items, flow/map nodes and edges, lineage types/steps, states and transitions.

|Blocks|Skill|
|---|---|
|`tree`, `table`, `data`|`report-table`|
|`flow`, `lineage`, `states`|`report-flow`|
|`map`, `mermaid`|`report-diagram`|
|`bars`, `vega`|`report-charts`|
|`video`|`report-video`|

## Files

- `template.html`: theme tokens, layout, badge shapes, tree filter, tabs, link highlight, diagram interaction (hover, legend toggle, ⤢ zoom), `map` controller, `data`/`vega`/`mermaid` init, find box. Alpine, the font and the extension libraries load from CDNs; offline the plain tables, `bars` and mermaid source show, the page keeps working.
- `build.py`: renderer, link checker and linter, stdlib only. It fails on unknown refs, nodes, kinds and listen targets, unbalanced child flows, links without a target and anchors rendered twice.
- `example.json`: one block of every type with its data in `example.data/`. Build it from any directory: the `video` `src` resolves next to the output HTML, else next to `report.json` (here `../report-video/example.media/`), and the page gets the path relative to the output. `python3 build.py example.json example.html` prints `lint: 0 findings` (`example.html` is gitignored).
