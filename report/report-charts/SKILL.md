---
name: report-charts
description: "Quantities as `bars` or Vega-Lite `vega` charts with tooltips, selections and cross-filter. Use for 'how much', 'distribution', 'over time', 'compare counts'."
metadata:
  version: 0.1.0
  publisher: mortegro
---

# report-charts <question>

Answer `<question>` about quantities with `bars` (a few numbers) or `vega` (Vega-Lite: counts, distributions, time series, selections). Every number comes from the dump or the code. Write prose per `skill://report-asd-ste100`.

## Which block

| Question | Block |
|---|---|
| A few values, one per label or entity; no axis, no hover | `bars` |
| Distribution, histogram, counts per enum value, trend over time, two numeric fields, a chart that filters a table | `vega` |
| Real flow numbers between stages | `mermaid sankey-beta` (`skill://report-diagram`), not a chart block |

`bars` renders without JS and without a network. `vega` needs the jsDelivr CDN: offline, the figure shows a one-line note and the page keeps working. Use `bars` when it is enough.

## `bars`

```
{ "type": "bars", "items": [["<label or entity id>", 8, "<color?>"]], "color": "ink", "link": true }
```

A label that is an entity id renders as a link (`link: false` turns that off). The longest bar is 100 %.

## `vega`

```
{ "type": "vega", "id": "kinds", "label": "Tickets je Art",
  "spec": { "mark": {"type": "bar", "tooltip": true}, "data": {"values": [{"id": "t1", "kind": "feat"}]},
            "params": [{"name": "pick", "select": {"type": "point", "fields": ["kind"]}}],
            "encoding": {...} },
  "entity": "id", "at": "src/report.ts:12" }
```

`id` is required (it shares the diagram id space with `flow`, `map` and `mermaid`; the figure gets the anchor `#f-<id>`). `label` is the caption. `at` adds the evidence table.

Spec rules. The build fails on the first two:

- `spec.data.values` is an inline array of row objects. No `data.url`: the page stays one file. Message: `vega <id>: data must be inline values`. Put the rows from the dump into the spec; aggregate in Vega-Lite (`aggregate`, `bin`, `timeUnit`) instead of in your own code when the chart is a count.
- `entity` (optional) names the row field that holds entity ids. Every row needs it: `vega <id>: entity <f> missing in row <n>`.
- The build sets `$schema` (Vega-Lite v6), `width: "container"` and `data.name = "rows"` when missing. Give `height` (about 200-260). Do not set a fixed `width` (the chart must fit 390 px).
- Add `mark.tooltip: true` (or an `encoding.tooltip`) so a hover shows the value.
- Label axes with `title` in the language of the report. Keep the default colours; set `mark.color` to `#0969da` for a single series.
- Do not put a `vega` block inside `tabs`: a hidden panel has no width when the chart renders.
- One chart answers one question. Two series that share no scale are two charts.

## Cross-filter: chart → table

A point selection on the chart filters a `data` table (`skill://report-table`).

1. In the spec declare a point selection with the field: `"params": [{"name": "pick", "select": {"type": "point", "fields": ["kind"]}}]`. Without `fields` the selection holds row ids, and the table cannot map it. Make the selection visible: `"opacity": {"condition": {"param": "pick", "value": 1}, "value": 0.35}`.
2. In the `data` block set `"listen": {"chart": "<vega id>", "param": "pick", "field": "kind"}`. `field` is a column key. The cell text of that column must equal the chart value, so use plain string cells (a `{badge}` cell shows its label, not its value).
3. A click on a bar leaves only the rows of that value. A click on the chart background clears the selection and restores all rows. A shift-click adds a value.

The build fails when `listen.chart` is no `vega` block, when `listen.param` is no param of that spec, when `select.type` is not `point`, or when `listen.field` is no column key.

## Badge → chart

A `tree` filters the chart with `drives`. The chart then follows every badge toggle: the rows of hidden entities leave the dataset and the bars shrink; the tree's reset restores them.

```
{ "type": "tree", "filter": ["kind"], "drives": ["kinds"] }
```

Needs `entity` on the `vega` block, and the rows' `entity` values must be ids of entities in that tree: `tree: drives kinds: no row of it has an `id` that is an entity of this tree`. Use one row per entity (the count then comes from `aggregate: "count"`), so a filtered entity removes exactly one row. Say in the tree's `hint` that the chart follows. The header find box filters the tree rows, and the chart follows that too.

## Alone

1. Pin the question and find the numbers: dump the collection (`<report>.data/`) or read them from the code. Name the field for each axis.
2. Write `report.json`: one `p` that states the answer, then per question one `vega` (or `bars`) block. Add `badges`, `entities` and a `tree` only when the rows are entities and the reader should filter them; add a `data` table only when the reader needs the rows. Copy the shape from `example.json`.
3. Build: `python3 ~/.agents/skills/report-html/build.py report.json <out>.html`. Fix every `lint:` line or justify it in chat.
4. Verify (below), `open <out>.html`, state the answer in chat.
5. Location: `<repo>/.scratch/reports/<topic>-<YYYY-MM-DD>.html`.

## Under report-html

1. Return the `vega`/`bars` blocks (and the `listen` and `drives` wiring) to the orchestrator's section plan; do not build.
2. Section order: the prose that states the finding first, then the chart, then the `data` table that listens to it. A tree that drives the chart comes before the chart.
3. Wire the cross-filter only when the orchestrator checked it (`data` and `vega` both chosen). Wire badge → chart only when the rows carry entity ids.
4. The orchestrator builds. Run the Verify list below for your blocks.

## Verify

Open the built file at 1280 px and at 390 px. The charts need the network.

- `document.documentElement.scrollWidth == 390` at 390 px; the chart fits the column; no console errors.
- Each `vega` figure contains an `svg` (no "needs the vega CDN" note).
- A hover over a bar shows a tooltip with the value.
- A click on a bar leaves only the rows of that value in the listening `data` table (the info line drops); a click on the chart background restores all rows.
- A tree badge toggle removes bars (or their counts) from the chart; the tree's reset restores them.
- Offline (CDN blocked): the figure shows the note, the rest of the page works.

Sources: [vega-embed](https://vega.github.io/vega-embed/) (`vegaEmbed(el, spec, options)` returns `{view}`), [Vega View API](https://vega.github.io/vega/docs/api/view/) (`addSignalListener`, `change`, `changeset`).
