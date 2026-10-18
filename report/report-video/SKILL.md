---
name: report-video
description: "Chaptered, narrated manim explainer of a report's main concepts with a brand look, embedded as a `video` block with captions and chapters. Use only when the user asks for a video, animation or explainer."
metadata:
  version: 0.2.0
  publisher: skaile-ai
---

# report-video <report.json | topic>

Turn a report's main concepts (the answer, the chosen questions, entities, diagrams, numbers) into a chaptered, branded explainer video. Output in `<stem>.media/`: `<id>.script.md`, `<id>.py`, `brand.py`, `timestamps.json`, `<id>.mp4` (mp4 chapter markers, AAC voice when a TTS exists), `<id>.vtt`, `<id>.jpg`, `<id>.block.json`; the `video` block carries `track` and `chapters`, so `build.py` renders a caption track and a clickable chapter list.

Use this skill only when the user asks for a video, an animation or an explainer. `skill://report-html` offers it unchecked otherwise. Inputs: a built `report.json` (under report-html), or the user's text alone.

Reading contract: follow `skill://report-html` (citations, labels, answer-first). The video is supplementary: the prose of the report MUST answer the question without it. It goes last and the reader starts it (the block has controls and no autoplay).

Read [`TECHNIQUES.md`](TECHNIQUES.md) before you write the script and again before you write the scenes. It holds the visual grammar, the arc per profile, the block → shot table, the layouts, the pacing and the checklist for stills.

One video per media folder: `timestamps.json` and `beats.json` are per folder. A second video gets its own `<stem>.media/`.

## Install

1. `manim --version || uv tool install "manim[typst]"`, then `manim checkhealth`. Check `ffmpeg -version` and `ffprobe -version`.
2. Set formulas with `Typst` or `MathTypst`. LaTeX is not installed (`Tex`/`MathTex` fail).
3. TTS: `narrate.py --provider auto` picks ElevenLabs (`ELEVENLABS_API_KEY` in the environment, in a `.env` from cwd upward, or in `~/.env`), else macOS `say`, else captions only. A harness TTS tool (omp `tts`) works through the `dir` provider (see Narrate).
4. Install fails → state the failure in chat, deliver the script and the scene file, leave the `video` block out. A block with a dead `src` fails the build.

## Brief

Read `report.json`: `title`, `meta`, `stats`, the first section (the answer), every section with `question` in order, `entities` with their badges, the diagrams (`flow`, `states`, `lineage`, `map`, `mermaid`), `tree`, charts, `since`. Plan the chapters:

- Chapter 1 is the answer: a hook sentence, the answer in at most 3 sentences, the `stats` as counters.
- One chapter per chosen question in section order. Merge two thin sections into one chapter.
- The last chapter is the verdict or the next step. Critique: the "fix first" items. Explanation: a replay of the full pipeline with pulses. Comparison: the verdict. Inventory/exploration: the gaps.
- At most 6 chapters including the last one. With more questions, keep the ones that hold a diagram, tree or chart first, then the earliest.
- 20-40 s and 3-7 beats per chapter. The language is the report's `lang`.
- Alone, without a report: the user's text supplies the chapters, one chapter per stage the text names.

Done when you hold a list of chapters, each with its section, the concepts it must show and its role in the arc (`TECHNIQUES.md`, Arc per profile).

## Script

Write `<stem>.media/<id>.script.md`. `narrate.py` and `stitch.py` parse it with one parser, so the grammar is exact:

```
# <Video title>                                   ← H1: title card and block `label`
- report: <stem>.json                             ← key/value list, any order
- lang: de
- brand: default | <path>
- arc: build-up | problem-solution | comparison | data-story | before-after
- target: 150 s

## 1. <Chapter title> {scene=Ch1Answer section=answer}   ← H2: number, title, attributes in braces
Goal: <one sentence: what the viewer knows after the chapter>
Carry: <the object that stays on screen or returns; "none" allowed>
Concepts: <[[entity]] ids, stat labels, diagram ids this chapter must show>
Shots: <layout names per beat, e.g. FULL_CENTER → LEFT_RIGHT>

1. <what appears or changes> | <technique or brand.py helper>
   > <narration: one sentence, ≤ 20 words, ASD-STE100>
2. <...> | <...>
   > <...>
3. <pure pause or silent reveal>                   ← a beat without a `>` line is silent
```

- `section=` is the `question` id of the report section: `answer` for the first section, `end` for the closing chapter. Each `scene=` name is used once.
- Chapters count from 1 in order, beats from 1 per chapter. Narration is exactly one `>` line directly under its beat; a second `>` line under the same beat fails. Only the chapter fields (Goal, Carry, Concepts, Shots) take indented continuation lines, not beats or narration.
- `narrate.py` fails with `narrate: <file>:<line>: <reason>` on a heading without `scene=`, a number out of sequence, a chapter without beats, or narration over 30 words. The style rule is 20 words, one sentence, `skill://report-asd-ste100`.
- Every beat is one visual change. `Concepts` names only ids that exist in `report.json`. `Carry` is the spine of the video: the object the viewer follows.
- The script's `lang` picks the `say` voice; the caption track takes the `lang` of `report.json`.
- The chapter plan is the brief; the shots are yours. Take the shot per block from `TECHNIQUES.md` and go beyond it where the report's own structure suggests a better picture: a hook, an "aha" beat, a payoff. Only the chrome (header), the title/chapter/end cards and the caption lane are fixed.

Done when `python3 <skill-dir>/narrate.py <id>.script.md --provider none` parses the script without error.

## Brand

1. Copy the module next to the script: `cp <skill-dir>/brand.py <stem>.media/brand.py`. The media folder stays self-contained.
2. Precedence, first hit wins: `REPORT_BRAND` (a path) → the script's `brand:` path (`narrate.py` reads it for the voice only; render with `REPORT_BRAND=<path>` to apply it to the scenes) → `<stem>.brand.json` beside `<stem>.media/` → `brand.json` beside it → the defaults.
3. Defaults: the GitHub dark look with the report's badge colour names, so an entity keeps its report colour in the video. Write a brand file only when the user gives brand facts; ask for none.
4. `brand.json`: a found file is merged over the defaults (`colors` and `voice` key by key).

```
{ "name": "", "tagline": "", "logo": "logo.png",          // logo path relative to the brand file
  "bg": "#0d1117", "fg": "#e6edf3", "muted": "#8b949e", "rule": "#30363d", "accent": "#58a6ff",
  "colors": { "purple": "#a371f7", "blue": "#58a6ff", "green": "#3fb950", "gray": "#8b949e", "orange": "#db6d28",
              "pink": "#db61a2", "teal": "#39c5cf", "yellow": "#d29922", "red": "#f85149", "navy": "#388bfd",
              "brown": "#bd561d", "ink": "#e6edf3" },
  "font": null,                                           // null = first installed of FONT_CHAIN
  "voice": { "provider": "auto", "voice_id": null, "model_id": "eleven_multilingual_v2", "say_voice": null } }
```

`FONT_CHAIN` = JetBrains Mono, Menlo, DejaVu Sans Mono, Monospace. `name` empty → the header shows the video title.

## Scenes

Write `<stem>.media/<id>.py` with `from brand import *` and one `class Ch<n><Name>(Explainer)` per chapter. Set `CHAPTER` (the heading number), `CHAPTERS` (the total) and `TITLE` (the chapter title); the class name is the script's `scene=`.

