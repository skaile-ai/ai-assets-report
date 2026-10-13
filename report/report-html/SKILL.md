---
name: report-html
description: "Build one static HTML report (data sheet, pipeline explanation, dependency map, inventory, coverage) from live data or code. Use for 'report', 'overview page', 'data sheet', 'how does X work as a page'. Orchestrates report-table, report-flow, report-diagram, report-charts, report-video."
metadata:
  version: 0.1.0
  publisher: mortegro
---

# report-html <question>

Answer `<question>` with one static HTML file: technical data-sheet style (GitHub Primer light, JetBrains Mono), every entity linked to every place it appears, badges that filter the tree on click.

Do not hand-write the page. Collect data into `report.json`, render it with `build.py`. The template owns all styling; adapt it only when a new block type truly needs it.

## Process

1. **Pin the question.** Name the entities it is about (e.g. area → chapter → screen, source chapter) and the 2-4 badge categories that classify them (kind, audience, origin, status). Ask only if the question names no data source. If the question asks how code or a pipeline works, read [`DIAGRAMS.md`](DIAGRAMS.md) now: it replaces steps 2-3 with fact collection from the code and sets the diagram levels.
2. **Pull live data.** Dump every relevant collection/table as-is with a script, one `<collection>.json` per file (array, or Directus `{"data": [...]}`; `.jsonl` works), into `<report>.data/`; never estimate counts. The dump stays next to the report so numbers can be re-checked.
3. **Detect entities and connections:** `python3 ~/.agents/skills/report-table/detect.py <report>.data <report>.build [--title T] [--max N] [--skip c1,c2]`. It infers from values, not names:
   - primary keys and business keys (unique identifier-shaped fields such as `external_id`; ≤3 % duplicates allowed and listed as `DUPLICATE KEYS`: report them, they are data errors);
   - foreign keys (≥90 % of values hit one collection's keys), also inside objects and arrays (`sources[].chapter`);
   - hierarchies (self-reference, or a join table with two keys into one collection) and enums (badge candidates).

   It writes `schema.json`, `schema.ts` (minimal TypeScript types, refs as `Target["key"]`) and a draft `report.json`. Read its console summary and correct false links with `--skip` or by editing the draft, never by trusting it blindly.
4. **Shape `report.json`** (schema below) for the question: rename titles, drop noise badges, add prose sections, tables and charts. One entity per thing a reader may want to jump to; state each link once, in `parent` or `refs`. `build.py` computes the back-links (`←`). Skip step 3 when the data has no keys to detect and write the file directly.
5. **Render:** `python3 ~/.agents/skills/report-html/build.py report.json <out>.html`. It aborts on an unknown ref, parent, badge or colour; fix the data, not the check.
6. **Verify in a browser** at 1280 px and 390 px: no horizontal scroll (`scrollWidth == 390`), no console errors, one badge toggle changes the counter (if there is a tree), one link jumps and highlights, one diagram node with ⊞ jumps to its detail diagram, and a link into a closed tab opens that tab. In one diagram: hovering a node fades everything but its edges and neighbours, a legend edge kind hides its edges, and ⤢ opens the zoom view. In a `map`: dragging a box moves its edges, a click greys it out and changes the counter, both survive a reload, "Reset layout" restores the build. With `drives`: one tree badge toggle hides (map) or fades (other diagrams) the matching nodes, and the tree's reset brings them back. Screenshot every diagram and fix bundled lines with `col`/`row`.
7. Default location: `<repo>/.scratch/reports/<topic>-<YYYY-MM-DD>.html` (dump in `<topic>-<date>.data/`, detector output in `<topic>-<date>.build/`). Open it for the user (`open <file>`) and report the answer in chat, not only the file.

## Writing

- Prose in the user's language, short STE-style sentences: one statement each, active voice, fixed terms.
- Every number comes from step 2. Label estimates as such.
- Use real identifiers (`collection`, `external_id`) in `code`, so the reader can find them.
- Say each fact once. Before adding a block, check that no diagram, card or table shows it already; link to that place with `[[id]]` instead. A tree or table that only repeats what the diagrams show goes.
- **List and diagram of the same entities** (repos in a tree and in a dependency map, screens in a tree and in a flow): one section, the tree first, the diagram right after it. Set `drives: [<diagram id>]` on the tree and `ref` on every diagram node that is one of its entities, so the tree's badges filter both: a `map` hides the filtered boxes and their edges and refits, other diagrams fade them. The tree's `hint` says that the diagram follows. Badges that matter for the diagram (owner, role, a `hide` flag such as "stale") belong in the tree's `filter`.
- Three or more blocks of one kind in a row (one detail diagram per stage, one state machine per field) go into one `tabs` block, one tab per item, with the item's own extras (its state machine, its note) in the same tab. Each tab opens with an entry summary: `entity` renders that entity's card (title, meta, badges, links) and makes the tab its link target; otherwise give a one-sentence `summary`.
- **Change document** (the user asks what changed, or for a report on a change): start from the previous `report.json`, keep its structure and set `change: new|changed|removed` on exactly the parts that differ, at the smallest level that holds the change (a node, an edge, a row, an item; a whole tab or section only when all of it is new or gone). Keep removed parts, they render struck through. Set top-level `since` to the previous version. `build.py` then adds a header bar with counts and a full-contrast toggle, opens the first changed tab and dims every unmarked sibling of a marked part, so the reader sees only the change in colour. Do not mark inside a `new` or `removed` part; the build ignores it.

## Which diagram

| Question | Block | Notation |
|---|---|---|
| How does pipeline or feature X work | `flow` L0, then one `flow` per stage with `parent` (L1, L2 if needed) | DFD levels, C4 zoom |
| What happens inside one stage | `flow` with `parent`, decisions and `error` edges | balanced DFD child, UML activity |
| What becomes what (types, entities) | `lineage` | dataset → job → dataset (OpenLineage) |
| Which states a record or run goes through | `states`, one per status field | UML state machine |
| Who does which step | `flow`, one column per actor | BPMN lanes |
| What depends on what (repos, packages, services), more than ~15 nodes or a dense web | `map` with one declared `kinds` entry per dependency type | dependency graph the reader rearranges |
| What depends on what, few nodes, one direction | `flow` with `dir: right` and `kinds` | dependency graph |
| How much of what | `bars`, `table` | (Sankey only with real flow numbers) |

Rules, schema and sources: [`DIAGRAMS.md`](DIAGRAMS.md).

## report.json

```
title, lang, meta: [line], stats: [[label, value]], numbered: true, since?
badges: { <cat>: { label, shape: square|round|pill|dashed|text, filter: any|hide,
                   values: { <val>: { label?, color, desc? } } } }
entities: [{ id, title, label?, parent?, order?, tree?: false, muted?,
             badges: { <cat>: [val] }, meta: [inline], refs: [id] }]
sections: [{ title, sub?, id?, change?, blocks: [block] }]
```

- `shape`: one per category, so a category is recognisable without colour.
- `filter`: `any` keeps a node while at least one of its values is on (audiences, origins); `hide` drops a node carrying a switched-off value (status flags).
- `color`: purple blue green gray orange pink teal yellow red navy brown ink.
- `tree: false`: entity is a link target only (a table row `anchor` or a tab `entity`), not a tree node. Each entity renders in one place: a tree row, a table row or a tab.
- Inline text: `` `code` ``, `[[id]]` or `[[id|label]]` links.
- `change`: `new|changed|removed`, allowed on a section, a block, a tab, an entity, a table row (`{cells, change}`), a list item (`{text, change}`), and on flow and map nodes, dict edges, lineage types and steps, states and transitions.

Blocks (`type`):

| type | fields |
|---|---|
| `p` | `text` |
| `bullets`, `steps` | `items: [inline]` |
| `tree` | `filter: [cat]` (first is the kind badge, or `kind`), `count: <kind val>`, `count_label`, `hint`, `reset`, `drives?: [diagram id]` (its badges filter those diagrams' nodes by `ref`) |
| `table` | `columns`, `numeric: [col index]`, `rows: [[cell]]` or `[{anchor, cells}]`; cell = inline, number, `{ref, text?}`, `{refs:[id]}`, `{badge:[cat,val]}` |
| `bars` | `items: [[label or id, value, color?]]`, `color`, `link` |
| `flow` | `nodes: [{id, label?, sub?, shape?, color?, ref?, at?, col?, row?}]`, `edges: [[from, to, label?, kind?]]` or `[{from, to, label?, kind?, at?}]`, `kinds?: {<kind>: {label?, color?, dash?: dash\|dot}}`, `parent?: "<flow>:<node>"`, `dir: right\|down`, `box: [w,h]`, `gap: [x,y]` |
| `map` | `nodes: [{id, label?, sub?, lines?: [text], shape?: process\|external, color?, ref?, href?, at?}]`, `edges` as in `flow` plus `label` as a list of lines and `warn: true` (red label), `kinds?`, `off?: [node]`, `pos?: {node: [x, y]}`, `height?` |
| `lineage` | `types: [{id, label?, sub?, shape?, ref?}]`, `steps: [{from, to, fn, at?, note?}]` (`from`/`to` id or list), `parent?`, `dir` |
| `states` | `field`, `at`, `states: [{id, label?, color?, ref?}]`, `transitions: [{from, to, trigger?, guard?, action?, at?}]` (`[*]` = start/end), `parent?` |
| `tabs` | `id`, `label`, `tabs: [{entity? \| label, summary?, blocks: [block]}]`, `kind?` (badge category shown first in the card), `numbered: true` |
| `html` | `html` (escape hatch; use the template's classes) |

`example.json` shows every block type; render it to see the result.

## Files

- `template.html`: theme tokens, layout, badge shapes, tree, Alpine `treeFilter`, tabs, link highlight, diagram interaction (hover or focus a node: its edges and neighbours stay, the rest fades; legend edge kinds toggle; ⤢ opens a `<dialog>` with wheel/pinch zoom, drag pan, `+`/`-`/`0`/arrow keys), and the `map` controller (drag boxes, click to grey out, curved edges re-routed live, labels as pills or dots, ⌘/Ctrl-wheel or pinch zoom, background pan, toolbar Fit/Reset/All active/Copy layout/Full screen, state in `localStorage` per page, figure and build). Alpine 3.14.9 and the font load from CDNs; offline the tree toggles do not work and the font falls back. Tabs and diagram interaction work without Alpine; without JS every panel shows.
- `build.py`: renderer and link checker, stdlib only. Without a tree `count`, the counter counts leaves; each row shows at most 12 links per direction plus `+N`. Diagrams are SVG with orthogonal edges (a `map` gets its start layout here and its curves from the template); it fails on unknown nodes, unbalanced child flows, parent loops, links without a target and anchors rendered twice, and warns about edges without `at`.
- `DIAGRAMS.md`: fact collection from code, levels and balancing, `flow`/`lineage`/`states`/`map` schema, layout, sources for the notation choice.
- `detect.py`: key/relation/hierarchy/enum detection, `schema.json`, `schema.ts`, draft `report.json`; stdlib only.
