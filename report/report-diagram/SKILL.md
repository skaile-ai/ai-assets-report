---
name: report-diagram
description: "Dependency `map` canvases, `board` moodboards (screens today vs. proposed, changes marked) `concepts` figures (UI variants per state with their linked terms), `mock` dialogs and mermaid notations (sequence, class, ER, C4, gantt, mindmap, sankey, railroad) with the notation-choice table. Use for 'what depends on what', 'who calls whom in which order', 'moodboard', 'before/after of screens', 'which UI variant', 'how do these terms relate', 'draw this as a diagram'."
license: MIT
metadata:
  version: 0.3.1
  publisher: skaile-ai
---

# report-diagram <question>

Answer `<question>` about dependencies, call order, structure or a planned change of screens with one `map`, `board` or `mermaid` block. Read the relations from the code or the dump first, draw second. Never draw an edge you did not read.

Reading contract: follow `skill://report` (citations, labels, answer-first).

## Which block

| Question | Block |
|---|---|
| What depends on what, more than ~15 nodes, dense web, no main direction | `map` |
| Few nodes, one direction, steps of a process | `flow` with `kinds`: `skill://report-flow` |
| Which call comes after which between actors | `mermaid` `sequenceDiagram` |
| Class or type structure | `mermaid` `classDiagram` |
| Tables and their keys | `mermaid` `erDiagram` |
| Schedule, phases | `mermaid` `gantt` |
| Concept tree | `mermaid` `mindmap` |
| How much flows where, real numbers only | `mermaid` `sankey-beta` (3 columns: source,target,value) |
| Which input is valid (grammar) | `mermaid` `railroad-beta` |
| C4 context or container | `mermaid` `C4Context`, only when the user asks (experimental syntax) |
| Screens or parts today vs. proposed, side by side, the changes marked (moodboard, before/after) | `board` |
| UI variants of one question (where a thing lives, how it is named), the terms and how they relate | `concepts` |
| A dialog today vs. proposed, fields and buttons, numbered remarks | `mock` |

A levelled DFD stays native (`flow` in `report-flow`): mermaid has no balancing, no `drives` and no evidence table per edge.

## `map`: working canvas

A `map` is a dependency web the reader rearranges as on a whiteboard: drag boxes apart, grey out what does not matter, read one box's edges on hover. It has no drill-down, only the shapes `process` and `external`, and curved edges; it is not a DFD.

```
map: id, label, height?, nodes: [{id, label?, sub?, lines?: [text], shape?: process|external,
                                  color?, ref?, href?, at?}],
     edges: [{from, to, label?: text|[text], kind?, warn?, at?}], kinds?, off?: [node], pos?: {node: [x, y]}
```

- A box shows `label`, `sub` and a few `lines` (exports, versions). `ref` (entity id or detail diagram id) or else `href` (URL) adds ↗; ⌘/Ctrl-click on the box follows it.
- `kinds: {<kind>: {label?, color?, dash?: dash|dot}}` declares one edge type per dependency type (`npm`, `submodule`). With two or more kinds in use, each legend entry hides or shows its edges.
- An edge `label` may be a list, one line each. `warn: true` paints the label red (spec mismatch, stale version).
- `off` greys boxes out from the start. The reader's clicks, drags and zoom stay in `localStorage` for this page and build.
- Under size `technical` put `at` (`path:line`) on every edge; the build fails without it and lists them in the Evidence table. In other sizes `at` is optional.
- Keep node labels readable: the name as in the code or a short human term, no `path:line`. Put the source in `at`. A path is a label only when it is the object being drawn (a file dependency web).
- A `tree` with `drives: ["<map id>"]` above the map filters it: boxes whose `ref` the badges filter out disappear with their edges. Set `ref` on every box that is an entity. Tree first, map right after it.
- Start layout: ranks by longest path, barycentre order, long ranks wrapped. "Copy layout" puts `{"pos": …, "off": […]}` on the clipboard; paste both into the block to ship the reader's arrangement.

## `board`: moodboard canvas

A `board` lays screens out as on a moodboard: one canvas per area, lanes of cards side by side (today, proposed), and between two lanes a gutter that lists what changes, with arrows. The reader pans, zooms and steps through the canvases; read mode stacks everything in page flow. Cards have no x/y and no drawn connectors.

```
board: id, label, height?: px (240-2400, default 640), legend?: bool (default true),
  canvases: [{ id, label, title?, lead?: inline, change?,
     lanes: [{ label?, tone?: today|proposed|plain, cols?: 1-4, change?, cards: [card],
               changes?: [{ mark, text: inline, from?: card id, to?: card id, change? }] }] }]
card: { id?, title, kicker?, ref?: entity id, marks?: ["<kind>[ qualifier]"], image?: {src, alt, caption?},
        text?: inline, items?: [inline], blocks?: [block], at?, change? }
```

