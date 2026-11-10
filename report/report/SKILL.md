---
name: report
description: "Build one static HTML report read front to back: argued answer first, tables, trees, diagrams and charts as support. Use for 'report', 'overview page', 'data sheet', 'how does X work as a page'. Autopilot by default; 'report interactive: <question>' asks first; a pasted '# Notes on report' block revises it."
license: MIT
metadata:
  version: 0.8.0
  publisher: skaile-ai
  requires: "report-prose, report-table, report-flow, report-diagram, report-charts, report-video"
---

# report <question>

Answer `<question>` with one static HTML file a person reads front to back: each section argues its answer in prose, and tables, trees, diagrams and charts support it. Collect the data into `report.json` and render it with `build.py`; the template owns all styling. The extension skills (`report-prose`, `report-table`, `report-flow`, `report-diagram`, `report-charts`, `report-video`) sit beside this one at `<skill-dir>/../<name>`, where `<skill-dir>` holds this SKILL.md.

All files of one report share a stem: `<stem>.json`, `<stem>.choice.json`, `<stem>.data/` (dump), `<stem>.build/` (detector output), `<stem>.media/`.

## Modes

A report runs on autopilot unless the request contains `interactive`, `ask me` or `with questions`.

||interactive|autopilot (default)|
|---|---|---|
|Source|asked when the question names none|the one the question names, else the current repository; named in chat|
|Size + profile|one `ask` call (step 3)|the `recommended` size and profile|
|Questions|one `ask` call per chapter (step 5)|the pre-checked candidates|
|Extras|offered in step 5|none; `video` only when the question names a video or an animation|
|Chat line|the candidates left out|`Autopilot: size <s>, profile <p> (matched "<word>"), questions <ids>; left out: <ids or none>. Re-run with "interactive" to choose.`|

Under autopilot nothing asks and nothing waits. The steps compute the same lists as interactive mode and answer them as the table says. A revision from pasted notes copies the previous choice file, including its `mode`.

**Built in one task subagent, never ticketed.** A report gets no `## Ticket breakdown`, no `to-tickets` run and no fresh session, also when planned in plan mode. Under autopilot one `task` subagent runs steps 1-9 and writes the autopilot chat line; its task contains `autopilot` and the question and tells it to read `skill://report`. This session then does step 10. Under interactive mode steps 1-5 run here because they ask; steps 6-9 run in one `task` subagent, started right after the choice file is written, whose task names the question, the stem and directory, the dump, the choice file and the outline with its signals.

## Workflow

1. **Pin the question and the source.** Name the entities it is about and the 2-4 badge categories that classify them. Interactive: ask only if the question names no source. Autopilot: take the named source, else the current repository.
   - **Dump freshness.** A dump is stale when its sources are newer than it or a path it cites no longer exists. Re-run it, or write `dump-<stem>.py` beside the report. The dump reads facts from files and never hard-codes code facts. Say in chat that it was re-run.
