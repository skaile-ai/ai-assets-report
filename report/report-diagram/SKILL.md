---
name: report-diagram
description: "Dependency `map` canvases and mermaid notations (sequence, class, ER, C4, gantt, mindmap, sankey, railroad) with the notation-choice table. Use for 'what depends on what', 'who calls whom in which order', 'draw this as a diagram'."
metadata:
  version: 0.1.0
  publisher: mortegro
---

# report-diagram <question>

Answer `<question>` about dependencies, call order or structure with one `map` or `mermaid` block. Read the relations from the code or the dump first, draw second. Never draw an edge you did not read.

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
- Put `at` (`path:line`) on every edge. The build lists them in the "Evidence" table.
- A `tree` with `drives: ["<map id>"]` above the map filters it: boxes whose `ref` the badges filter out disappear with their edges. Set `ref` on every box that is an entity. Tree first, map right after it.
- Start layout: ranks by longest path, barycentre order, long ranks wrapped. "Copy layout" puts `{"pos": …, "off": […]}` on the clipboard; paste both into the block to ship the reader's arrangement.

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
- Name nodes and participants as in the code. State the entity in `at` when the whole diagram comes from one place.
- One diagram per question. More than ~20 nodes: split it, or use a `map`.
- Hover-fade does not apply to mermaid output. ⤢ opens the zoom view.
- Do not use `mermaid@12`: its layout default differs from the tested one.

## Alone

1. Pick the block from the table. Collect the relations from the code or data, every one with `path:line`.
2. Define one entity per node the reader should reach (`badges`, `meta`), and a `tree` for them, so each `ref` and `click` target exists.
3. Write `report.json` with only the block, its entities, the tree, and one `p` that states the answer. Copy the shape from `example.json`. State each term as in the code.
4. Build: `python3 ~/.agents/skills/report-html/build.py report.json <out>.html`. Fix every `report.json:` line.
5. Verify (list below), then `open <out>.html` and state the answer in chat.

## Under report-html

1. Do steps 1 to 3 of Alone; hand the blocks and entities back to the orchestrator's section plan instead of building.
2. Order inside a section: the prose first, then the `tree` of the nodes, then the `map` it `drives`, then `mermaid` figures.
3. The orchestrator builds and runs the full checks. Run the Verify list for your blocks.

## Verify

- 1280 px and 390 px: `scrollWidth == 390`, no console errors.
- `map`: dragging a box moves its edges. A click greys the box out and changes the counter. Both survive a reload. "Reset layout" restores the start layout.
- `map` with a `tree`: a badge toggle removes boxes and their edges and changes the counter.
- `mermaid`: the figure contains an `svg.dg`; ⤢ opens the zoom dialog with it; a click on a linked node jumps to the entity and highlights it. Without network the source text shows.
- Screenshot every diagram. Overlapping labels: shorten them or split the diagram.
