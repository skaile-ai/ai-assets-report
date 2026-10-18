# Visual techniques for explainer scripts and scenes

Read this before writing `<id>.script.md` and again before writing `<id>.py`. Helper names (`self.box`, `self.pipeline`, `COLORS`, `FRAME_W`, …) are the ones in `brand.py`; `from brand import *` also gives the whole manim namespace. Formulas: `Typst("x^2")` / `MathTypst("x^2")` (no LaTeX, never `Tex` or `MathTex`).

## 1. Grammar

1. **One idea per beat.** A beat is one visual change plus one sentence.
2. **Colour is meaning.** An entity keeps its badge colour (`COLORS["teal"]`, or the name `"teal"` in any helper) in every chapter. `accent` marks emphasis only; `muted` marks support; `red` marks errors and removals; `green` marks new or good.
3. **Opacity has three layers**: 1.0 (the subject), 0.4 (`self.dim(...)`), 0.15 (`self.structural(...)`). Step older content back instead of deleting it.
4. **At most 6 live elements.** Dim or clear the rest (`self.clear_stage()`).
5. **Transform the same object.** Use `ReplacementTransform(a, b)` or `TransformMatchingShapes(a, b)` instead of fading `a` out and `b` in.
6. **The visual leads the sentence.** The object appears in the beat before (or together with) the sentence that names it.
7. **Labels are the report's identifiers verbatim**: `source_chapter`, `npm run import`, the entity id as written in `report.json`.
8. **Every reveal gets its hold.** `beat(..., wait=…)` gives the eye time; the narration budget extends it (section 5).
9. **Tempo curve across chapters**: slow (chapter 1) → medium → fast (middle chapters) → slow (closing chapter).
10. **The video reads with the sound off.** The caption lane carries each sentence; the picture carries the structure.

```python
# one beat = one change + one sentence; hold = max(wait, narration - run_time)
self.beat(1, FadeIn(boxes), say="The import has five steps.")
self.beat(2, self.pulse(arrows[0]), say="Each chapter becomes one row.", run_time=1.0)
self.beat(3, self.dim(*boxes[:3]), self.hi(boxes[4]), say="Only the last step writes files.")
```

## 2. Arc per profile

| Report profile | Arc (`arc:` in the script) | Chapter roles |
|---|---|---|
| explanation / structure | `build-up` | component → connection → scale → full picture → replay with pulses |
| critique | `problem-solution` | what breaks → evidence → the one insight → fix first → scorecard |
| comparison | `comparison` | setup → A → B → contrast → verdict |
| inventory / exploration | `data-story` | the number → the distribution → the outlier → the gap |
| change | `before-after` | what was → what is new (green) → what is gone (struck through, red) → net |

## 3. Block → shot

Starting points; go beyond them where the report's structure suggests a better picture (a hook, an "aha" beat, a payoff).

| Report block | Shot |
|---|---|
| first section `p` + `stats` | The key sentence as `self.text(s, H1)` with `self.ring(subject)` on the subject word group. One `self.counter(max_value, label)` per stat; `beat(n, FadeIn(c), self.count_to(c, value), run_time=1.5)`. Two stats `LEFT_RIGHT`, four in a `GRID` (`VGroup(...).arrange_in_grid(rows=2)`). `counter`'s first argument is the largest value it will show. |
| `flow` | `boxes, arrows = self.pipeline(labels, colors)` (≤ 5 one row; 6–8 a two-row snake that runs right to left in row two). Reveal boxes with `FadeIn(box)`, edges with `GrowArrow(arrow)` plus `self.edge_label(arrow, "label")` in edge order. `self.pulse(arrow)` when the narration says what travels. `kind: error` edge: `DashedLine(a.get_edge_center(RIGHT), b.get_edge_center(LEFT), buff=0.1, color=color_of("red")).add_tip()`. `shape: decision`: `Square(side_length=1.6).rotate(PI/4)` with the label. L1 flow: `self.dim(parent_box)` then a second `self.pipeline` below it (zoom without a camera move), `clear_stage()` to return. |
| `states` | States as `self.box` on a circle (`box.move_to(2.2 * np.array([np.cos(a), np.sin(a), 0]))`, a = k·2π/n); the current state gets `self.hi(box)`; transitions as `CurvedArrow(start, end)` + `self.pulse(arrow)`. |
| `lineage` | Types as `self.pipeline` boxes left to right. Move forward with `ReplacementTransform(prev.copy(), next_box)`; the step function is `self.edge_label(arrow, "fn_name")`. |
| `tree` + badges | `self.stack(rows)` with indent per level (leading spaces in the string, or `.shift(RIGHT*0.4*level)`), `self.chip(s, color)` beside each row. Filter beat: `self.dim(*failing_rows)` + `self.count_to(counter, n)`. |
| `bars` / `vega` | `chart = self.bars([(name, value, color), …])`; `beat(n, Create(chart))`; `self.hi(chart.bars[i])` on the largest bar. Time series: `Axes(...).plot(fn)` with `Create`. |
| `table` (criteria × candidates) | Rows as `self.stack`; `LaggedStart` by row (`beat(n, *[FadeIn(r, shift=RIGHT*0.2) for r in rows], lag=0.3)`); `self.ring(cell)` on the winning cell. |
| `data` (findings) | The top five rows as `self.box(label, color=…, sub=detail)` cards stacked with `lag=0.3`, colour by the `sev` column (`red` for the worst, then `orange`, `yellow`, `gray`); one `self.counter` for the rest. |
| `map` | Nodes as `self.box` or `Circle` on a ring, edges `Line(..., stroke_color=BRAND["muted"])`, the chain the prose names gets `self.hi(node)` in order. |
| `mermaid` sequence | Lifelines as vertical `DashedLine`, messages as `Arrow` in order (`GrowArrow` per message). Other mermaid kinds: draw as `flow` or `map`. |
| `bullets` / `steps` | `rows = self.stack(items)`; `FadeIn(rows[i], shift=RIGHT*0.2)` per item; earlier rows `self.dim(*rows[:i])`. |
| `since` / `change` | `LEFT_RIGHT` before / after. Removed items: a `Line` through the text in `color_of("red")`, text via `self.dim`. New items: `self.chip(s, "green")` or green text. |

