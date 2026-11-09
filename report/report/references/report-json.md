# report.json

The data file `build.py` renders. Read it in workflow step 7 (`skill://report`). The extension skills specify their own blocks (`report-flow/NOTATION.md`, `report-diagram`, `report-table`, `report-charts`, `report-video`).

```
title, lang, profile, meta: [inline line], numbered: true, since?, data_dir?, brand?
stats: [[label, {count: "<collection>", where?: {field: value}} | {rows: "<table|data id>"} | {value, source}]]
badges: { <cat>: { label, shape: square|round|pill|dashed|text, filter: any|hide, default?: "<val>",
                   values: { <val>: { label?, color, desc? } } } }
entities: [{ id, title, label?, parent?, order?, tree?: false, muted?,
             badges: { <cat>: [val] }, meta: [inline], refs: [id] }]
sections: [{ title, sub?, id?, question?: "<choice id>", change?, blocks: [block] }]
sources?: [{ id, title, url, publisher?, year?, kind?, read?, note? }]
readers?: { default?: "informed", label?, levels: [{ id: general|informed|professional, label, description? }] }
```

## Page order and sections

- Reading order: header (logo, title, collapsed "Sources and run details" from top-level `meta`, German "Quellen und Laufdetails", open in print; find box over the whole page, with a clear button and a labelled count, whenever there is a table of contents, a `tree` or a `data` block; table of contents), the first section, `stats` and the change summary, the other sections, the bibliography.
- The first section is the **lede**: it renders under the title with no heading and no number (`<section class="lede">`), in a larger size. It holds prose only: no figure, table or video. Its `title` is not shown, so the lede text does not restate the page title. It has no section pencil for reader notes; text-selection comments still work.
- The other sections are numbered from 1 (`numbered: false` drops the numbers). Each gets the id `id` or `s-<n>`, an `h2` with id `<id>-h` and a `#` permalink.
- `sub` names the section's chapter. A chapter label renders once, before the first section of a run of sections with the same `sub`; a missing `sub` renders none.
- With 4 or more numbered sections (web-research: always), the header gets a table of contents grouped by `sub`, and the page a skip link to `<main id="main">`. The lede is not listed; the bibliography is.

## Keys

- `stats`: `count` reads `<report stem>.data/<collection>.json` (or `data_dir`); a bare number fails. Show a stat only for a number the prose names once.
- `brand`: see `brand.md`.
- `shape`: one per category. `filter: any` keeps a node while one of its values is on; `hide` drops a node with a switched-off value. `color`: purple blue green gray orange pink teal yellow red navy brown ink. One colour means one thing across all categories (lint).
- `default`: the value most entities share. Its chip is hidden on tree rows, so a row shows only its exceptions; the legend still lists the value and its toggle, and filtering is unchanged. An unknown value fails the build: `badge <cat>: default <v> is not one of its values`.
- `tree: false`: link target only. Render places: a table row `anchor`, a tab `entity`. Without a `table`, gather link-only entities in one `tabs` block. Each entity renders in one place.
- Inline text: `` `code` ``, `[[id]]`, `[[id|label]]`, `[@source text]`. One `lang`; identifiers stay as in the code.

## Citation syntax

`[@source text]` works in any inline text (`p`, `bullets`, `steps`, `callout`, `argument`, `example`, `compare`, captions, notes, entity `meta`, top-level `meta`). The text is non-empty, on one line, and holds no `[`, `]` or backtick. Spaces, a path without a line, `:line` and `:start-end` are allowed. A malformed token stays literal text. A token inside a backtick code span stays literal. Example: `The import rejects bad dates [@src/import.py:88-94].`

Outside size `technical` a citation renders as a superscript number linking to `#n-<section>-<n>` in the section's notes list (German "Belege"); the same text in one section reuses its number, and the list opens when a number is clicked and in print. A section with a single note shows it inline under the prose instead of a collapsed list. Top-level `meta` and the bibliography always stay inline grey brackets.

Structured `at` fields (evidence tables, `lineage`, `states`) render as an inline grey bracket in every size; they never become notes. Write the bare value there, without `[@…]`. A source path does not go in a title, a node label, a tab label or an axis label.

## Blocks

