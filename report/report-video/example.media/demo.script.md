# Vom Buch zum Screen

- report: ../report-html/example.json
- lang: de
- brand: default
- arc: build-up
- target: 75 s

## 1. Antwort {scene=Ch1Antwort section=answer}
Goal: Der Zuschauer weiß, was der Bericht zählt und welche Frage er beantwortet.
Carry: Der Satz „Der Bereich „Im Alltag“ enthält zwei Screens.“ wird zur Frage nach dem Weg vom Buch zum Screen.
Concepts: stats Bereiche, Screens, Entwürfe; [[alltag]]
Shots: FULL_CENTER → GRID → FULL_CENTER

1. Der Schlüsselsatz erscheint | text(H1)
   > Der Bereich „Im Alltag“ enthält zwei Screens.
2. Drei Zähler laufen hoch, ein Rahmen markiert den Satz | counter, count_to, ring
   > Der Bericht zählt einen Bereich, zwei Screens und einen Entwurf.
3. Der Satz wird zur Frage, die Zähler treten zurück | Transform, dim
   > Doch wie wird aus einem Buch ein Screen?

## 2. Ablauf {scene=Ch2Ablauf section=ablauf}
Goal: Der Zuschauer kennt die fünf Stationen vom Buch bis zum Leser und die Richtung der Daten.
Carry: Die Pipeline Buch → Kapitel importieren → source_chapter → Screen schreiben → Leser.
Concepts: flow uebersicht; [[imp]]; [[trigger]]
Shots: FULL_CENTER

1. Buch und Import mit der Kante „Kapitel“ | pipeline, FadeIn, GrowArrow, edge_label
   > Der Import liest die Kapitel des Buchs.
2. source_chapter mit der Kante „Zeile“ | FadeIn, GrowArrow, edge_label
   > Jedes Kapitel wird eine Zeile in source_chapter.
3. Screen schreiben mit der gepunkteten Kante „Absätze“ (liest, teal) | DashedLine, Create, edge_label
   > Der Editor liest daraus die Absätze.
4. Leser mit der Kante „Screen“ | FadeIn, GrowArrow, edge_label
   > Aus den Absätzen entsteht der Screen für den Leser.
5. Ein Lichtpunkt läuft über alle Kanten | pulse, Succession
   > So wandert ein Kapitel vom Buch zum Leser.

## 3. Typen und Baum {scene=Ch3Typen section=typen}
Goal: Der Zuschauer sieht, welcher Typ aus welchem entsteht, und wie der Filter einen Entwurf aus dem Baum nimmt.
Carry: Die Kette chapters/*.md bis stations.json, danach der Baum mit dem Zähler „Screens sichtbar“.
Concepts: lineage typen; tree; [[trigger]]; [[pause]]; badge flag draft
Shots: FULL_CENTER → LEFT_RIGHT → end_card (zwei Kernaussagen, ohne Erzähltext)

1. Der Typ chapters/*.md steht allein | pipeline, FadeIn
   > Am Anfang steht eine Markdown-Datei.
2. ChapterCandidate entsteht aus der Datei | ReplacementTransform, edge_label
   > readChapter() macht daraus einen ChapterCandidate.
3. source_chapter entsteht aus dem Kandidaten | ReplacementTransform, edge_label
   > POST /items speichert ihn als Zeile in source_chapter.
4. content_variant entsteht aus der Zeile | ReplacementTransform, edge_label
   > writeScreen() macht aus den Absätzen Blöcke je Zielgruppe.
5. stations.json entsteht aus der Variante | ReplacementTransform, edge_label
   > compileContent() erzeugt daraus die Datei stations.json.
6. Die Bühne wird leer, der Baum erscheint mit Badges und Zähler | clear_stage, stack, chip, counter, count_to
   > Der Baum zeigt den Bereich mit seinen zwei Screens.
7. Der Entwurf tritt zurück, der Zähler fällt auf 1 | dim, count_to
   > Der Filter blendet den Entwurf aus, ein Screen bleibt.
