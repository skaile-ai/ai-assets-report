---
name: report-video
description: "3blue1brown-style explainer video of a process or algorithm with manim, embedded as a `video` block. Use only when the user asks for a video, animation or explainer."
metadata:
  version: 0.1.0
  publisher: mortegro
---

# report-video <topic>

Render a stepped, captioned explainer video of `<topic>` with manim Community and embed it as a `video` block.

Use this skill only when the user asks for a video, an animation or an explainer. `skill://report-html` offers it unchecked otherwise.

## Install
1. `manim --version || uv tool install "manim[typst]"`
2. `manim checkhealth`. LaTeX is not needed.
3. Set formulas with `Typst` or `MathTypst`. Never use `Tex` or `MathTex` (no LaTeX on this machine).
4. If the install fails, state the failure in chat and deliver the scene file only. Leave the `video` block out of the report; do not ship a block with a dead `src`.

## Write the scene

1. Copy [`scene_template.py`](scene_template.py) to `<report>.media/<id>.py`.
2. Fill the data at the top of the file:
   - `TITLE`: title card, from the question.
   - `STEPS = [(label, caption), …]`: three to six steps. The label is the box text (2-3 words). The caption is one sentence of at most 20 words that says what happens in this step.
   - `END`: end card text.
3. From a `flow` block: `nodes` in edge order → `label`; the label of the edge into the node → the caption sentence (add the verb). From the user's text: one step per stage the text names.
4. Keep the template's conventions: black background, manim palette (`BLUE`, `GREEN`, `YELLOW`), `JetBrains Mono` labels, one caption lane at the bottom that changes by `Transform`, `Create`/`GrowArrow`/`FadeIn` for new steps, `Indicate` on the current step, `self.wait(1)` after each caption.
5. Use one scene class. A step that needs another picture (a graph, a table, a formula) goes in a second scene file, not in a longer first scene.

## Render

Run in `<report>.media/` (create the folder next to the HTML):

```
manim -qm --format=mp4 -o <id> <id>.py Explainer
mv media/videos/<id>/720p30/<id>.mp4 <id>.mp4 && rm -rf media
ffmpeg -y -ss 12 -i <id>.mp4 -frames:v 1 <id>.jpg
```

- manim writes to `media/videos/<scene file name>/720p30/<id>.mp4`. The folder name follows the scene file.
- Take the poster from a frame where every step shows (after the last step appears). Use `-ss 1` for the title card.
- Keep `<id>.py` next to the video. Re-run the command to regenerate it.
- `-qm` is 720p30, about 3 s of render time for 3 steps. Use `-qh` only on request.

## Block

```
{ "type": "video", "id": "demo", "label": "Import pipeline",
  "src": "<report>.media/demo.mp4", "poster": "<report>.media/demo.jpg",
  "caption": "one sentence", "at": "path:line" }
```

- The `id` shares the diagram id space: it is unique among all diagram ids and the figure anchor is `#f-<id>`.
- The build fails with `video <id>: file not found <path>` when `src` or `poster` does not exist next to the output HTML. Build into the directory that holds the media folder.
- `caption` takes inline text (`code`, `[[id]]`). `at` adds the evidence table.
- A video has no ⤢ zoom and no node hover. The browser's own controls cover fullscreen.
- A report with a video is a folder: the HTML and `<report>.media/` move together.

## Alone

1. Collect the steps (Write the scene). Render the mp4 and the poster (Render). Stop: no HTML.
2. If the user wants a page: write a `report.json` with one `p` and the `video` block (copy `example.json`), build it into the directory of the media folder: `python3 ~/.agents/skills/report-html/build.py report.json <out>.html`.
3. Run Verify. State the path of the mp4 in chat.

## Under report-html

1. Do the Write-the-scene and Render steps. Put the media in `<out dir>/<report>.media/`, the same directory as the built HTML.
2. Hand the `video` block back to the orchestrator's section plan. Place it last, after the prose and the diagrams.
3. The orchestrator builds. Run Verify on the built page.

## Verify

- `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height <id>.mp4`: h264, 1280×720, duration > 0.
- Read the poster. All boxes and the caption are visible and no text is cut off.
- Build the example from the skill folder: `python3 ~/.agents/skills/report-html/build.py example.json example.html` builds. The same call with output `/tmp/x.html` fails with `video demo: file not found …` because the media is not beside it.
- In the browser: the `<video>` element has `readyState ≥ 1` after `load()`. The poster shows before play. Play moves `currentTime`.
- 390 px: `scrollWidth == 390`, no console errors.
- A block with a missing `src` fails the build with `video <id>: file not found <path>`.