- `construct` starts with `self.title_card(title, sub, meta)` (chapter 1) or `self.chapter_card()`, then one `self.beat(n, *anims, say="…")` per script beat in order, then `self.clear_stage()` or, in the last chapter, `self.end_card([≤ 3 takeaways])`.
- The beat numbers match the script and `say` is the script's narration verbatim: `narrate.py` and `stitch.py` find the clips by chapter and beat number. Once `narrate.py` ran, `beat()` raises a `ValueError` when `say` differs from the script line in `timestamps.json` (whitespace aside). A beat whose script line has narration but no `say` holds for the clip and leaves the caption lane as it is.
- Build objects with the `brand.py` helpers (`box`, `pipeline`, `pulse`, `edge_label`, `chip`, `counter`/`count_to`, `bars`, `stack`, `dim`, `structural`, `hi`, `ring`). `counter(value, label)` takes the largest value it will show. `beat(run_time=…)` applies to all of the beat's animations; `lag > 0` staggers them.
- All text goes through `self.text` (it fits the frame). At most 6 live elements: `dim` or `clear_stage` the rest.

Done when `<id>.py` holds one scene per script chapter and one `beat` per script beat. `TECHNIQUES.md` (Block → shot) names the shot per report block.

## Narrate

Run in `<stem>.media/` before rendering: the measured clip lengths are the time budget of the beats.

`python3 <skill-dir>/narrate.py <id>.script.md [--provider auto|elevenlabs|say|dir|none] [--voice <id|name>] [--out <dir>] [--force]`

| Provider | What it does |
|---|---|
| `auto` (default; brand `voice.provider` overrides it) | `elevenlabs` when a key is found, else `say` when `/usr/bin/say` exists, else `none` |
| `elevenlabs` | one mp3 per narration line, `<id>.voice/<ch>-<beat>.mp3`; `--voice` = voice id (else brand `voice.voice_id`, else the default voice) |
| `say` | macOS `say`, `<id>.voice/<ch>-<beat>.wav`; voice by `lang` (`de` Anna, `en` Samantha); `--voice` = voice name |
| `dir` | generates nothing; harness TTS branch below |
| `none` | no audio; captions only; durations estimated as words / 2.5 + 0.6 s |

- Harness TTS (omp `tts` device, `read xd://tts` first): for every narration line call the tool with `output_path` `<id>.voice/<chapter>-<beat>.wav` and the line as text, then run `--provider dir`. A missing clip fails with `narrate: dir: missing <path>`.
- The run writes `timestamps.json` beside the script (one entry per narration line: chapter, beat, scene, text, `duration_s`, `file`) and prints `narrate: <n> clips, <provider>, <total> s`.
- A clip is regenerated only when its text changed or the file is missing. After a voice or model change, add `--force`. After editing narration, run `narrate.py` again, then render the touched scenes again.

Done when `narrate:` prints the clip count and `timestamps.json` holds one entry per `>` line.

## Render

Run in `<stem>.media/`, in this order:

1. Draft: `manim -ql -a <id>.py` (every scene).
2. Read one still per chapter: `manim -ql -s <id>.py <Scene>` (or an ffmpeg frame of the draft) against the `TECHNIQUES.md` checklist (chrome, no cut text, ≤ 6 elements, readable caption lane, report colours). Fix and render again.
3. Final: `manim -qm --format=mp4 -a <id>.py`, then `python3 <skill-dir>/stitch.py <id>.script.md --quality m`. `-qh` and `--quality h` only on request. Render and stitch use the same quality. About 3-5 s render per scene at `-qm` per 10 s of video.

`stitch.py [--quality l|m|h] [--poster <chapter>.<beat> | <seconds> | <seconds>s] [--keep]` mixes each chapter's clips at the beat start times, joins the chapters with mp4 chapter markers, writes `<id>.mp4`, `<id>.vtt`, `<id>.jpg` and `<id>.block.json`, then removes `media/` (`--keep` keeps it). The poster defaults to the answer with everything shown (after chapter 1's last beat has settled, before its closing fade). It prints `stitch: <id>.mp4 <s> s, <n> chapters, voice=<yes|no>, captions=<cues>`.

