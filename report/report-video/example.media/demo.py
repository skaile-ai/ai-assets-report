"""Scenes of demo.script.md: one class per chapter. Render: manim -qm --format=mp4 demo.py"""

from brand import *


class Ch1Antwort(Explainer):
    CHAPTER, CHAPTERS, TITLE = 1, 3, "Antwort"

    def construct(self):
        self.title_card(
            "Vom Buch zum Screen",
            sub="Beispiel · Inhaltsbaum",
            meta="Quelle: lokales Directus (localhost:8059) · Stand: 2026-10-12",
        )
        key = self.text("Der Bereich „Im Alltag“ enthält zwei Screens.", H1, w=11.5).move_to(UP * 1.5)
        counters = VGroup(
            self.counter(1, "Bereiche"),
            self.counter(2, "Screens"),
            self.counter(1, "Entwürfe", "yellow"),
        ).arrange(RIGHT, buff=1.8).move_to(DOWN * 0.5)
        question = self.text("Doch wie wird aus einem Buch ein Screen?", H1, w=11.5).move_to(key)

        self.beat(1, FadeIn(key, shift=UP * 0.2), say="Der Bereich „Im Alltag“ enthält zwei Screens.", run_time=2.0, wait=1.0)
        self.beat(
            2,
            self.ring(key),
            FadeIn(counters),
            self.count_to(counters[0], 1),
            self.count_to(counters[1], 2),
            self.count_to(counters[2], 1),
            say="Der Bericht zählt einen Bereich, zwei Screens und einen Entwurf.",
            run_time=1.5,
        )
        self.beat(3, Transform(key, question), self.dim(*counters), say="Doch wie wird aus einem Buch ein Screen?", run_time=1.5)
        self.clear_stage()


class Ch2Ablauf(Explainer):
    CHAPTER, CHAPTERS, TITLE = 2, 3, "Ablauf"

    def construct(self):
        self.chapter_card()
        # flow `uebersicht`: nodes in edge order; orange = origin powerbook (entities imp, trigger), gray = external / store
        boxes, arrows = self.pipeline(
            ["Buch", "Kapitel importieren", "source_chapter", "Screen schreiben", "Leser"],
            colors=["gray", "orange", "gray", "orange", "gray"],
            subs=["chapters/*.md", "npm run import", "Directus", "Editor", None],
            gap=0.7,
        )
        labels = [self.edge_label(a, s) for a, s in zip(arrows, ["Kapitel", "Zeile", "Absätze", "Screen"])]
        labels[2].set_color(color_of("teal"))
        # edge kind `liest`: dotted, teal (the pipeline arrow stays as the path for the pulse)
        liest = DashedLine(
            arrows[2].get_start(), arrows[2].get_end(), dash_length=0.07, dashed_ratio=0.5, stroke_width=4, color=color_of("teal")
        ).add_tip(tip_length=0.2)

        self.beat(1, FadeIn(boxes[0]), FadeIn(boxes[1]), GrowArrow(arrows[0]), FadeIn(labels[0]), say="Der Import liest die Kapitel des Buchs.")
        self.beat(2, FadeIn(boxes[2]), GrowArrow(arrows[1]), FadeIn(labels[1]), say="Jedes Kapitel wird eine Zeile in source_chapter.")
        self.beat(3, FadeIn(boxes[3]), Create(liest), FadeIn(labels[2]), say="Der Editor liest daraus die Absätze.")
        self.beat(4, FadeIn(boxes[4]), GrowArrow(arrows[3]), FadeIn(labels[3]), say="Aus den Absätzen entsteht der Screen für den Leser.")
        self.beat(
            5,
            Succession(*[self.pulse(a, "teal" if i == 2 else "accent") for i, a in enumerate(arrows)]),
            say="So wandert ein Kapitel vom Buch zum Leser.",
            run_time=3.0,
        )
        self.clear_stage()


class Ch3Typen(Explainer):
    CHAPTER, CHAPTERS, TITLE = 3, 3, "Typen und Baum"

    def construct(self):
        self.chapter_card()
        # lineage `typen`: md -> cand -> row -> variant -> json
        types, arrows = self.pipeline(
            ["chapters/*.md", "ChapterCandidate", "source_chapter", "content_variant", "stations.json"],
            colors=["orange", "blue", "gray", "gray", "blue"],
            subs=["Markdown + YAML", "TS-Typ", "Directus-Zeile", "Directus-Zeile", "Build-Artefakt"],
            gap=0.5,
        )
        fns = ["readChapter()", "POST /items", "writeScreen()", "compileContent()"]
        labels = [self.edge_label(a, f) for a, f in zip(arrows, fns)]

        self.beat(1, FadeIn(types[0]), say="Am Anfang steht eine Markdown-Datei.")
        notes = [
            "readChapter() macht daraus einen ChapterCandidate.",
            "POST /items speichert ihn als Zeile in source_chapter.",
            "writeScreen() macht aus den Absätzen Blöcke je Zielgruppe.",
            "compileContent() erzeugt daraus die Datei stations.json.",
        ]
        for i, note in enumerate(notes):
            self.beat(
                i + 2,
                ReplacementTransform(types[i].copy(), types[i + 1]),
                GrowArrow(arrows[i]),
                FadeIn(labels[i]),
                say=note,
                run_time=1.5,
                wait=1.0,
            )
        self.clear_stage()

        # tree: Im Alltag > Trigger, Mach mal Pause; badges as in the report
        def row(label, level, chips):
            t = self.text(label, BODY, "fg")
            t.move_to(LEFT * 6.0 + RIGHT * 0.7 * level, aligned_edge=LEFT)
            c = VGroup(*chips).arrange(RIGHT, buff=0.2)
            c.move_to(RIGHT * -1.0 + UP * t.get_y(), aligned_edge=LEFT)
            return VGroup(t, c)

        rows = VGroup(
            row("Im Alltag", 0, [self.chip("Bereich", "gray")]),
            row("Trigger", 1, [self.chip("teen", "navy"), self.chip("young", "brown"), self.chip("powerbook", "orange")]),
            row("Mach mal Pause", 1, [self.chip("teen", "navy"), self.chip("authored", "pink"), self.chip("Entwurf", "yellow")]),
        )
        for r, y in zip(rows, [1.2, 0.1, -1.0]):
            r.set_y(y)
        shown = self.counter(2, "Screens sichtbar").move_to(RIGHT * 5.0 + UP * 0.1)

        self.beat(
            6,
            *[FadeIn(r, shift=RIGHT * 0.2) for r in rows],
            FadeIn(shown),
            self.count_to(shown, 2),
            say="Der Baum zeigt den Bereich mit seinen zwei Screens.",
            run_time=1.5,
        )
        self.beat(7, self.dim(rows[2]), self.count_to(shown, 1), say="Der Filter blendet den Entwurf aus, ein Screen bleibt.", run_time=1.5)
        self.end_card(["Ein Import macht aus dem Buch Zeilen und Screens.", "Ein Filter nimmt Entwürfe aus Baum und Zähler."])