```python
# chapter 1: hook + counters
def construct(self):
    self.title_card("Vom Buch zum Screen", sub="Ein Import in fünf Schritten", meta="Bericht vom 2026-10-18")
    key = self.text("Das Buch wird Zeile für Zeile zu Screens.", H1).move_to(UP * 1.5)
    n = self.counter(120, "Screens").move_to(DOWN * 0.5)
    self.beat(1, FadeIn(key), say="Ein Buch wird zu Screens.")
    self.beat(2, self.ring(key), FadeIn(n), self.count_to(n, 120), say="Der Import erzeugt 120 Screens.", run_time=1.5)
    self.clear_stage()
```

## 4. Layouts

Usable area under the chrome (coordinates from `brand.py`): the header hairline sits at y = 3.1 (header text at y = 3.55); the caption lane is anchored at y = -3.5 and grows upward, two lines (any narration ≤ 20 words) reach y = -3.0, three lines y = -2.7. Place content in **y ∈ [-2.6, 2.8]** and **x ∈ [-6.6, 6.6]** (`FRAME_W` = 13.22 wide, 8 high frame).

| Name | Placement |
|---|---|
| `FULL_CENTER` | one object or group at `ORIGIN`; use for the hook, a `pipeline`, a `bars` chart |
| `LEFT_RIGHT` | two groups at x = ±3.5 (each ≤ 6 wide); before/after, A vs B, two counters |
| `TOP_BOTTOM` | two groups at y = ±1.5 (each ≤ 2.4 high); a parent box above its child flow |
| `GRID` | `VGroup(...).arrange_in_grid(rows=2, buff=0.6)` centred; four counters, four cards |
| `PROGRESSIVE` | `self.stack(items)` anchored left (`.to_edge(LEFT, buff=0.7)`), one row per beat, earlier rows dimmed; `stack` caps its height at 5.0 |
| `ANNOTATED` | one centre object (≤ 6 wide) with `self.text(..., SMALL)` labels placed by `next_to` and joined by `Arrow` |

A two-row `pipeline` spans y ∈ [-1.8, 1.8]; a one-row `pipeline` y ∈ [-0.65, 0.65]. Leave `edge_label` space (0.6) above arrows.

## 5. Pacing

Beat durations are `run_time` + hold. The measured narration length from `timestamps.json` (+0.15 s) **overrides every number below upward, never downward**: `hold = max(wait, narration − run_time)`. A long sentence stretches its beat; a short one never shortens the table value.

| Moment | `run_time` | `wait` |
|---|---|---|
| title card (`title_card`) | built in: fade 1 s, hold 2 s, fade 1 s | – |
| chapter card (`chapter_card`) | built in: fade 1 s, hold 1.5 s, fade 1 s | – |
| new object appears | 1.2 | 0.8 |
| key reveal (answer, verdict, headline number) | 2.0 | 2.0 |
| transform | 1.5 | 1.0 |
| supporting label / edge label | 0.8 | 0.5 |
| clear (`clear_stage`) | 0.5 | 0.3 |
| end card (`end_card`) | built in: about 6 s | – |

`beat(n, *anims, say=None, run_time=1.2, wait=0.8, lag=0.0)`: `run_time` applies to every animation of the beat (it overrides a helper's own `run_time`, so pass `run_time=1.5` for a `count_to`); `lag > 0` staggers the animations with `LaggedStart`; a beat without `say` keeps the caption lane as it is; `self.beat(n, wait=1.5)` is a pure pause.

## 6. Checklist for stills

Read one still per chapter (and the poster) and confirm:

- [ ] The header shows `n/N · title` and the hairline; the first chapter shows the brand name or logo left.
- [ ] No text crosses the frame edge (x beyond ±7.1) or the hairline (y above 3.1).
- [ ] At most 6 live elements; the rest dimmed or cleared.
- [ ] The caption lane holds exactly one caption, readable (22 pt, `muted`), clear of content (nothing below y = -2.6).
- [ ] Colours match the report: the same entity has the same badge colour in every chapter; errors `red`, new `green`.
- [ ] Labels are the report's identifiers verbatim.