Guard: `stitch: chapter <n> beat <b>: narration ends at <x> s, video is <y> s` means the clip outlasts its scene. Shorten the sentence or give that beat a longer `wait`, then render the scene again.

Done when `stitch:` prints its summary line.

## Block

`stitch.py` prints the block and saves it as `<id>.block.json`:

```
{ "type": "video", "id": "demo", "label": "<script H1>",
  "src": "<stem>.media/demo.mp4", "poster": "<stem>.media/demo.jpg", "track": "<stem>.media/demo.vtt",
  "chapters": [ { "t": 0, "label": "1. Antwort" }, { "t": 21.4, "label": "2. Ablauf" } ],
  "caption": "", "at": "path:line" }
```

- `chapters[].t` is seconds from the start, ascending; `label` is `<n>. <title>`. The build shows them as a button list under the player that seeks it. `track` is the WebVTT file (written only when the scenes had narration lines); the build adds it as the default caption track in the report's `lang`.
- Fill `caption` with one readable sentence that says what the video shows (inline `code`, `[[id]]`, `[@path:line]` are allowed). `at` is optional and adds the evidence table.
- The `id` shares the diagram id space: unique among all diagram ids; the figure anchor is `#f-<id>`.
- `src`, `poster` and `track` resolve next to the output HTML first, else next to `report.json`; the page gets `src` and `poster` rewritten relative to the HTML, and the track inlined into the page as a `data:` URI (browsers block `file://` tracks).
- The build fails with ``video <id>: `src` is required``, with `video <id>: file not found <path>` when `src`, `poster` or `track` exists in neither place, and with `video <id>: chapters[<i>] needs numeric ascending t and a label`.
- A video has no ⤢ zoom and no node hover; the browser's controls cover fullscreen.
- A report with a video is a folder: the HTML and the media folder move together (keep the relative path between them).

## Alone

1. Brief from the user's text → Script → Brand → Scenes → Narrate → Render (all above), in `<stem>.media/`.
2. Stop at the mp4: no HTML. If the user wants a page, write a `report.json` with one `p` and the block from `<id>.block.json` (copy `example.json`) and build: `python3 <skill-dir>/../report-html/build.py report.json <out>.html`.
3. Run Verify. State the path of the mp4 and the chapter list in chat.

The example in `example.media/` holds a finished set: `demo.script.md`, `demo.py`, `brand.py`, `demo.block.json`.

## Under report-html

1. Do Brief to Render with the built `report.json`. Put the media in `<stem>.media/` next to `report.json` (the sibling of `<stem>.json`).
2. Hand the block from `<id>.block.json` back to the orchestrator's section plan. Place it last in the first section (the answer), unless a chosen question asked for the video: then last in that section. The text above states the answer; the video walks through it. Do not move a finding into the video.
3. Size: `small` never offers a video.
4. The orchestrator builds and runs the full checks. Run Verify.

## Verify

- `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -show_chapters <id>.mp4`: h264 (+ aac when narrated), 1280×720, chapter count = script chapter count, chapter titles match `<n>. <title>`.
- `<id>.vtt` cue count (`grep -c -- '-->'`) = narration line count.
- Read the poster and one still per chapter: chrome visible, no cut text, ≤ 6 elements.
- Build from any directory: `python3 <skill-dir>/../report-html/build.py <report>.json /tmp/x.html` prints `lint: 0 findings`; the emitted `src`/`poster` point at existing files relative to `/tmp`; the track is inlined as a `data:text/vtt` URI.
- Built page at 1280 px and 390 px: `scrollWidth == 390`, no console errors; `<video>` `readyState ≥ 1` after `load()`; `video.textTracks[0].cues.length` = the vtt cue count (also from `file://`); a click on the second chapter button sets `currentTime` to its `t` and starts playback.
- Build errors fire on a missing `src`, a missing file, and a `chapters` entry without `t`.
