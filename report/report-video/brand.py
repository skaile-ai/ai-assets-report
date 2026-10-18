"""brand.py: the look and the building blocks every explainer scene imports.

The skill copies this file next to the scene file (`<stem>.media/`), so the media
folder stays self-contained. Nothing here needs more than the standard library
and manim (Community 0.22, no LaTeX).

A scene file looks like this::

    from brand import *

    class Ch1Answer(Explainer):
        CHAPTER, CHAPTERS, TITLE = 1, 3, "Answer"
        VIDEO_TITLE = "Report title"          # optional: header text when the brand has no name

        def construct(self):
            self.title_card("Report title", sub="One-line promise", meta="2026-10-18")
            boxes, arrows = self.pipeline(["read", "parse", "render"], colors=["blue", "teal", "green"])
            self.beat(1, FadeIn(boxes), say="The pipeline has three steps.")
            self.beat(2, self.pulse(arrows[0]), say="Data moves from read to parse.", run_time=1.0)
            self.end_card(["First takeaway", "Second takeaway"])

Rules this module enforces: all text fits its width (`text()`); a pipeline never
exceeds the usable width (`pipeline()`); the caption lane is one mobject that is
replaced by `Transform` (never two captions at once); `clear_stage()` keeps the
header and the caption lane.

Timing: `beat(n, ..., say=...)` waits for the measured narration length of
(CHAPTER, n) from `timestamps.json` (written by `narrate.py`), else for an
estimate of `words / 2.5 + 0.6` s; `say` must equal the script line there. `tear_down()` records the start time of every
beat in `beats.json`; `stitch.py` places the voice clips with it.

Brand lookup (`load_brand()`): `REPORT_BRAND` (a path) > `<stem>.brand.json` next
to the media folder > `brand.json` next to it > the defaults below.
"""

from __future__ import annotations

import json
import math
import os
import sys
import textwrap
from pathlib import Path

from manim import *  # noqa: F403  (scenes get the whole manim namespace through `from brand import *`)

# --------------------------------------------------------------------------- brand

DEFAULTS = {
    "name": "",
    "tagline": "",
    "logo": None,  # path relative to the brand file
    "bg": "#0d1117",
    "fg": "#e6edf3",
    "muted": "#8b949e",
    "rule": "#30363d",
    "accent": "#58a6ff",
    # same names as the report's badge colour tokens
    "colors": {
        "purple": "#a371f7",
        "blue": "#58a6ff",
        "green": "#3fb950",
        "gray": "#8b949e",
        "orange": "#db6d28",
        "pink": "#db61a2",
        "teal": "#39c5cf",
        "yellow": "#d29922",
        "red": "#f85149",
        "navy": "#388bfd",
        "brown": "#bd561d",
        "ink": "#e6edf3",
    },
    "font": None,  # None = first installed font of FONT_CHAIN
    "voice": {"provider": "auto", "voice_id": None, "model_id": "eleven_multilingual_v2", "say_voice": None},
}
FONT_CHAIN = ["JetBrains Mono", "Menlo", "DejaVu Sans Mono", "Monospace"]


def load_brand() -> dict:
    """Defaults, overridden by the brand file found by the lookup order above."""
    brand = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    here = Path.cwd()
    stem = here.name[: -len(".media")] if here.name.endswith(".media") else here.name
    env = os.environ.get("REPORT_BRAND")
    if env:
        path = Path(env).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"REPORT_BRAND points to a missing file: {path}")
    else:
        path = next(
            (p for p in (here.parent / f"{stem}.brand.json", here.parent / "brand.json") if p.is_file()),
            None,
        )
    if path is not None:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in data.items():
            if key in ("colors", "voice") and isinstance(value, dict):
                brand[key].update(value)
            else:
                brand[key] = value
        if brand.get("logo"):
            brand["logo"] = str((path.parent / brand["logo"]).resolve())
    return brand


def resolve_font(brand: dict) -> str:
    """The brand font, else the first installed font of FONT_CHAIN."""
    if brand.get("font"):
        return brand["font"]
    try:
        import manimpango  # lazy: only needed when the brand names no font

        installed = set(manimpango.list_fonts())
    except Exception:  # enumeration can fail depending on the cwd or the pango build
        return "Menlo" if sys.platform == "darwin" else "DejaVu Sans Mono"
    return next((f for f in FONT_CHAIN if f in installed), FONT_CHAIN[-1])


