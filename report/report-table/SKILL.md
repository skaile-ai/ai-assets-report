---
name: report-table
description: "Dump collections, detect keys/relations/enums with detect.py, and render entities as badge-filtered trees and interactive sortable/searchable tables. Use for inventories, 'which X exist', 'how many', data sheets."
license: MIT
metadata:
  version: 0.3.1
  publisher: skaile-ai
---

# report-table <question>

Answer `<question>` about what exists with data from the source: entities in a badge-filtered `tree`, plain `table` blocks and interactive `data` tables. Dump first, detect second, write `report.json` third.

Reading contract: follow `skill://report` (citations, labels, answer-first).

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

Edit the draft until it answers the question. The core schema (`badges`, `entities`, `sections`, inline text) is in `skill://report`, section "report.json".

- One entity per thing a reader may jump to. State each link once, in `parent` or `refs`; `build.py` computes the back-links (`←`).
- A badge category has 2-4 values that split the entities. The value most rows share is the category's `default`: its chip is hidden, so the row shows only exceptions; the build lints a value on more than 60 % of rows without `default`. A value on fewer than 5 % of the entities that carry the category is not a badge: move it to a `meta` line or a table column.
- One colour means one thing across all categories (lint).
- A category whose values equal the tree level (for example `stage` on parents and `finding` on their children) is not a badge: the nesting already shows it, and toggling it hides whole subtrees. Use `kind`, a `meta` line or a column. The build prints `badge <cat>: mirrors tree level, not a filter`.
- Every entity of one `kind` carries the same `meta` keys. The build prints `kind <val>: <id> lacks meta "<key>"` when at least 80 % of its siblings have the key. Fill the gap from the dump or drop the key from all.
- Every entity has one place on the page: a tree row, a table row `anchor`, or a tab `entity`. Prose links it only per `skill://report-prose` rule 6.
- Drop badges that only decorate. A title is the reader's word for the thing. Put the code name in one `meta` line when the reader needs it to find the thing. Meta lines naming code (function names, line ranges) belong to size `technical`.
- Titles and `meta` values are short human labels: a few words, no ids, no paths outside size technical. Put a source in a grey `[@path:line]` token in a `meta` value or a table cell, never in a title.
- Each entity has one home: one tree row or one table row `anchor`. Do not repeat its full evidence in a tree row and in a table. Keep the evidence where the entity lives; other places name it in words, link it once per section, or use a `{ref}` cell.

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
- The header find box searches the whole page and filters every tree and every data table; its counter reads `<n> matches · <rows> rows` (tree and table rows added up).

**List and diagram of the same entities** (repos in a tree and in a dependency map, screens in a tree and in a flow): one section: a lead `p`, the tree, the diagram right after it. Set `drives: [<diagram id>]` on the tree and `ref` on every diagram node that is one of its entities, so the tree's badges filter both: a `map` hides the filtered boxes and their edges and refits; other diagrams fade them. Say in the tree's `hint` that the diagram follows. Badges that matter for the diagram (owner, role, a `hide` flag such as "stale") belong in the tree's `filter`.

## Alone

Standalone: run `skill://report` with this feature preselected.

## Under report

Shared contract: `skill://report`, Under orchestration. Delta:

1. Do Dump, Detect and Shape. Return the entities and only the blocks of the chosen features (`tree` with its `badges`, `table`, `data`). A `data` choice alone adds no `tree`.
2. Section order: the prose that answers first, then for each block a lead `p` and the block: the `tree`, the diagrams it `drives`, `table` and `data`.
3. Size: `small` returns one `tree` and no `table` or `data`; `technical` returns a `data` table for every collection the chosen questions name, with every column of the dump.
4. Add `data` only when a collection has more than 30 rows (the orchestrator pre-checks it on that signal).

## Verify

Base checks (1280/390 px, console) are in `skill://report`. Delta:

- One tree badge toggle changes the counter; the tree's reset restores it.
- One link jumps to its entity and highlights it. A link into a closed tab opens that tab.
- Data table: a header click sorts (a number column sorts numerically); typing in the table's search box cuts the rows and the info line; the page size and the pager change the visible rows; the CSV button downloads `<id>.csv`.
- Key column: its links jump to the entity row.
- Find box: typing a term filters tree rows and data rows, and `#findn` shows `<n> matches · <rows> rows` (tree and table rows added up); clearing the box restores both.
- Offline (CDN blocked): the plain table shows all rows and the page has no layout break.