2. **Pick the profile.** Match the question against this table, first hit wins. The profile's skeleton seeds the outline, one candidate per slot; it is not a template.

   |Profile|Trigger words|Skeleton after the answer|Leans on|
   |---|---|---|---|
   |`explanation`|how does X work, what happens when, pipeline, run, import|L0 `flow` → `example` (one item through the whole pipeline) → `tabs`: per stage an L1 `flow` + `states` → `lineage` of types → data stores `table`|flow, tree|
   |`structure`|code structure, architecture, modules, features, layers|feature `table` → `tree` driving a layer `map`/`flow` → `tabs` per feature (entity card + runtime `flow`) → API `table`|tree, flow, map|
   |`inventory`|what exists, which repos/packages/screens, what depends on what, stale, missing|`tree` driving a `map` (deps) or the content tree → coverage `table`s → gaps `argument`|tree, map, charts|
   |`critique`|review, critique, audit, what breaks, what is wrong, rate|findings `tree` (`sev`) → one `argument` per main finding (at most 3) → stage `flow` driven by the tree → `bars` per stage → findings `data` table (id, severity, evidence, location, recommendation; `key: "id"` links each row to its tree entity) → scorecard `table` → workarounds `table`|tree, data, flow, charts|
   |`comparison`|compare, X vs Y, which should we use, alternatives, options|candidates `tree` (badges: origin, licence, status) → criteria × candidates `table` (numeric, `{badge}` cells) → `vega` of the numeric criteria → `compare` of the two leading candidates → verdict `argument` → sources `table` (url, read date)|tree, charts|
   |`exploration`|how many, distribution, over time, per month, outliers, which rows|`stats` from the dump → `vega` charts with a point selection → `data` tables listening to them → findings `argument`|data, charts|
   |`change`|what changed, diff, since version|previous `report.json` + `since`; keeps its profile and its choice file|as before|
   |`web-research`|research a topic from the web, what do guidelines say, what helps, resources for patients or the public, report with sources and images|`callout` `answer`/`safety`/`action` → `p` (`reader: informed`) → `media` (licensed images) → `table` (responsive) → `flow` (`dir: down`) → `resources` (curated links) → `bullets` (`reader: professional`: evidence, limits); `sources` render the bibliography after the last section|callout, media, resources, table, flow|
   |`app-audit`|explore my app, app audit, how clear is my app, screens, navigation, ontology of an app|`callout` `answer` + `argument` (verdict, top 3 fixes) → objects `tree` (badges `class`, `shown-as`) + naming-conflict `table` → tasks `table` (anchors) + per-object CTA `tabs` → navigation `map` of screens + click-depth `bars` + first-click `table` → clarity scorecard `table` + rubric `bars` + findings `tree` (`sev`) + findings `data` → screens `gallery` → with `since`: change bar, findings status `table`, gallery before/after|tree, gallery, map, charts|

   `web-research` adds sources, media, resources and reader depths: read `references/web-research.md`.
3. **Size and profile.** Autopilot: take the recommended size and this step's profile. Interactive: one `ask` call with two single-choice questions, before any outline exists:
   - `size`: options `small`, `medium`, `detailed`, `technical`, label `` `<size>` <reader> ``, description `<questions> · <sentences> · <abilities>` from **Sizes**. `recommended` = `small` unless the request asks for more: `medium` on medium, main support, standard; `detailed` on detailed, full, everything; `technical` on technical, engineers, code-level, implementation.
   - `profile`: options = the nine profiles, label `` `<profile>` ``, description = its trigger words, `recommended` = the step 2 match.

   Without an `ask` tool: print both lists in chat and wait.
4. **Draft the outline.** Collect the signals: row counts, enum/number/date fields, the words of the question. Write candidate questions in the chapters the size allows. A chapter is one reader goal ("What exists", "How it runs", "What is wrong", "What to do"). A candidate is one question the data answers, with an id (`q1`, `q2`, …), the cheapest ability that answers it (key from **Abilities**) and its signal with the number. Sources: each skeleton slot, each ability whose "Offer when" holds, the user's own words. Drop a candidate without a signal and one that restates another. Every chapter holds 2-4 candidates (`small`: 1-2); a chapter that cannot reach 2 candidates merges into its neighbour. Pre-check as many as the size allows: the ones the answer cannot stand without; the profile's "Leans on" abilities break ties. `small` offers only `none`, `tree` and `bars` candidates; `technical` adds a `flow` candidate for every question that names code and a `data` candidate for every collection a candidate names.
5. **Choose the questions.** Autopilot: the pre-checked candidates. Interactive: one `ask` call:
   - one question per chapter, id `ch<n>`, `multi: true`, text = the chapter name. Options = its candidates, label `` `q<n>` <question> ``, description `<ability key> · <signal>`. List the pre-checked candidates first, append ` ✓` to their label and start their description with `pre-checked: <reason>`. The first chapter's text starts with `Size: <s>; Profile: <p> (matched "<word>"); <n> candidates, <k> pre-checked`.
   - `extras`, `multi: true`: the wiring abilities that apply (`crossfilter`, `badge-chart`) and `video`, label `` `<key>` <ability> ``. Omit it for `small`.

   Without an `ask` tool: print the lists in chat and wait. A typed answer becomes a new candidate; tag it yourself. The features are the questions' ability keys plus the selected extras. Write `<stem>.choice.json` once, always with `size`: `{"profile", "size", "mode": "ask"|"autopilot", "questions": [{"id", "chapter", "text", "feature"}], "features": ["<key>", ...]}`. Leave it as written; a failing check means the report is wrong.
