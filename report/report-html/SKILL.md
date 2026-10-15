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
2. **Pick the profile.** Match the question against the table below, first hit wins. Set it as top-level `profile`. The skeleton seeds the outline in step 3, one candidate question per slot; it is not a template.

   |Profile|Trigger words|Skeleton after the answer|Leans on|
   |---|---|---|---|
   |`explanation`|how does X work, what happens when, pipeline, run, import|L0 `flow` → `tabs`: per stage an L1 `flow` + `states` → `lineage` of types → data stores `table`|flow, tree|
   |`structure`|code structure, architecture, modules, features, layers|feature `table` → `tree` driving a layer `map`/`flow` → `tabs` per feature (entity card + runtime `flow`) → API `table`|tree, flow, map|
   |`inventory`|what exists, which repos/packages/screens, what depends on what, stale, missing|`tree` driving a `map` (deps) or the content tree → coverage `table`s → gaps `bullets`|tree, map, charts|
   |`critique`|review, critique, audit, what breaks, what is wrong, rate|findings `tree` (`sev`) driving a stage `flow` → `bars` per stage → findings `data` table (id, severity, evidence, location, recommendation; `key: "id"` links each row to its tree entity) → scorecard `table` → workarounds `table`|tree, data, flow, charts|
   |`comparison`|compare, X vs Y, which should we use, alternatives, options|candidates `tree` (badges: origin, licence, status) → criteria × candidates `table` (numeric, `{badge}` cells) → `vega` of the numeric criteria → verdict `steps` → sources `table` (url, read date)|tree, charts|
   |`exploration`|how many, distribution, over time, per month, outliers, which rows|`stats` from the dump → `vega` charts with a point selection → `data` tables listening to them → findings `bullets`|data, charts|
   |`change`|what changed, diff, since version|previous `report.json` + `since`; keeps its profile and its choice file|as before|
3. **Draft the outline.** Collect the signals: row counts, enum/number/date fields, the words of the question. Write candidate questions in 2-4 chapters. A chapter is one reader goal ("What exists", "How it runs", "What is wrong", "What to do"). A candidate is one question the data answers, with an id (`q1`, `q2`, …), the cheapest ability that answers it (key from **Abilities**; `none` for prose) and its signal with the number. Sources: each skeleton slot, each ability whose "Offer when" holds, the user's own words. Drop a candidate without a signal and a candidate that restates another. Done when every chapter holds 2-4 candidates and each candidate names its signal. Pre-check at most 5: the ones the answer cannot stand without; the profile's "Leans on" abilities break ties.
4. **Ask once.** One `ask` call:
   - `profile`: single choice, `recommended` = the match.
   - one question per chapter, id `ch<n>`, `multi: true`, text = the chapter name. Options = its candidates, label `` `q<n>` <question> ``, description `<ability key> · <signal>`. `recommended` is a single index, so list the pre-checked candidates first, append ` ✓` to their label and start their description with `pre-checked: <reason>`. The first chapter's text starts with `Profile: <p> (matched "<word>"); <n> candidates, <k> pre-checked`.
   - `extras`, `multi: true`: the wiring abilities that apply to the candidates (`crossfilter`, `badge-chart`) and `video`, label `` `<key>` <ability> ``.

   Without an `ask` tool: print the same lists in chat and wait. After the answer: the questions are the selected candidates; a typed answer becomes a new candidate, tag it yourself. The features are the ability keys of the questions plus the selected extras. Write `<stem>.choice.json` beside `report.json` once, from the answer: `{"profile": "<p>", "questions": [{"id", "chapter", "text", "feature"}], "features": ["<key>", ...]}`. Leave it as written; a failing check means the report is wrong. In chat, name the candidates left out in one line.
