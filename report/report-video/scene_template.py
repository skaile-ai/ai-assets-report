"""Stepped, captioned explainer scene (3blue1brown conventions: black background, manim palette).

Fill TITLE, END and STEPS, then render:
    manim -qm --format=mp4 -o <id> scene.py Explainer
Output: media/videos/scene/720p30/<id>.mp4 (folder name follows the file name `scene`).
Text only: no LaTeX needed. Use `Typst`/`MathTypst` for formulas, never `Tex`/`MathTex`.
"""
from manim import (
    BLUE, YELLOW, GREEN, WHITE, GREY_B, UP, DOWN, RIGHT,
    Scene, Text, VGroup, RoundedRectangle, Arrow, Transform,
    Create, GrowArrow, FadeIn, FadeOut, Indicate, config,
)

TITLE = "Import pipeline"          # title card
END = "Done"                       # end card
FONT = "JetBrains Mono"            # falls back to a system font when missing
# (box label, caption shown while the step is current). From a `flow` block: node label, label of the edge into it.
STEPS = [
    ("Read book", "The importer reads the book from the source."),
    ("Build screens", "It builds one screen for each page."),
    ("Publish", "It publishes the screens to the app."),
]

PALETTE = [BLUE, GREEN, YELLOW]    # box colours, cycled over the steps


def label(text, size=28, color=WHITE):
    return Text(text, font=FONT, font_size=size, color=color)


class Explainer(Scene):
    def construct(self):
        # title card
        title = label(TITLE, 48)
        self.play(FadeIn(title, shift=UP * 0.3))
        self.wait(1)
        self.play(title.animate.scale(0.5).to_edge(UP))

        # layout: one row, boxes share the frame width
        n = len(STEPS)
        gap = 0.9
        box_w = min(3.2, (config.frame_width - 1.0 - gap * (n - 1)) / n)
        boxes = VGroup()
        for i, (text, _) in enumerate(STEPS):
            col = PALETTE[i % len(PALETTE)]
            txt = label(text, 24)
            if txt.width > box_w - 0.4:
                txt.scale_to_fit_width(box_w - 0.4)
            box = RoundedRectangle(corner_radius=0.15, width=box_w, height=1.4, color=col)
            txt.move_to(box)
            boxes.add(VGroup(box, txt))
        boxes.arrange(RIGHT, buff=gap).move_to(UP * 0.3)  # slightly above centre: the caption lane stays clear
        arrows = [Arrow(boxes[i].get_right(), boxes[i + 1].get_left(), buff=0.1, color=GREY_B)
                  for i in range(n - 1)]

        # caption lane: one Text, transformed per step
        caption = label(STEPS[0][1], 26, GREY_B).to_edge(DOWN, buff=0.8)

        for i, (_, cap) in enumerate(STEPS):
            anims = [Create(boxes[i][0]), FadeIn(boxes[i][1])]
            if i:
                anims.append(GrowArrow(arrows[i - 1]))
            new_cap = label(cap, 26, GREY_B).to_edge(DOWN, buff=0.8)
            if new_cap.width > config.frame_width - 1:
                new_cap.scale_to_fit_width(config.frame_width - 1)
            if i == 0:
                caption.become(new_cap)
                anims.append(FadeIn(caption))
            else:
                anims.append(Transform(caption, new_cap))
            self.play(*anims)
            self.play(Indicate(boxes[i], color=YELLOW))
            self.wait(1)

        # end card
        self.play(FadeOut(caption), FadeOut(boxes), *[FadeOut(a) for a in arrows], FadeOut(title))
        end = label(END, 44, YELLOW)
        self.play(FadeIn(end))
        self.wait(1)
        self.play(FadeOut(end))