6. **Run the chosen extensions.** Take each chosen ability to the skill **Abilities** names and follow its "Under report" branch (contract: **Under orchestration**). An extension adds only the selected blocks; its standalone recipe does not apply. Order inside a section: the answer first, then the `tree`, the diagrams it `drives`, `flow`/`mermaid`, a `board`, charts and `data` tables, `video` last. A chart or diagram never precedes the prose that explains it; every list, table, tree, chart and diagram follows a `p` that says what it shows, and a `tree` shares one lead `p` with the diagram it drives. The lede is prose only: a video goes last in the section whose question asked for it, else last in the first numbered section after the lede. Video: build once without the video block, render the video from that build, add the block, build again.
7. **Shape `report.json`** (schema: `references/report-json.md`; prose: `skill://report-prose`). The first section answers `<question>` within the size's sentence budget. It renders as the lede under the title: no heading, so do not restate the title in it. Then one section per chosen question, chapters in order: `question: "<id>"`, `title` = the question in at most 8 words, `sub` = the chapter. Each opens with its claim and reason within the budget, then holds only the blocks its candidate named. Show `stats` only for numbers the prose names once. A section's last sentence does not recap its figure. Create an entity only for a thing with a place on the page (a tree row, a table row `anchor`, a tab `entity`) that the reader may open; without such places there are no entities and no links. Without `tree`, entities get `tree: false`. State each link once, in `parent` or `refs`; the build computes back-links. Every number comes from the dump or the code.
8. **Build.** Run `python3 <skill-dir>/build.py report.json <out>.html --check-choice <stem>.choice.json --strict`; it aborts on unknown refs, badges and colours, on a failing `--check-choice` and on any `lint:` line: fix the data, not the check. Fix every `lint:` line; a lint you judge wrong you name and justify in the chat answer, and for that report build once without `--strict`. `python3 <skill-dir>/build.py --help` lists every check and its fix.
9. **Verify in a browser** at 1280 px and 390 px: `scrollWidth == 390`; no console errors; one link jumps and highlights; a link into a closed tab opens it; a note number opens or shows the section's note and highlights it; when badges exist, one badge toggle changes the counter. With a `gallery`: a thumbnail click opens `#gl-dlg` with its pins and notes; ←/→ moves to the neighbouring item; the Before toggle swaps the image; Escape closes and focus returns to the thumbnail; at 390 px the gallery is one column. Add `references/web-research.md` (Verify) for that profile, `references/notes.md` (Verify) for reader notes, and the Verify list of every chosen extension.
10. **Location and answer.** Write `<repo>/.scratch/reports/<topic>-<YYYY-MM-DD>[-vN].html` with its siblings; earlier versions stay untouched. `open <file>` and give the answer in chat, not only the file, plus the chat line from **Modes**.

## Sizes

|Size|Reader|Chapters and questions|Pre-checked|Opening sentences|Abilities offered|Evidence|
|---|---|---|---|---|---|---|
|`small`|wants the verdict on one screen|1 chapter, at most 2 questions|1 (the one the answer cannot stand without)|answer and each section at most 2|`none`, `tree`, `charts` as `bars` only, `gallery`; no extras question|notes in the prose; no evidence tables|
|`medium`|wants the answer and its main support|2-4 chapters, at most 6 questions|at most 5|at most 3|all|numbered notes; `at` optional|
|`detailed`|wants every finding|2-4 chapters, at most 8 questions|every candidate with a signal, up to the cap|at most 3|all; `data` offered for every collection with more than 30 rows|numbered notes; `at` optional|
|`technical`|will change the code|2-4 chapters, no cap|as `detailed`|at most 3|all; `flow` offered for every question that names code; `data` for every collection the chosen questions name, without the 30-row threshold|inline grey `[@…]` brackets; `at` on every `flow`/`map` edge (build error); every section after the first cites (lint); identifiers may stay `code`; tree rows show the id|

## Abilities

Tag each candidate with the cheapest ability that answers it: prose before a table, a table before a chart, a chart before a diagram. `skill://report-prose` is always on.