- Generic blocks: `p` (`text`); `bullets`, `steps` (`items: [inline]`); `callout` (`tone`: `answer`|`safety`|`action`|`note`, `title`, `text`, `items?: [inline]`; the tone name is printed as the label. Callouts are neutral; `action` gets an ink frame and only `safety` is red; under `web-research`, `safety` and `action` stay visible at every reader depth); `tabs` (`id`, `label`, `tabs: [{entity? | label, summary?, blocks}]`, `kind?`, `numbered?`; three or more blocks of one kind go in one `tabs`, each tab opens with its `entity` card or a `summary`; the tab label falls back to the entity `label`, then `title`, backticks stripped; the card omits a title equal to the tab label); `html` (`html`, escape hatch).
- Explanation blocks (every profile, feature `none`), neutral frames with small grey labels. `argument` (`claim: inline`, `reasons: [inline]` 1-3, `conclusion: inline`; renders the claim in bold, then "Because", "So"; errors: ``argument: `claim` is required and must not be empty`` (same for `conclusion`), ``argument: `reasons` needs 1 to 3 non-empty items``). `example` (`title: text`, `setup: inline`, `steps: [inline]` 1-6, `result: inline`; renders the title in bold, then "Result"; errors: ``example: `{k}` is required and must not be empty`` for `title`, `setup`, `result`, ``example: `steps` needs 1 to 6 non-empty items``). `compare` (`title: text`, `columns: [{label, text?: inline, items?: [inline]}]` exactly 2, `verdict: inline`; renders the title in bold, two columns, one under 640 px, then "Verdict"; errors: ``compare: `columns` needs exactly 2 columns``, ``compare: column {n} needs `label` and `text` or `items` ``, ``compare: `{k}` is required and must not be empty`` for `title`, `verdict`). German labels (`lang: de`): Gründe, Folgerung, Ergebnis, Fazit.
- `gallery` (core, every size): `items: [{src, title, alt?, caption?, entity?, badges?: {cat: [val]}, before?, change?, notes?: [{x, y, w?, h?, text, sev?, ref?}]}]`, `label?`; `src`/`before` are local files next to the report, note `x`/`y`/`w`/`h` are percent 0-100, `sev` 0-4, `ref` an entity id. Renders a screenshot grid with numbered pins; a click opens a lightbox with the notes, ←/→, and a Before/Now toggle when `before` is set.
- `web-research` blocks: `media`, `resources`, `reader` and `sources`; see `web-research.md`.
- `table` blocks in every profile emit `data-label` on each cell; under 640 px the rows render as labelled cards. `data` tables keep scroll and paging.
- Figures: a legend identical to one shown earlier on the page collapses into a "Legend" disclosure. Diagrams keep at least 75 % of their drawn size; on a narrow page they scroll inside their frame, which shows a shadow at the scrollable edge. A vertical flow (`flow` with `dir: down`) scrolls inside its frame at ≥75 % scale; the page keeps `scrollWidth == 390`.
- `video` goes last in the section whose question asked for it, else last in the first numbered section after the lede.
- Tree: the badge legend and the filter controls sit in a "Filters" disclosure, open on a wide page and closed under 800 px.

## Choice file and `--check-choice`

`<stem>.choice.json`: `{"profile": "<p>", "size": "<s>", "mode": "ask"|"autopilot", "questions": [{"id", "chapter", "text", "feature"}], "features": ["<key>", ...]}`. `mode` is `ask` after an `ask` answer, `autopilot` under autopilot; a missing `mode` means `ask`, a missing `size` means `medium`.

`--check-choice` prints `choice: <key> chosen=<yes|no> used=<yes|no>` per feature key, then `choice: size <s>` and `choice: mode <m>`. It fails when:

- the report holds a block (or top-level `badges`) of an unchosen ability, or uses `crossfilter` (`listen` on a `data` block) or `badge-chart` (a tree `drives` a `vega`/`bars` block) without choosing it;
- the choice file lists more questions than the size allows, a feature key the size does not offer, or a `vega` block appears under `small`;
- with `questions`: a section after the first carries no chosen `question`, a chosen question has no section or two, or a question's ability is missing from `features`;
- `mode` is neither `ask` nor `autopilot`; under `autopilot` also when `questions` is missing (`--check-choice: autopilot needs "questions"`) or when `features` hold a key no question names (`none` and `find` excepted).

A bare-number stat from an older report gets a migration hint; give it a dump before `--strict`. A missing `at` on an edge is an error only in size `technical`.

## Change document

What changed: start from the previous `report.json`, set `change: new|changed|removed` on the smallest part that differs (node, edge, row, item; a tab or section only when all of it changed) and top-level `since`. Removed parts stay, struck through. Do not mark inside a `new` or `removed` part. `change` is allowed on sections, blocks, tabs, entities, table rows, list items, flow/map nodes and edges, lineage types/steps, states and transitions, board canvases, lanes, cards, lane changes and gallery items. With `since` and no mark anywhere, the change bar says "none".