BRAND = load_brand()
FONT = resolve_font(BRAND)
COLORS = BRAND["colors"]

TITLE, H1, BODY, LABEL, CAPTION, SMALL = 48, 36, 28, 22, 22, 18
FRAME_W = config.frame_width - 1.0  # usable width
HEADER_Y = 3.1  # the hairline under the header
BUDGET_PAD = 0.15  # seconds added to a measured narration budget (frame rounding; keeps stitch's guard quiet)

_SPECIAL = {k: BRAND[k] for k in ("bg", "fg", "muted", "rule", "accent")}


def color_of(name):
    """Brand colour by name (`fg`, `muted`, `accent`, `rule`, `bg` or a badge colour), else the value as given."""
    if name is None:
        return BRAND["fg"]
    return _SPECIAL.get(name) or COLORS.get(name) or name


class _Digit(Text):
    """Text with the brand font; the label constructor for DecimalNumber and axes (no LaTeX)."""

    def __init__(self, s, **kwargs):
        kwargs.setdefault("font", FONT)
        super().__init__(str(s), **kwargs)


_GLYPHS: dict = {}


def _glyphs() -> dict:
    """Outline points of `0-9` and `,` relative to a slot centre (monospace font), plus the advance and digit height; built once."""
    if not _GLYPHS:
        ref = _Digit("000", font_size=TITLE)
        first = ref[0].get_center()
        _GLYPHS["adv"] = float(ref[2].get_center()[0] - first[0]) / 2
        _GLYPHS["h"] = float(ref[0].height)
        for ch in "0123456789,":
            t = _Digit("0" + ch + "0", font_size=TITLE)
            c0 = t[0].get_center()
            shift = np.array([c0[0] + _GLYPHS["adv"], c0[1], 0.0])
            _GLYPHS[ch] = t[1].points - shift
    return _GLYPHS


class _Odometer(VGroup):
    """Integer display with a fixed set of digit slots, so its family never changes size while it counts
    (a FadeIn of the same counter can share the play). Slot 0 is an invisible ruler that carries position and scale."""

    def __init__(self, n_slots: int, color):
        g = _glyphs()
        ruler = Rectangle(width=n_slots * g["adv"], height=g["h"], stroke_width=0, fill_opacity=0)
        slots = [VMobject().set_fill(color, opacity=1).set_stroke(width=0) for _ in range(n_slots)]
        super().__init__(ruler, *slots)
        self.n_slots = n_slots
        self.value = 0
        self.show(0)

    def show(self, value):
        g = _glyphs()
        text = f"{int(round(value)):,}"
        if len(text) > self.n_slots:
            raise ValueError(f"counter has {self.n_slots} digit slots, {text!r} does not fit; create it with the largest value")
        ruler = self.submobjects[0]
        scale = ruler.width / (self.n_slots * g["adv"])
        left = (self.n_slots - len(text)) / 2
        for i, slot in enumerate(self.submobjects[1:]):
            if i >= len(text):
                slot.set_points(np.tile(ruler.get_center(), (4, 1)))  # a point, not nothing: animations zip only family members that have points
                continue
            x = (left + i - (self.n_slots - 1) / 2) * g["adv"]
            slot.set_points(g[text[i]] * scale + ruler.get_center() + np.array([x * scale, 0.0, 0.0]))
        self.value = int(round(value))


class _CountTo(Animation):
    """Run an `_Odometer` from its value at the start of the play to `value`."""

    def __init__(self, counter, value, **kwargs):
        if len(f"{int(round(value)):,}") > counter.number.n_slots:
            raise ValueError("count_to: value has more digits than the counter was created for")
        self.target_value = value
        self.start_value = 0
        super().__init__(counter.number, **kwargs)

    def begin(self):
        self.start_value = self.mobject.value
        super().begin()

    def interpolate_mobject(self, alpha):
        self.mobject.show(self.start_value + (self.target_value - self.start_value) * self.rate_func(alpha))


def _nice_step(top: float) -> float:
    raw = top / 5
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    return next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)