|Key|Blocks|Skill|Offer when (signal)|Needs|
|---|---|---|---|---|
|`none`|`p`, `argument`, `example`, `compare`, `callout`; `bullets`, `steps` after a lead `p`|core|always|—|
|`tree`|`tree`, `table`, top-level `badges`|`report-table`|a dump with ≥ 1 collection (collection and row counts)|—|
|`data`|`data` (sortable, searchable, paged, CSV)|`report-table`|a collection with > 30 rows (largest collection, its rows)|simple-datatables CDN|
|`charts`|`bars`, `vega`|`report-charts`|an enum field with ≥ 3 values, a numeric or a date field (the field names)|vega CDN (`bars`: none)|
|`crossfilter`|`listen` on `data`: a chart click filters a table|`report-charts`, `report-table`|candidates use `data` and `charts`|—|
|`badge-chart`|tree `drives` a chart: a badge toggle filters it|`report-charts`, `report-table`|candidates use `tree` and `charts`, chart rows carry entity ids|—|
|`flow`|`flow`, `lineage`, `states`|`report-flow`|the question names code or a pipeline (the matched phrase)|—|
|`map`|`map` (dependency canvas)|`report-diagram`|the question names repos, packages, services, modules, or a link table has > 15 nodes|—|
|`mermaid`|`mermaid` (sequence, class, ER, gantt, mindmap, sankey, railroad)|`report-diagram`|the question asks for one of these notations|mermaid CDN|
|`board`|`board` (moodboard canvas)|`report-diagram`|a moodboard, a canvas, or a before/after of screens|—|
|`concepts`|`concepts`, `mock`|`report-diagram`|UI variants, terms or a rename, dialogs compared|—|
|`video`|`video` (chaptered, narrated manim explainer)|`report-video`|the user asks for a video, animation or explainer; otherwise offered unchecked ("renders in minutes, needs manim; voice needs a TTS")|manim, ffmpeg, a `.media/` folder|
|`gallery`|`gallery` (screenshot grid with numbered note pins, lightbox, before/after)|core|what does screen X look like, where on the screen is the problem: screenshots exist (`<stem>.media/` count)|—|
|`find`|header find box over the whole page|core|automatic with a table of contents, a `tree` or a `data` block; never offered|—|

**`gallery` block** (core: `b_gallery` in `build.py`, `.gl`/`#gl-dlg` CSS and JS in `template.html`): `{type: "gallery", label?, items: [{src, title, alt?, caption?, entity?, badges?: {cat: [val]}, before?, change?, notes?: [{x, y, w?, h?, text, sev?, ref?}]}]}`. `src` and `before` are local files next to the report, rewritten relative to the output; `alt` defaults to `title`; note `x`, `y`, `w`, `h` are percent of the image (`w`/`h` draw a box), `sev` is an integer 0-4 and colours the pin, `ref` links the note to an entity, `entity` makes the item that entity's anchor. One grid, about three shots per row; under 640 px one column. Notes show in the lightbox and in print.

## Reading contract

The extensions point here.

- **Answer first.** The first section answers the question and renders as the lede: claim, reason, consequence, no heading. Counts, run details and source lists do not go in it. Provenance goes in two places only: top-level `meta` (a collapsed "Sources and run details" disclosure under the title) and `at` fields or `[@…]` citations next to the claim.
- **Link labels.** `[[id]]` shows the entity `label`, else its `title`, else the id. Give every entity a short human `title` and, when the title is long, a short `label`. Write `[[id|text]]` only when the sentence needs other wording; the full `title` stays on the link as a hover hint.
- **Citations per size.** Outside `technical` a `[@…]` renders as a numbered note at the end of its section; under `technical` as an inline grey bracket. A source id (`[@S1]`) always links to its bibliography record. Syntax: `references/report-json.md`.
- **Link-only entities.** An entity with `tree: false` renders in one place: a table row `anchor`, a tab `entity` or a gallery item `entity`. Without a `table`, gather link-only entities in one `tabs` block.
- **Ids are keys.** They are reader-facing only in tree rows under size `technical`.

## Under orchestration

The shared contract for every extension's "Under report" branch:

- The extension returns blocks and entities and does not build.
- Size `small` reaches only `report-table` (`tree`, `table`) and `report-charts` with `bars`.
- An entity has one owner: the first extension to create it owns it; the others reference it.
- The orchestrator runs the build and the base verify of step 9; the extension runs only its own Verify delta.

## References

- `references/report-json.md`: schema, block specs, page order (lede, chapter labels, contents), citation syntax, choice file, change documents.
- `references/brand.md`: brands, fonts, icons.
- `references/notes.md`: reader notes, revising from a pasted `# Notes on report` block, its verify list.
- `references/web-research.md`: reader depth, sources, media, resources, its verify list.
