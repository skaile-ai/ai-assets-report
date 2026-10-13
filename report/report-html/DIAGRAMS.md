# Diagrams: how code and pipelines work

Read this before you write a `flow`, `lineage` or `states` block.

## Capture the flow

Collect facts from the code first; draw second. For more than two stages, give each stage to one `scout` subagent and ask for this list, every fact as `path:line`:

1. **Trigger**: npm script (`package.json`), HTTP route (`server/api/**`), UI call, hook, cron. One trigger is one entry node.
2. **Steps**: the functions in call order, with their real names.
3. **Input and output**: the type or collection that goes in and comes out of each step.
4. **Stores**: every collection, table or directory that a step reads or writes.
5. **Error paths**: condition → effect (`throw`, exit code, HTTP state, rollback, status set).
6. **Hand-off**: which later stage reads the output.

Rules for the diagram:

- Draw an edge only if you read it in the code: a call, or a write that a later read consumes. Put the line in `at`. If one edge has `at`, `build.py` warns about every edge without it.
- Name a process with a verb and an object, or with the real function name. Name a store with its collection or path. Name an edge with the data it carries (`source_chapter`, `ImportDoc`), never "uses" or "calls".
- An error path is `kind: "error"` to a node with `color: "red"` whose `sub` states the effect (`exit 1`, `409 conflict`).
- A conditional or optional path is `kind: "opt"`.
- A decision is `shape: "decision"` with a question as label and the answers as edge labels.
- Do not guess a step to close a gap. Leave the gap and say so in a `p` block.

## Levels

| Level | Block | Contains |
|---|---|---|
| L0 | `flow` without `parent` | the stages (processes with `ref` to their entity), stores shared by two or more stages, external parties. About 6-12 nodes. |
| L1 | `flow` with `parent: "<L0 id>:<node id>"` | the steps of one stage: functions, decisions, error ends, the stores only this stage uses. |
| L2 | `flow` with `parent: "<L1 id>:<node id>"` | only for a step whose branching is worth its own diagram. Not every stage needs L2. |

