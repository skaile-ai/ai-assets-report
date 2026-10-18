---
name: report-table
description: "Dump collections, detect keys/relations/enums with detect.py, and render entities as badge-filtered trees and interactive sortable/searchable tables. Use for inventories, 'which X exist', 'how many', data sheets."
metadata:
  version: 0.1.0
  publisher: skaile-ai
---

# report-table <question>

Answer `<question>` about what exists with data from the source: entities in a badge-filtered `tree`, plain `table` blocks and interactive `data` tables. Dump first, detect second, write `report.json` third.

Reading contract: follow `skill://report-html` (citations, labels, answer-first).

## Dump

Write a script that dumps every relevant collection or table as-is, one `<collection>.json` per file (array, Directus `{"data": [...]}`, or `.jsonl`) into `<report>.data/`. The dump stays next to the report. Every number in the report comes from it; label estimates as such.

Done when each collection that the question names has a file and its row count is known.

## Detect

`python3 <skill-dir>/detect.py <report>.data <report>.build [--title T] [--lang de] [--max N] [--skip c1,c2]`

It infers from values, not names:

- primary keys and business keys (unique identifier-shaped fields such as `external_id`). Up to 3 % duplicates are allowed and listed as `DUPLICATE KEYS`. Report each one in the answer: it is a data error.
- foreign keys (≥ 90 % of the values hit one collection's keys), also inside objects and arrays (`sources[].chapter`).
- hierarchies (self-reference, or a join table with two keys into one collection) and enums (badge candidates).

It writes `schema.json`, `schema.ts` (refs as `Target["key"]`) and a draft `report.json`. Read the console summary. Correct a false link with `--skip` or by editing the draft. Skip this step when the data has no keys to detect and write `report.json` by hand.

## Shape

Edit the draft until it answers the question. The core schema (`badges`, `entities`, `sections`, inline text) is in `skill://report-html`, section "report.json".

- One entity per thing a reader may jump to. State each link once, in `parent` or `refs`; `build.py` computes the back-links (`←`).
- A badge category has 2-4 values that split the entities. A value on more than 85 % or on fewer than 5 % of the entities that carry the category is not a badge: move it to a `meta` line or a table column. The build prints `badge <cat>=<val>: <n> of <m> entities (<pct> %)`.
- A category whose values equal the tree level (for example `stage` on parents and `finding` on their children) is not a badge: the nesting already shows it, and toggling it hides whole subtrees. Use `kind`, a `meta` line or a column. The build prints `badge <cat>: mirrors tree level, not a filter`.
- Every entity of one `kind` carries the same `meta` keys. The build prints `kind <val>: <id> lacks meta "<key>"` when at least 80 % of its siblings have the key. Fill the gap from the dump or drop the key from all.
- Every entity gets a link: a tree row, a table row `anchor`, or a tab `entity`. Link it from prose with `[[id]]`.
- Drop badges that only decorate. Rename titles so the reader finds the thing by the word the code uses.
- Titles and `meta` values are short human labels: a few words, no ids, no paths. Put a source in a grey `[@path:line]` token in a `meta` value or a table cell, never in a title.
- Each entity has one home: one tree row or one table row `anchor`. Do not repeat its full evidence in a tree row and in a table. Keep the evidence where the entity lives and link to it from other places with `[[id]]` or `{ref}` cells.

## Blocks

| type | fields |
|---|---|
| `tree` | `filter: [cat]` (the first is the kind badge, or `kind`), `count: <kind val>`, `count_label`, `hint`, `reset`, `drives?: [figure id]` |
| `table` | `columns: [label]`, `numeric: [column index]`, `rows: [[cell]]` or `[{anchor, cells}]`; cell = inline text, number, `{ref, text?}`, `{refs: [id]}`, `{badge: [cat, val]}` |
| `data` | `id`, `label?`, `columns: [{label, key, type?: number\|date\|string}]`, `rows: [{<key>: cell}]`, `key?: <column key>`, `page?: 25`, `listen?: {chart, param, field}` |

- `table`: use it up to about 30 rows or when rows need an `anchor` as link target. Use `data` above that, or when the reader wants to sort, search or export.
- `data`: sortable, searchable, paginated (10/25/50/100), a CSV button. Cells use the `table` cell forms. Put numbers as JSON numbers (`type: "number"` sorts numerically) and dates as ISO 8601 (`2026-10-13`: text order is date order). The build fails on a row key that is no column key, a `type` outside number/date/string, a `key` that is no column key, and on a `listen` target that is no `vega` block, or a `listen.field` that is no column key. Empty `rows` render one `—` row with a warning.
- `key`: the column whose values are entity ids. Each value renders as a link to the entity and the row carries `data-e`. A value that is no entity id stays plain text.
- `listen`: a point selection of a `vega` block (`skill://report-charts`) filters this table. `field` is the column that holds the selected values. The cell text of that column must equal the chart value (plain strings; a badge cell shows its label, not its value).
- The header find box (`tree` or `data` in the report) filters every tree and every data table; its counter adds both.

**List and diagram of the same entities** (repos in a tree and in a dependency map, screens in a tree and in a flow): one section, the tree first, the diagram right after it. Set `drives: [<diagram id>]` on the tree and `ref` on every diagram node that is one of its entities, so the tree's badges filter both: a `map` hides the filtered boxes and their edges and refits; other diagrams fade them. Say in the tree's `hint` that the diagram follows. Badges that matter for the diagram (owner, role, a `hide` flag such as "stale") belong in the tree's `filter`.

## Alone

1. Dump, detect and shape (above) for `<question>`.
2. Write `report.json` with the entities, the `badges`, one `tree` and the `table` or `data` blocks the question needs, plus one `p` that states the answer. Copy the shape from `example.json`.
3. Build: `python3 <skill-dir>/../report-html/build.py report.json <out>.html`. The build aborts on an unknown ref, parent, badge or colour: fix the data, not the check. Read every `lint:` line and fix it or justify it in chat.
4. Verify (below), then `open <out>.html` and state the answer in chat.
5. Location: `<repo>/.scratch/reports/<topic>-<YYYY-MM-DD>[-vN].html`, dump in `<topic>-<date>[-vN].data/`, detector output in `<topic>-<date>[-vN].build/`. When any of these names already exists, use the first free `-vN` (`-v2`, `-v3`, …) for all of them. Never overwrite an earlier report.

## Under report-html

1. Do Dump, Detect and Shape. Return the entities and only the blocks of the chosen features (`tree` with its `badges`, `table`, `data`) to the orchestrator's section plan; do not build. A `data` choice alone adds no `tree`.
2. Section order: the prose that answers first, then the `tree`, then the diagrams it `drives`, then `table` and `data` blocks.
3. Size (`skill://report-html` **Sizes**): `small` returns one `tree` and no `table` or `data`; `technical` returns a `data` table for every collection the chosen questions name, with every column of the dump.
4. Add `data` only when a collection has more than 30 rows (the orchestrator pre-checks it on that signal).
5. The orchestrator builds and runs the core checks. Run the Verify list below for your blocks.

## Verify

Open the built file at 1280 px and at 390 px.

- `document.documentElement.scrollWidth == 390` at 390 px; no console errors.
- One tree badge toggle changes the counter; the tree's reset restores it.
- One link jumps to its entity and highlights it. A link into a closed tab opens that tab.
- Data table: a header click sorts (a number column sorts numerically); typing in the table's search box cuts the rows and the info line; the page size and the pager change the visible rows; the CSV button downloads `<id>.csv`.
- Key column: its links jump to the entity row.
- Find box: typing a term filters tree rows and data rows, and `#findn` shows `<tree rows> · <table rows>`; clearing the box restores both.
- Offline (CDN blocked): the plain table shows all rows and the page has no layout break.
