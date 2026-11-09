---
name: report-charts
description: "Quantities as `bars` or Vega-Lite `vega` charts with tooltips, selections and cross-filter. Use for 'how much', 'distribution', 'over time', 'compare counts'."
license: MIT
metadata:
  version: 0.3.0
  publisher: skaile-ai
---

# report-charts <question>

Answer `<question>` about quantities with `bars` (a few numbers) or `vega` (Vega-Lite: counts, distributions, time series, selections). Every number comes from the dump or the code. Write prose per `skill://report-prose`.

Reading contract: follow `skill://report` (citations, labels, answer-first). Chart rules:

- The caption (`label` on `vega`, the `p` above a `bars` block) states the interpretation: what the chart shows and what the reader should see in it, for example "Most tickets are features". A bare measure ("Tickets per kind") is not enough.
- The title states only what the plotted data shows: a title naming the top five plots five bars, or the plot marks them. An "other" group sits last and takes `gray`.
- Provenance goes in `at` (evidence table) or in a `[@path:line]` token in the caption or the prose. Never put a file path, line number or source name in an axis `title`, a `bars` label or a field name.
- One chart answers one question. The answer to that question is in the prose before the chart; the chart supports it.

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
- Label axes with `title` in the language of the report. Leave colours and legend placement to the page: it applies the brand palette and puts legends below the plot.
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

## Standalone

Standalone: run `skill://report` with this feature preselected.

## Under report

The shared contract is in `skill://report`, "Under orchestration". This skill's delta:

1. Return the chosen `vega`/`bars` blocks. Add `listen` wiring only when `crossfilter` was chosen and `drives` wiring only when `badge-chart` was chosen; wire badge → chart only when the rows carry entity ids.
2. Section order: the prose that states the finding first, then the chart, then the `data` table that listens to it. A tree that drives the chart comes before the chart.
3. Under `technical` the caption's `[@…]` token names the dump file and the field of every series.
4. Run the Verify list below for your blocks.

## Verify

The base checks (1280/390 px, `scrollWidth`, console) are in `skill://report`. Chart checks; the charts need the network:

- Each `vega` figure contains an `svg` (no "needs the vega CDN" note) and fits its column at 390 px.
- A hover over a bar shows a tooltip with the value.
- A click on a bar leaves only the rows of that value in the listening `data` table (the info line drops); a click on the chart background restores all rows.
- A tree badge toggle removes bars (or their counts) from the chart; the tree's reset restores them.
- Offline (CDN blocked): the figure shows the note, the rest of the page works.

Sources: [vega-embed](https://vega.github.io/vega-embed/) (`vegaEmbed(el, spec, options)` returns `{view}`), [Vega View API](https://vega.github.io/vega/docs/api/view/) (`addSignalListener`, `change`, `changeset`).