- `build.py` gives the parent node a drill marker (⊞) and a link to the child; the child caption links back ("↑ Part of").
- **Balancing (DFD)**: every parent neighbour of the node is a node in the child with the same `id`, and keeps its edge direction. The build fails otherwise. These boundary nodes are dashed and link to that neighbour's own detail diagram.
- An external party that appears first in a child must also go into the parent (warning).
- A `lineage` or `states` block can also have a `parent`; then it is the detail of that node (no balancing).
- Put the L1 diagrams of one L0 into `tabs`, one tab per stage with `entity` set to the stage the L0 node `ref`s. The card carries trigger, code and guard (the stage's `meta`), so the diagram caption and section text do not repeat them. The stage's L2 diagrams (`states` of its store) go into the same tab.

## Types: `lineage`

What becomes what, as dataset → job → dataset (OpenLineage, dbt DAG). Types are nodes; the function of a step labels the edge. A step with several inputs or outputs becomes a job node. The table under the diagram lists from, function, to, evidence, change.

## Status: `states`

One block per status field (`import_item.status`). Read the enum (`z.enum([...])`) and every write of that field. `[*]` as source is the initial, as target the final state. A transition is `trigger [guard] / action` (UML). A self-transition shows a write that keeps the state. `build.py` warns about a state no path reaches from `[*]`.

## Working canvas: `map`

A `map` is a dependency web the reader rearranges, as on a whiteboard. Use it instead of a `flow` when the graph has more than about 15 nodes, many cross edges or no main direction, and the reader wants to sort it out: drag boxes apart, grey out what does not matter now, read one box's edges on hover. It has no drill-down, no shapes beyond `process`/`external` and no orthogonal routing; it is not a DFD.

- A box shows `label`, `sub` and up to a few `lines` (exports, versions). `ref` (entity or detail diagram) or else `href` (URL) adds ↗; ⌘/Ctrl-click on the box follows it too.
- An edge `label` may be a list: one line each. `warn: true` paints the label red (spec mismatch, stale version).
- `off` greys out boxes from the start; their edges grey with them. The reader's clicks, drags and zoom stay in `localStorage` for this page, figure and build; a rebuild with a different layout or `off` starts fresh.
- A tree with `drives: ["<map id>"]` above the map filters it: boxes whose `ref` the tree filters out disappear with their edges, the map refits, and the counter says how many are filtered out. Greyed-out (a reader's choice) and filtered out (the badges) stay separate.
- Start layout: ranks top-down by longest path, barycentre order, long ranks wrapped into sub-rows so the whole map fits the page. "Copy layout" puts `{"pos": …, "off": […]}` on the clipboard; paste both into the block to ship the reader's arrangement.

## Schema

```
flow:     id, label, parent?, dir: right|down (right), box?: [w,h], gap?: [x,y],
          nodes: [{id, label?, sub?, shape?: process|store|external|decision|data|state,
                   color?, ref?, at?, col?, row?}],
          edges: [[from, to, label?, kind?]] or [{from, to, label?, kind?: flow|error|opt|<declared>, at?}],
          kinds?: {<kind>: {label?, color?, dash?: dash|dot}}
lineage:  id, label, parent?, dir (down), types: [{id, label?, sub?, shape? (data), ref?, col?, row?}],
          steps: [{from: id|[id], to: id|[id], fn, at?, note?, kind?}]
states:   id, label, parent?, field?, at?, dir (down), states: [{id, label?, color?, ref?}],
          transitions: [{from, to, trigger?, guard?, action?, label?, kind?, at?}]
map:      id, label, height?, nodes: [{id, label?, sub?, lines?: [text], shape?: process|external,
                                     color?, ref?, href?, at?}],
          edges: [{from, to, label?: text|[text], kind?, warn?, at?}], kinds?, off?: [node], pos?: {node: [x, y]}
(all four take `kinds`)
```

- Anchors: `#f-<id>` per diagram, `#f-<id>-<node>` per node. `ref`, `parent` and boundary nodes link to them; elsewhere use `<a href="#f-…">` in an `html` block.
- Node `label` defaults to the `id`; in a child, a boundary node takes the parent node's label.
- `at` on nodes and edges goes into the collapsible "Evidence" table below the diagram.
- `kinds` declares edge types beyond `flow`, `error` and `opt` (`npm`, `submodule`, `reads`): each gets its colour token and line style on the line, the arrow and the legend. With two or more edge kinds in use, every legend entry is a button that hides or shows those edges.
- Every diagram is interactive: hovering or focusing a node keeps its edges and neighbours and fades the rest; ⤢ in the caption opens a full-screen zoom/pan view (a `map` has its own toolbar instead).

## Layout

- Without `col`/`row`, ranks follow the longest path; back edges do not count. A source (no incoming edge) moves forward to one rank before its nearest successor. Barycentre sweeps order each rank; the build keeps the order with the fewest crossings, so a hand-written node order wins ties. Give `col` and `row` to every node or to none.
- Three or more edges on one side of a box spread into separate ports, each as near its far end as the side allows; each bends on its own track. Too many for 6 px spacing share one trunk.
- Use `dir: "down"` for more than five ranks, so the diagram stays narrow on a phone.
- Put the main path in column 0, error ends beside the step that fails, stores in the column right of their writer.
- Screenshot every diagram. If lines bundle or cross boxes, set `col`/`row`. A diagram wider than the page scrolls inside its own container; the page itself must not scroll sideways.

## Why these notations

| Question | Notation | Source |
|---|---|---|
| How does X work (overview) | DFD level 1 / C4 container: processes, stores, externals, named data on edges | [Yourdon, DFD ch. 9](https://static1.squarespace.com/static/50c9c50fe4b0a97682fac903/t/512878e6e4b02e5615b4c5ed/1361606886338/Yourdon+DFD.pdf); [C4 diagrams](https://c4model.com/diagrams) |
| Inside one stage | balanced child DFD; branches and failures as UML activity (decision, exception path) | [UCT DFD levelling](https://www.cs.uct.ac.za/mit_notes/software/pdfs/Chp06.pdf); [UML 2.5.1](https://www.omg.org/spec/UML/2.5.1/PDF) cl. 15 |
| Drill-down | C4 zoom: each level one abstraction, neighbours shown as supporting elements | [C4 abstractions](https://c4model.com/abstractions); [C4 notation](https://c4model.com/diagrams/notation) |
| What becomes what | dataset → job → dataset | [OpenLineage object model](https://openlineage.io/docs/spec/object-model); [dbt `ref`](https://docs.getdbt.com/reference/dbt-jinja-functions/ref) |
| Status of a record or run | UML state machine, `trigger [guard] / action` | [UML 2.5.1](https://www.omg.org/spec/UML/2.5.1/PDF) §14.2; [Mermaid state](https://mermaid.js.org/syntax/stateDiagram.html) |
| Who does which step | BPMN lanes; here: one column per actor in a `flow` (no lane block) | [BPMN 2.0.2](https://www.omg.org/spec/BPMN/2.0.2/PDF) §10.8 |
| How much flows where | Sankey only with real numbers; here: `bars` | [d3-sankey](https://github.com/d3/d3-sankey) |
| Runtime order of calls | C4 dynamic: numbered edge labels (`1 · POST`), not DFD numbers | [C4 dynamic](https://c4model.com/diagrams/dynamic) |