5. **Run the chosen extensions.** Read `skill://report-<x>` for each chosen ability and follow its "Under report-html" branch: it returns blocks and entities, no build. Order inside a section: the answer first, then the `tree`, the diagrams it `drives`, `flow`/`mermaid`, charts and `data` tables, `video` last. A chart or diagram never precedes the prose that explains it.
6. **Shape `report.json`** (schema below). The first section answers `<question>` in at most 3 sentences. Then one section per chosen question, chapters in order: `question: "<id>"`, `title` = the question in at most 8 words, `sub` = the chapter. Each opens with its answer in at most 3 sentences, then holds only the blocks its candidate named. Entities and `[[links]]` are core regardless of the chosen abilities; without `tree`, entities get `tree: false`. One entity per thing a reader may jump to; state each link once, in `parent` or `refs`; `build.py` computes the back-links. Prose per `skill://report-asd-ste100`. Every number comes from the dump or the code.
7. **Build:** `python3 ~/.agents/skills/report-html/build.py report.json <out>.html --check-choice <stem>.choice.json [--strict]`. It aborts on an unknown ref, parent, badge or colour: fix the data, not the check. `--check-choice` must pass. It fails when the report holds a block (or top-level `badges`) of an unchosen ability and prints `choice: <key> chosen=<yes|no> used=<yes|no>` per key; keys without a block (`crossfilter`, `badge-chart`, `find`) are reported, never fail. With `questions` in the choice file it also fails when a section after the first carries no chosen `question`, a chosen question has no section or two, or a question's ability is missing from `features`. Every `lint:` line is fixed or justified in chat: `orphan`, `prose … 0 links`, `badge <cat>=<val>` (value on > 85 % or < 5 % of the entities: make it a `meta` line or a column), `badge <cat>: mirrors tree level` (the values restate the nesting: drop the category), `kind … lacks meta`, `tree after the diagram it drives`, `stat … literal`. A bare-number stat from an older report gets a migration hint; give it a dump before `--strict`. A missing `at` on an edge is an error in the `explanation` and `structure` profiles. `--strict` turns every lint line into an error.
8. **Verify in a browser** at 1280 px and 390 px: `scrollWidth == 390`, no console errors, one link jumps and highlights, a link into a closed tab opens it; when badges exist, one badge toggle changes the counter. With no extension chosen: these base checks, plus every tab opens and every `[[link]]` resolves. Otherwise add the "Verify" list of every chosen extension.
9. **Location:** `<repo>/.scratch/reports/<topic>-<YYYY-MM-DD>[-vN].html`. All siblings share the stem: `<stem>.json`, `<stem>.choice.json`, `<stem>.data/` (dump), `<stem>.build/` (detector output), `<stem>.media/`. Earlier versions stay untouched. `open <file>`; give the answer in chat, not only the file.

## Abilities

Tag each candidate with the cheapest ability that answers it: prose before a table, a table before a chart, a chart before a diagram. STE prose (`skill://report-asd-ste100`) is always on.

|Key|Ability (skill: blocks)|Answers questions like|Offer when (signal)|Page cost|Needs|
|---|---|---|---|---|---|
|`none`|Prose (core: `p`, `bullets`, `steps`)|why, what to do, verdict|always|1-6 sentences|—|
|`tree`|Badge-filtered tree, static tables (`report-table`: `tree`, `table`, top-level `badges`)|what exists, which X has Y|a dump with ≥ 1 collection (collection and row counts)|one row per entity|—|
|`data`|Sortable, searchable, paged table with CSV (`report-table`: `data`)|which rows, list every X|a collection with > 30 rows (largest collection, its rows)|one table, 25 rows a page|simple-datatables CDN|
|`charts`|Bars, Vega-Lite charts with tooltips and selections (`report-charts`: `bars`, `vega`)|how many, distribution, over time, compare counts|an enum field with ≥ 3 values, a numeric or a date field (the field names)|one figure|vega CDN (`bars`: none)|
|`crossfilter`|A chart click filters a table (`listen` on `data`)|which rows are behind this bar|candidates use `data` and `charts`|none|—|
|`badge-chart`|A badge toggle filters a chart (tree `drives`)|the same counts for one category|candidates use `tree` and `charts`, chart rows carry entity ids|none|—|
|`flow`|Levelled DFD (`report-flow`: `flow`, `lineage`, `states`)|how does X work, what becomes what, which states|the question names code or a pipeline (the matched phrase)|L0 + one figure per stage|—|
|`map`|Dependency canvas (`report-diagram`: `map`)|what depends on what|the question names repos, packages, services, modules, or a link table has > 15 nodes (node count)|one large canvas|—|
|`mermaid`|Sequence, class, ER, gantt, mindmap, sankey, railroad (`report-diagram`: `mermaid`)|who calls whom in which order, which tables and keys|the question asks for one of these notations (the notation)|one figure|mermaid CDN|
|`video`|Manim explainer (`report-video`: `video`)|show it as an animation|the user asks for a video, animation, explainer; otherwise offered unchecked ("renders in minutes, needs manim")|one player|manim, a `.media/` folder|
|`find`|Global find box (core)|—|automatic with a `tree` or `data` block; never offered|header field|—|

