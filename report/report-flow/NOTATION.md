# Notation: `flow`, `lineage`, `states`

Read this before you write a `flow`, `lineage` or `states` block. `build.py` is the schema authority: it fails on unknown nodes, kinds, shapes and colours.

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
(all three take `kinds`)
```

- Use the dict form of an edge when you set `at`. The list form `[from, to, label?, kind?]` has no `at`.
- Anchors: `#f-<id>` per diagram, `#f-<id>-<node>` per node. `ref`, `parent` and boundary nodes link to them. Elsewhere use `<a href="#f-…">` in an `html` block.
- Node `label` defaults to the `id`. In a child, a boundary node takes the parent node's label.
- `ref` links the node to an entity. A tree with `drives` filters the diagram by these refs.
- `at` goes into the collapsible "Evidence" table below the diagram. `lineage` and `states` show `at` in their own table.
- `kinds` declares edge types beyond `flow`, `error` and `opt` (`reads`, `npm`, `submodule`). Each kind gets its colour token and line style on the line, the arrow and the legend. With two or more edge kinds in use, every legend entry is a button that hides or shows those edges.
- Every diagram is interactive: hovering or focusing a node keeps its edges and neighbours and fades the rest. ⤢ in the caption opens a full-screen zoom/pan view.
- `states`: `[*]` as `from` is the initial state, as `to` the final state. A `trigger [guard] / action` transition follows UML.
- `lineage`: a step with one `from` and one `to` draws an edge labelled with `fn`. A step with several inputs or outputs draws a job node named `fn`.

## Layout

- Without `col`/`row`, ranks follow the longest path. Back edges do not count. A source (no incoming edge) moves forward to one rank before its nearest successor. Barycentre sweeps order each rank. The build keeps the order with the fewest crossings, so a hand-written node order wins ties. Give `col` and `row` to every node or to none.
- Three or more edges on one side of a box spread into separate ports, each as near its far end as the side allows. Each bends on its own track. Too many for 6 px spacing share one trunk.
- Use `dir: "down"` for more than five ranks, so the diagram stays narrow on a phone.
- Put the main path in column 0, error ends beside the step that fails, stores in the column right of their writer.
- Screenshot every diagram. If lines bundle or cross boxes, set `col`/`row`. A diagram wider than the page scrolls inside its own container. The page itself must not scroll sideways.

## Why these notations

|Question|Notation|Source|
|---|---|---|
|How does X work (overview)|DFD level 1 / C4 container: processes, stores, externals, named data on edges|[Yourdon, DFD ch. 9](https://static1.squarespace.com/static/50c9c50fe4b0a97682fac903/t/512878e6e4b02e5615b4c5ed/1361606886338/Yourdon+DFD.pdf); [C4 diagrams](https://c4model.com/diagrams)|
|Inside one stage|balanced child DFD; branches and failures as UML activity (decision, exception path)|[UCT DFD levelling](https://www.cs.uct.ac.za/mit_notes/software/pdfs/Chp06.pdf); [UML 2.5.1](https://www.omg.org/spec/UML/2.5.1/PDF) cl. 15|
|Drill-down|C4 zoom: each level one abstraction, neighbours shown as supporting elements|[C4 abstractions](https://c4model.com/abstractions); [C4 notation](https://c4model.com/diagrams/notation)|
|What becomes what|dataset → job → dataset|[OpenLineage object model](https://openlineage.io/docs/spec/object-model); [dbt `ref`](https://docs.getdbt.com/reference/dbt-jinja-functions/ref)|
|Status of a record or run|UML state machine, `trigger [guard] / action`|[UML 2.5.1](https://www.omg.org/spec/UML/2.5.1/PDF) §14.2; [Mermaid state](https://mermaid.js.org/syntax/stateDiagram.html)|
|Who does which step|BPMN lanes; here: one column per actor in a `flow` (no lane block)|[BPMN 2.0.2](https://www.omg.org/spec/BPMN/2.0.2/PDF) §10.8|
|Runtime order of calls|C4 dynamic: numbered edge labels (`1 · POST`), not DFD numbers|[C4 dynamic](https://c4model.com/diagrams/dynamic)|