- Mark kinds: `move`, `merge`, `new`, `reuse`, `keep`, `later`, `remove`, `optional`; any other kind fails. A qualifier after the kind names the detail (`reuse picker`). The kind is printed, colour only backs it up; the legend lists the kinds in use.
- A lane's `changes` render as a gutter after that lane: mark, text, then `from` → `to` as links. `from`/`to` name a card `id` on any canvas of the same board, else the build fails. A link opens the card's canvas and focuses the card.
- Anchors: canvases and cards share `#f-<board>-<id>`; ids are unique per board. A page hash to a card opens its canvas.
- `ref` links the card to its entity (↗). `image.src` is a local file next to the output HTML or `report.json`, rewritten relative to the output; a missing file or a URL fails. A click on the image opens it large, Esc closes.
- `blocks` take any report block except `board` (a wireframe as `table`/`bullets`/`html`). `at` renders the source next to the card.
- `tone` labels the lane (`today`, `proposed`) when it has no `label`. `cols` sets the card columns of a lane in canvas mode.
- Keep one canvas per area or screen group, at most ~4 lanes per canvas. Screenshots go in `<stem>.media/`; never inline them.

## `mermaid`

```
mermaid: id, label?, code: "<mermaid source>", at?
```

The browser renders `code` from the pinned CDN module `mermaid@11`. The build checks only the links, not the syntax. Offline or on a syntax error the source stays visible in the figure.

- Use `securityLevel: "strict"` (the build sets it). In-page anchors work in strict mode, callbacks do not.
- Link a node to an entity: `click <node> href "#e-<entity id>"`. Link a node to a diagram: `click <node> href "#f-<diagram id>"`. The build fails with `links without a target: <id>` for a `click` target that does not exist.
- `click` works in `flowchart` and `stateDiagram-v2` (tested on 11.17). The mermaid docs list it for `classDiagram` too (untested here). `sequenceDiagram`, `erDiagram`, `gantt` and the others take no in-page links: put `[[id]]` links in the prose beside the figure.
- Do not write lowercase `end` in a label: it ends a subgraph. Write `End`.
- `direction` inside a `subgraph` is ignored when an edge crosses the subgraph boundary.
- Label every edge with the data or message it carries (`rows (JSON)`, `GET /items`), never "uses".
- Name nodes and participants as in the code, without paths. State the entity in `at` when the whole diagram comes from one place. Keep `[[id]]` links in the prose beside the figure for diagram types without `click`.
- One diagram per question. More than ~20 nodes: split it, or use a `map`.
- Hover-fade does not apply to mermaid output. ⤢ opens the zoom view.
- Do not use `mermaid@12`: its layout default differs from the tested one.

## `concepts`: UI variants and their terms

A `concepts` figure shows one UI question in states: the sidebar tree and the chat window as they look in each variant, what a user thinks there, and the terms the variants use. The reader picks a preset, flips switches, and sees every row marked against the baseline (new, moved, renamed, changed, gone). Hovering or tapping a term lights up every place it appears, across views, graph and glossary.

```
concepts: id, label, hint?, parts?: [views|graph|gloss] (default all three), at?,
  presets: [{id, label, set: {<key>: bool}, desc?, vs?: preset id|null}], switches?: [{id, label, requires?: <key>}],
  baseline?: preset id, start?: preset id, initial?: {<key>: bool}, switchesLabel?,
  kinds?: {<kind>: {label, color}}, terms?: [{id, label, kind, def, aka?: [text], code?, where?: [{when?, text}]}],
  views?: [{label, layout: tree|tabs, items: [item]}], thoughts?: [{text, tone?: good|mixed|bad, when?, term?}],
  relations?: [{from, to, rel: has|is|uses|shows|controls, label?, when?}], graph?: {width, height, pos: {<term>: [x, y]}}
item: {id, label, key?, when?, term?, icon?: lucide name, color?, avatar?, sq?, chip?, depth? (tree),
       kind?: section|sel|heading (tree) | title|add|note|card (tabs), slot?: tab|head|more|body|composer|side (tabs), active?}
when: {<key>: bool, ...} | {any: [{<key>: bool}, ...]}
```