## report.json

```
title, lang, profile, meta: [line], numbered: true, since?, data_dir?
stats: [[label, {count: "<collection>", where?: {field: value}} | {rows: "<table|data id>"} | {value, source}]]
badges: { <cat>: { label, shape: square|round|pill|dashed|text, filter: any|hide,
                   values: { <val>: { label?, color, desc? } } } }
entities: [{ id, title, label?, parent?, order?, tree?: false, muted?,
             badges: { <cat>: [val] }, meta: [inline], refs: [id] }]
sections: [{ title, sub?, id?, question?: "<choice id>", change?, blocks: [block] }]
```

- `stats`: `count` reads `<report stem>.data/<collection>.json` (or `data_dir`); a bare number fails.
- `shape`: one per category. `filter: any` keeps a node while one of its values is on; `hide` drops a node with a switched-off value. `color`: purple blue green gray orange pink teal yellow red navy brown ink.
- `tree: false`: link target only. Render places: a table row `anchor`, a tab `entity`. Without a `table`, gather link-only entities in one `tabs` block. Each entity renders in one place.
- Inline text: `` `code` ``, `[[id]]`, `[[id|label]]`. One `lang`; identifiers stay as in the code.
- Generic blocks: `p` (`text`); `bullets`, `steps` (`items: [inline]`); `tabs` (`id`, `label`, `tabs: [{entity? | label, summary?, blocks}]`, `kind?`, `numbered?`; three or more blocks of one kind go in one `tabs`, each tab opens with its `entity` card or a `summary`; the tab label falls back to the entity `label`, then `title`, backticks stripped); `html` (`html`, escape hatch).
- **Change document** (what changed): start from the previous `report.json`, set `change: new|changed|removed` on the smallest part that differs (node, edge, row, item; a tab or section only when all of it changed) and top-level `since`. Removed parts stay, struck through. Do not mark inside a `new` or `removed` part. `change` is allowed on sections, blocks, tabs, entities, table rows, list items, flow/map nodes and edges, lineage types/steps, states and transitions.

## Files

- `template.html`: theme tokens, layout, badge shapes, tree filter, tabs, link highlight, diagram interaction (hover, legend toggle, ⤢ zoom), `map` controller, `data`/`vega`/`mermaid` init, find box. Alpine, the font and the extension libraries load from CDNs; offline the plain tables, `bars` and mermaid source show, the page keeps working.
- `build.py`: renderer, link checker and linter, stdlib only. It fails on unknown refs, nodes, kinds and listen targets, unbalanced child flows, links without a target and anchors rendered twice.
- `example.json`: one block of every type with its data in `example.data/`. Build it from any directory: the `video` `src` resolves next to the output HTML, else next to `report.json` (here `../report-video/example.media/`), and the page gets the path relative to the output. `python3 build.py example.json example.html` prints `lint: 0 findings` (`example.html` is gitignored).