def _scaled_opacity(mob, k: float):
    """A copy of `mob` whose fill and stroke opacity are k times the opacity it was first drawn with."""
    for sm in mob.get_family():
        if isinstance(sm, VMobject) and not hasattr(sm, "_op0"):
            sm._op0 = (sm.get_fill_opacity(), sm.get_stroke_opacity())
    target = mob.copy()
    for src, sm in zip(mob.get_family(), target.get_family()):
        if isinstance(sm, VMobject):
            fill, stroke = getattr(src, "_op0", (sm.get_fill_opacity(), sm.get_stroke_opacity()))
            sm.set_fill(opacity=fill * k)
            sm.set_stroke(opacity=stroke * k)
            sm._op0 = (fill, stroke)
    return target


# --------------------------------------------------------------------------- scene


class Explainer(Scene):
    """One chapter of the video. Subclasses set CHAPTER, CHAPTERS, TITLE (and optionally VIDEO_TITLE)."""

    CHAPTER: int = 1
    CHAPTERS: int = 1
    TITLE: str = ""
    VIDEO_TITLE: str = ""

    # ---- lifecycle

    def setup(self):
        super().setup()
        self.camera.background_color = BRAND["bg"]
        self.budget: dict[tuple[int, int], float] = {}
        self.script_text: dict[tuple[int, int], str] = {}
        stamps = Path("timestamps.json")
        stamps_title = ""
        if stamps.is_file():
            data = json.loads(stamps.read_text(encoding="utf-8"))
            stamps_title = data.get("title") or ""
            for b in data.get("beats", []):
                self.budget[(int(b["chapter"]), int(b["beat"]))] = float(b["duration_s"])
                if b.get("text") is not None:
                    self.script_text[(int(b["chapter"]), int(b["beat"]))] = str(b["text"])
        self.caption = None
        self._beats: list[dict] = []
        self._video_title = self.VIDEO_TITLE or stamps_title
        self._chrome_shown = False
        self.chrome = self._build_chrome()

    def tear_down(self):
        super().tear_down()
        path = Path("beats.json")
        entries = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
        name = type(self).__name__
        entries = [e for e in entries if e.get("scene") != name]
        entries.append({"scene": name, "chapter": self.CHAPTER, "beats": self._beats})
        entries.sort(key=lambda e: e.get("chapter", 0))
        path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- chrome

    def _brand_name(self) -> str:
        return BRAND["name"] or self._video_title

    def _logo(self, height: float):
        logo = ImageMobject(BRAND["logo"])
        logo.scale_to_fit_height(height)
        return logo

    def _left_item(self):
        """Header-left mobject: the logo, else the name (brand name, VIDEO_TITLE, timestamps title, title_card title), else None."""
        left_x = -config.frame_width / 2 + 0.5
        if BRAND["logo"]:
            item = self._logo(0.55)
        elif self._brand_name():
            item = self.text(self._brand_name(), SMALL, "muted", w=FRAME_W * 0.35)
        else:
            return None
        return item.move_to(UP * 3.55).align_to(left_x * RIGHT, LEFT)

    def _build_chrome(self):
        left_x = -config.frame_width / 2 + 0.5
        right_x = config.frame_width / 2 - 0.5
        parts = []
        left = self._left_item()
        self._has_left = left is not None
        if left is not None:
            parts.append(left)
        where = self.text(f"{self.CHAPTER}/{self.CHAPTERS} · {self.TITLE}", SMALL, "muted", w=FRAME_W * 0.55)
        parts.append(where.move_to(UP * 3.55).align_to(right_x * RIGHT, RIGHT))
        parts.append(Line(left_x * RIGHT + UP * HEADER_Y, right_x * RIGHT + UP * HEADER_Y, stroke_color=BRAND["rule"], stroke_width=1.5))
        return Group(*parts)

    def _show_chrome(self, animated: bool = False):
        """Show the header once. Cards call it with animation after they fade out; `beat()` calls it plainly."""
        if self._chrome_shown:
            return
        self._chrome_shown = True
        if animated:
            self.play(FadeIn(self.chrome), run_time=0.5)
        else:
            self.add(self.chrome)

    # ---- text

    def text(self, s, size=BODY, color=None, w=None, weight=NORMAL):
        """Text in the brand font that never exceeds `w` (default: the usable frame width)."""
        m = Text(s, font=FONT, font_size=size, color=color_of(color), weight=weight)
        limit = FRAME_W if w is None else w
        if m.width > limit:
            m.scale_to_fit_width(limit)
        return m

    def _caption_mob(self, say: str):
        wrapped = "\n".join(textwrap.wrap(say, width=80))
        return self.text(wrapped, CAPTION, "muted").to_edge(DOWN, buff=0.5)

    # ---- the unit of the script

    def beat(self, n, *anims, say=None, run_time=1.2, wait=0.8, lag=0.0):
        """Beat `n` of this chapter: play `anims`, show the narration line `say` in the caption lane, hold for the narration budget.

        The budget is the measured narration length of (CHAPTER, n) from `timestamps.json`, used whether or not `say` is given
        (a beat whose script line has narration holds for it; without `say` the caption lane stays as it is). Without a
        measurement and with `say`, it is estimated from the word count. When `timestamps.json` holds text for this beat,
        `say` must equal it (whitespace aside); a difference raises ValueError.
        """
        self._show_chrome()
        anims = sorted(anims, key=lambda a: isinstance(a, _CountTo))  # a count must run after a FadeIn of the same counter
        self._beats.append({"beat": n, "t0": round(float(self.time), 3)})
        measured = self.budget.get((self.CHAPTER, n))
        scripted = self.script_text.get((self.CHAPTER, n))
        if say and scripted is not None and " ".join(say.split()) != " ".join(scripted.split()):
            raise ValueError(f"beat {n}: say= differs from the script narration in timestamps.json; run narrate.py again or copy the line")
        budget = wait
        if measured is not None:
            budget = measured + BUDGET_PAD
        elif say:
            budget = len(say.split()) / 2.5 + 0.6
        caption_anim = None
        if say:
            self.add_subcaption(say, duration=max(budget - BUDGET_PAD, 0.5))  # ends just before the next beat's cue
            new = self._caption_mob(say)
            if self.caption is None:
                caption_anim, self.caption = FadeIn(new), new
            else:
                caption_anim = Transform(self.caption, new)
        plays = [LaggedStart(*anims, lag_ratio=lag)] if lag > 0 and anims else list(anims)
        if caption_anim is not None:
            plays.append(caption_anim)
        if not plays:  # a pure pause
            if max(wait, budget) > 0:
                self.wait(max(wait, budget))
            return
        self.play(*plays, run_time=run_time)
        hold = max(wait, budget - run_time)
        if hold > 0:
            self.wait(hold)

    # ---- cards

    def title_card(self, title, sub=None, meta=None):
        """Full-screen opening card (chapter 1); the header appears when it is gone."""
        self._video_title = self._video_title or title
        if not self._has_left:  # no brand name, VIDEO_TITLE or timestamps title: the card's title fills the header-left slot
            left = self._left_item()
            self.chrome.add(left)
            self._has_left = True
        parts = [self.text(title, TITLE, "fg", weight=BOLD)]
        parts.append(Line(LEFT * 2, RIGHT * 2, stroke_color=BRAND["accent"], stroke_width=4))
        if sub:
            parts.append(self.text(sub, H1, "muted"))
        if meta:
            parts.append(self.text(meta, SMALL, "muted"))
        card = VGroup(*parts).arrange(DOWN, buff=0.4).move_to(ORIGIN)
        self.play(FadeIn(card, shift=UP * 0.3))
        self.wait(2)
        self.play(FadeOut(card))
        self._show_chrome(animated=True)

    def chapter_card(self):
        """Chapter number and title; the header appears when it is gone."""
        num = self.text(str(self.CHAPTER), TITLE, "accent", weight=BOLD)
        title = self.text(self.TITLE, H1, "fg", w=FRAME_W - num.width - 0.5)
        card = VGroup(num, title).arrange(RIGHT, buff=0.5).move_to(ORIGIN)
        self.play(FadeIn(card, shift=UP * 0.3))
        self.wait(1.5)
        self.play(FadeOut(card))
        self._show_chrome(animated=True)

    def end_card(self, lines):
        """Closing card: brand, tagline, up to three takeaways; fades out everything."""
        if len(lines) > 3:
            raise ValueError("end_card takes at most 3 takeaways")
        self.clear_stage(keep_caption=False)
        head = Group(self._logo(0.9) if BRAND["logo"] else self.text(self._brand_name() or self.TITLE, H1, "fg", weight=BOLD))
        if BRAND["tagline"]:
            head.add(self.text(BRAND["tagline"], LABEL, "muted"))
        head.arrange(DOWN, buff=0.25)
        rows = self.stack([f"• {line}" for line in lines], "fg", BODY)
        Group(head, rows).arrange(DOWN, buff=0.8).move_to(ORIGIN)
        self.play(FadeIn(head))
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in rows], lag_ratio=0.3))
        self.wait(2.5)
        self.play(FadeOut(*self.mobjects))

    def clear_stage(self, run_time=0.5, keep_caption=True):
        """Fade out everything except the header (and the caption lane)."""
        keep = [self.chrome] + ([self.caption] if keep_caption and self.caption is not None else [])
        gone = [m for m in self.mobjects if all(m is not k for k in keep)]
        if gone:
            self.play(FadeOut(*gone), run_time=run_time)
        self.wait(0.3)

    # ---- shapes

    def box(self, label, color="blue", sub=None, w=2.8, h=1.3):
        """Rounded box in a badge colour with a label and an optional sub line."""
        c = color_of(color)
        rect = RoundedRectangle(
            width=w, height=h, corner_radius=0.15, stroke_color=c, fill_color=c, fill_opacity=0.12, stroke_width=3
        )
        limit = w - 0.4
        probe = self.text(label, LABEL, "fg")
        if probe.width > limit and " " in label:  # wrap at the space nearest the middle before shrinking
            cut = min((i for i, ch in enumerate(label) if ch == " "), key=lambda i: abs(i - len(label) / 2))
            label = label[:cut] + "\n" + label[cut + 1 :]
        lab = self.text(label, LABEL, "fg", w=limit)
        if sub:
            sub_mob = self.text(sub, SMALL, "muted", w=limit)
            VGroup(lab, sub_mob).arrange(DOWN, buff=0.12).move_to(rect.get_center())
            parts = [rect, lab, sub_mob]
        else:
            lab.move_to(rect.get_center())
            parts = [rect, lab]
        group = VGroup(*parts)
        group.rect = rect
        return group

    def pipeline(self, labels, colors=None, subs=None, gap=0.8):
        """Boxes joined by arrows: one row up to 5, a two-row snake for 6-8. Returns (boxes, arrows)."""
        n = len(labels)
        if not 1 <= n <= 8:
            raise ValueError("pipeline takes 1-8 labels")
        cols = n if n <= 5 else math.ceil(n / 2)
        bw = min(2.8, (FRAME_W - gap * (cols - 1)) / cols)
        bh, row_gap = 1.3, 1.0
        colors = list(colors) if colors else ["blue"]
        subs = list(subs) if subs else []
        boxes = VGroup()
        for i, label in enumerate(labels):
            b = self.box(label, colors[i % len(colors)], subs[i] if i < len(subs) and subs[i] else None, w=bw, h=bh)
            row = i // cols
            col = i % cols if row == 0 else cols - 1 - (i % cols)  # second row runs right to left
            x = (col - (cols - 1) / 2) * (bw + gap)
            y = 0.0 if n <= 5 else (0.5 - row) * (bh + row_gap)
            b.move_to(RIGHT * x + UP * y)
            boxes.add(b)
        arrows = []
        for a, b in zip(boxes[:-1], boxes[1:]):
            if abs(a.get_center()[1] - b.get_center()[1]) < 0.01:  # same row
                direction = RIGHT if b.get_center()[0] > a.get_center()[0] else LEFT
                arrow = Arrow(a.get_edge_center(direction), b.get_edge_center(-direction), buff=0.1, color=BRAND["muted"])
            else:  # row wrap: straight down
                arrow = Arrow(a.get_bottom(), b.get_top(), buff=0.1, color=BRAND["muted"])
            arrows.append(arrow)
        return boxes, arrows

    def pulse(self, arrow, color="accent"):
        """Animation: a bright segment travelling along an edge (data moving)."""
        return ShowPassingFlash(arrow.copy().set_stroke(color_of(color), 6), time_width=0.5)

    def edge_label(self, arrow, s):
        """Small muted label for an arrow: above it when it fits the gap, else above the box row (half a default box height up)."""
        label = self.text(s, SMALL, "muted", w=2.0)
        vector = arrow.get_end() - arrow.get_start()
        if abs(vector[1]) > abs(vector[0]):  # vertical arrow: label to the right
            return label.next_to(arrow.get_center(), RIGHT, buff=0.1)
        if label.width <= arrow.get_length():
            return label.next_to(arrow.get_center(), UP, buff=0.1)
        return label.next_to(arrow.get_center() + UP * 0.65, UP, buff=0.15)

    def chip(self, s, color):
        """Badge pill: coloured text on a tinted rounded rectangle."""
        c = color_of(color)
        t = self.text(s, SMALL, color)
        pill = RoundedRectangle(
            width=t.width + 0.4, height=0.42, corner_radius=0.21, stroke_color=c, fill_color=c, fill_opacity=0.18, stroke_width=2
        )
        t.move_to(pill.get_center())
        group = VGroup(pill, t)
        group.rect = pill
        return group

    def counter(self, value, label, color="accent"):
        """A number that starts at 0 above a muted label; animate it with `count_to`. `value` is the largest value it will show (sets the digit slots)."""
        number = _Odometer(len(f"{int(round(value)):,}"), color_of(color))
        group = VGroup(number, self.text(label, SMALL, "muted", w=3.5)).arrange(DOWN, buff=0.2)
        group.number = number
        return group

    def count_to(self, counter, value, run_time=1.5):
        """Animation: the counter's number runs from its current value to `value`. May share a beat with `FadeIn(counter)`; `beat()` plays it last."""
        return _CountTo(counter, value, run_time=run_time, rate_func=rush_from)

    def bars(self, rows, w=8, h=3.5):
        """Bar chart from rows of (name, value) or (name, value, colour name). Returns the chart (bars, axes, value labels)."""
        names = [r[0] for r in rows]
        values = [r[1] for r in rows]
        cols = [color_of(r[2]) if len(r) > 2 else color_of("blue") for r in rows]
        top = max(values) * 1.15 or 1
        axis = {"font_size": SMALL, "label_constructor": _Digit, "color": BRAND["muted"], "stroke_width": 2}
        chart = BarChart(
            values,
            bar_names=names,
            bar_colors=cols,
            y_range=(0, top, _nice_step(top)),
            x_length=w,
            y_length=h,
            x_axis_config=dict(axis),
            y_axis_config={**axis, "decimal_number_config": {"color": BRAND["muted"], "num_decimal_places": 0}},
        )
        slot = w / len(rows)
        for lab in chart.x_axis.labels:
            lab.set_color(BRAND["muted"])
            if lab.width > slot * 0.95:
                lab.scale_to_fit_width(slot * 0.95)
        chart.value_labels = chart.get_bar_labels(font_size=SMALL, label_constructor=_Digit, buff=0.15)
        chart.add(chart.value_labels)
        return chart

    def stack(self, items, color="fg", size=BODY):
        """Rows of text, left-aligned, top to bottom; reveal one row per beat."""
        rows = VGroup(*[self.text(i, size, color) for i in items]).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        if rows.height > 5.0:
            rows.scale_to_fit_height(5.0)
        return rows

    # ---- opacity layers and emphasis

    def dim(self, *m):
        """Animation: step the mobjects back to 0.4 of their opacity."""
        return AnimationGroup(*[Transform(x, _scaled_opacity(x, 0.4)) for x in m])

    def structural(self, *m):
        """Animation: step the mobjects back to 0.15 of their opacity (frame, background structure)."""
        return AnimationGroup(*[Transform(x, _scaled_opacity(x, 0.15)) for x in m])

    def hi(self, m):
        """Animation: a short pulse in the accent colour."""
        return Indicate(m, color=BRAND["accent"], scale_factor=1.05)

    def ring(self, m):
        """Animation: a rectangle drawn around the mobject, then gone."""
        return Circumscribe(m, color=BRAND["accent"], fade_out=True)