- State keys are the keys the presets `set` plus the switch ids. A `when` holds when every key matches; `any` holds when one alternative does. An item without `when` is always there. The build fails on an unknown key, a non-boolean value, an unknown term, icon, colour or slot.
- Item ids are unique per view (the build fails otherwise). Rows that are the same thing in two states (one under `when` A, the other under `when` B) share a `key`: at another depth the row is marked moved, with another label renamed, else changed. Without a shared `key` the pair reads as one new and one removed row.
- `baseline` is today; `start` is the preset the page opens on (the recommendation). `requires` hides a switch until its key is on. A preset's `vs` overrides the baseline for that preset, so a sequence of stands reads step by step (`main` → `next` with `vs: "main"` → two proposals with `vs: "next"`); `vs: null` shows that preset without marks.
- Icons are lucide names from `../report/lucide.json` (the platform set). Round avatar = belongs to a person, `sq` = belongs to a space or org: keep that rule when you draw agents.
- `thoughts` are what a user would think in that state, short and in their voice; `tone` colours them. Write at most one or two per state.
- `graph` needs a position for every term (about 960×500); place the terms so no edge crosses a box, and screenshot it. `gloss` cards list `aka` (old or rejected names), `code` (the name in code) and `where` (where the term shows, per state).

## `mock`: dialogs side by side

```
mock: id, label?, notes?: [inline], panes: [{label, title, sub?, n?, body: [row], buttons?: [{label, primary?}]}]
row: field {label, value?, off?, area?, ok?, n?} | {avatar: {text, color?, sq?}, fields: [field]}
   | {tabs: [label], active?} | {chips: [label]} | {more: label, text?, fields?: [field], n?}
```

- A static HTML dialog in the page tokens, no screenshot: for proposals that do not exist yet. Panes sit side by side (today, proposal) and stack under 640 px.
- `n` puts a numbered pin on a field, a disclosure or the title; `notes[n-1]` explains it below the figure. A pin without its note fails the build.
- `off` greys a field (empty or default), `area` makes it a text area, `ok` shows a green check text beside it (`@iris available`), `more` is an open disclosure (advanced options, helper hint).

## Alone

1. Pick the block from the table. Collect the relations from the code or data, every one with `path:line`.
2. Define one entity per node the reader should reach (`badges`, `meta`), and a `tree` for them, so each `ref` and `click` target exists.
3. Write `report.json` with only the block, its entities, the tree, and one `p` that states the answer. Copy the shape from `example.json`. State each term as in the code.
4. Build: `python3 <skill-dir>/../report/build.py report.json <out>.html`. Fix every `report.json:` line.
5. Verify (list below), then `open <out>.html` and state the answer in chat.

## Under report

1. Do steps 1 to 3 of Alone for the selected blocks only; the `tree` in step 2 and the "only the block, its entities, the tree" list in step 3 apply only when the plan selected a tree. Hand the blocks and entities back to the orchestrator's section plan instead of building.
2. Return only the `map`, `board`, `concepts`, `mock` or `mermaid` blocks the section plan selected, plus the entities that their `ref` and `click` targets need. Add the `tree` of the nodes only when the plan selected it; a `ref`/`click` target can also be an entity that another selected block (table row `anchor`, tab `entity`) already owns. The standalone recipe uses a tree; the orchestration does not force one.
3. Size: under `technical` every `map` edge carries `path:line` in `at` (the build fails without it). `small` never reaches this skill.
4. Order inside a section: the prose first, then the selected `tree` (if any), then the `map` it `drives`, then `mermaid` figures, then a `board`, `concepts` or `mock`.
5. The orchestrator builds and runs the full checks. Run the Verify list for your blocks.

## Verify

- 1280 px and 390 px: `scrollWidth == 390`, no console errors.
- `map`: dragging a box moves its edges. A click greys the box out and changes the counter. Both survive a reload. "Reset layout" restores the start layout.
- `map` with a `tree`: a badge toggle removes boxes and their edges and changes the counter.
- `mermaid`: the figure contains an `svg.dg`; ⤢ opens the zoom dialog with it; a click on a linked node jumps to the entity and highlights it. Without network the source text shows.
- `board`: the select and ‹ › change the visible canvas; ⌘/Ctrl + wheel changes the zoom %; a plain wheel scrolls the page; a change arrow's link opens the other canvas and focuses its card; a hash to a card on canvas 2 opens canvas 2; "Read mode" stacks the canvases; at 390 px it starts in read mode; an image click opens the large view, Esc closes it.
- `concepts`: each preset button changes the views and the change summary; a switch with `requires` appears only when its key is on; hovering a term highlights it in views, graph and glossary, a click pins it; at 390 px the views stack and the page does not scroll sideways.
- `mock`: every pin has its note; at 390 px the panes stack.
- Screenshot every diagram. Overlapping labels: shorten them or split the diagram.
