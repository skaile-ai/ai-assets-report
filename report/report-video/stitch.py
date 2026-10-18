#!/usr/bin/env python3
"""stitch.py: join the rendered chapter scenes of a report-video into one mp4 with
chapter markers, voice, captions, a poster and the `video` block for report.json.

    python3 stitch.py <id>.script.md [--quality l|m|h] [--poster C.B | SECONDS | SECONDSs] [--keep]

Run in the media folder (the one manim rendered into) after every chapter scene of
`<id>.py` is rendered with the same quality flag (-ql / -qm / -qh).

Inputs (the media folder is the current directory)
  <id>.script.md                           the script; the chapter list and titles come from it
  media/videos/<id>/<res>/<Scene>.mp4      one per chapter; res = 480p15 (l), 720p30 (m), 1080p60 (h)
  media/videos/<id>/<res>/<Scene>.srt      subcaptions of the scene (optional)
  beats.json                               written by brand.Explainer: t0 of every beat per scene
  timestamps.json + <id>.voice/<c>-<b>.*   written by narrate.py (optional; none = silent video)

Outputs (current directory)
  <id>.mp4          h264 video, AAC audio, mp4 chapter markers "<n>. <title>", faststart
  <id>.vtt          WebVTT captions, merged over all chapters (only when a scene wrote an .srt)
  <id>.jpg          poster frame
  <id>.block.json   the `video` block, also printed; paths are relative to the media folder's parent

Voice: per chapter, every narration clip is delayed to the beat's t0 and mixed into one
44.1 kHz stereo AAC track; a chapter without clips gets silence of the same format.
A clip that ends after its chapter video fails the run.

--poster picks the poster frame. Default: the midpoint between the start of the last beat of
chapter 1 and 0.8 s before chapter 1 ends (where clear_stage starts to fade), never earlier
than one second after that beat starts: the answer with everything shown and settled.
`C.B` (an existing chapter and beat) means one second after that beat starts; a plain number
or `<number>s` is seconds from the start of the video (use the `s` form when the number
could read as `C.B`).

`media/` is removed after a successful run unless --keep is given; intermediates live in
`media/stitch/`.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrate import NarrateError, parse_script, probe_duration, script_id  # noqa: E402

RESOLUTIONS = {"l": "480p15", "m": "720p30", "h": "1080p60"}
SAMPLE_RATE = 44100
POSTER_OFFSET_S = 1.0
FADE_OUT_S = 0.8  # clear_stage: 0.5 s fade + 0.3 s wait at the end of a chapter
_SRT_TIME = r"(\d+):(\d\d):(\d\d)[,.](\d{3})"
_SRT_CUE_RE = re.compile(rf"{_SRT_TIME}\s*-->\s*{_SRT_TIME}")


class StitchError(Exception):
    """Raised with a complete `stitch: ...` message; the CLI prints it and exits 1."""


def fail(msg):
    return StitchError(f"stitch: {msg}")


# --------------------------------------------------------------------------- ffmpeg

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        tail = "\n".join(p.stderr.strip().splitlines()[-12:])
        raise fail(f"{cmd[0]} failed ({p.returncode}): {' '.join(cmd[:3])} ...\n{tail}")
    return p.stdout


def ffmpeg(*args):
    run(["ffmpeg", "-v", "error", "-y", *map(str, args)])


def video_length(path):
    """Duration in seconds, via narrate.probe_duration; its error is re-raised as a `stitch:` one."""
    try:
        return probe_duration(path)
    except NarrateError as e:
        raise fail(str(e).removeprefix("narrate: "))


def read_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise fail(f"{what} {path}: {e.strerror or e}")
    except ValueError as e:
        raise fail(f"{what} {path}: invalid JSON ({e})")


# --------------------------------------------------------------------------- steps

def build_chapter(ch, scene_mp4, clips, t0s, out):
    """Write `out`: the scene video with its voice track (or silence). Returns the voiced flag."""
    video_len = video_length(scene_mp4)
    n = ch["number"]
    if not clips:
        ffmpeg("-i", scene_mp4, "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo",
               "-map", "0:v:0", "-map", "1:a:0", "-shortest",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", out)
        return False
    inputs, chains, labels = [], [], []
    for i, clip in enumerate(clips, start=1):
        beat = clip["beat"]
        t0 = t0s[beat]
        end = t0 + clip["duration_s"]
        if end > video_len:
            raise fail(f"chapter {n} beat {beat}: narration ends at {end:.2f} s, video is "
                       f"{video_len:.2f} s (raise the beat's wait or split the line)")
        inputs += ["-i", clip["path"]]
        chains.append(f"[{i}:a]aformat=sample_rates={SAMPLE_RATE}:channel_layouts=stereo,"
                      f"adelay={int(round(t0 * 1000))}:all=1[a{i}]")
        labels.append(f"[a{i}]")
    chains.append(f"{''.join(labels)}amix=inputs={len(clips)}:normalize=0:duration=longest[m]")
    chains.append("[m]apad[a]")
    ffmpeg("-i", scene_mp4, *inputs, "-filter_complex", ";".join(chains),
           "-map", "0:v:0", "-map", "[a]", "-shortest",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", out)
    return True


def srt_cues(path):
    """Yield (start_s, end_s, text) from an .srt file."""
    text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.split("\n")
        for i, line in enumerate(lines):
            m = _SRT_CUE_RE.search(line)
            if m:
                g = [int(x) for x in m.groups()]
                start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
                end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
                body = "\n".join(lines[i + 1:]).strip()
                if body:
                    yield start, end, body
                break


def vtt_time(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def ffmeta_escape(s):
    return re.sub(r"([=;#\\\n])", r"\\\1", s)


def parse_poster(arg, script, starts, beats_by_scene):
    """Return absolute seconds for --poster, or None for the default."""
    if arg is None:
        return None
    m = re.fullmatch(r"(\d+)\.(\d+)", arg)
    if m:
        c, b = int(m.group(1)), int(m.group(2))
        if 1 <= c <= len(script["chapters"]):
            t0 = beats_by_scene.get(script["chapters"][c - 1]["scene"], {}).get(b)
            if t0 is not None:
                return starts[c - 1] + t0 + POSTER_OFFSET_S
    m = re.fullmatch(r"(\d+(?:\.\d+)?)s?", arg)
    if m:
        return float(m.group(1))
    raise fail(f"--poster {arg}: expected <chapter>.<beat> of a rendered beat, or seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stitch.py", description="Join rendered report-video chapters.")
    ap.add_argument("script", help="<id>.script.md")
    ap.add_argument("--quality", choices=sorted(RESOLUTIONS), default="m")
    ap.add_argument("--poster", help="<chapter>.<beat> or seconds (default: midpoint between chapter 1's last beat and 0.8 s before its end, at least 1 s after the beat)")
    ap.add_argument("--keep", action="store_true", help="keep media/ after stitching")
    args = ap.parse_args(argv)

    script_path = Path(args.script).resolve()
    script = parse_script(script_path)
    sid = script_id(script_path)
    cwd = Path.cwd()
    media = cwd / "media"
    work = media / "stitch"
    res = RESOLUTIONS[args.quality]
    chapters = script["chapters"]

    # 1. scene files
    scenes = []
    for ch in chapters:
        scene = ch["scene"]
        mp4 = media / "videos" / sid / res / f"{scene}.mp4"
        if not mp4.is_file():
            raise fail(f"chapter {ch['number']} ({scene}): {mp4.relative_to(cwd)} missing")
        scenes.append(mp4)

    beats_path = cwd / "beats.json"
    beats_by_scene = {}
    if beats_path.is_file():
        for entry in read_json(beats_path, "beats"):
            beats_by_scene[entry["scene"]] = {b["beat"]: b["t0"] for b in entry["beats"]}

    clips_by_chapter = {}
    ts_path = script_path.parent / "timestamps.json"
    if ts_path.is_file():
        for entry in read_json(ts_path, "timestamps").get("beats", []):
            if not entry.get("file"):
                continue
            path = script_path.parent / entry["file"]
            if not path.is_file():
                raise fail(f"chapter {entry['chapter']} beat {entry['beat']}: {entry['file']} missing (run narrate.py)")
            clips_by_chapter.setdefault(entry["chapter"], []).append(
                {"beat": entry["beat"], "duration_s": float(entry["duration_s"]), "path": str(path)})

    # 2. per-chapter audio
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    chapter_files, voiced = [], False
    for ch, mp4 in zip(chapters, scenes):
        n = ch["number"]
        clips = sorted(clips_by_chapter.get(n, []), key=lambda c: c["beat"])
        t0s = beats_by_scene.get(ch["scene"])
        if clips:
            if t0s is None:
                raise fail(f"chapter {n} ({ch['scene']}): no entry in beats.json (render the scene again)")
            for clip in clips:
                if clip["beat"] not in t0s:
                    raise fail(f"chapter {n} ({ch['scene']}) beat {clip['beat']}: not in beats.json "
                               f"(the scene was not re-rendered after the script changed)")
        out = work / f"{n}.mp4"
        voiced |= build_chapter(ch, mp4, clips, t0s, out)
        chapter_files.append(out)

    # 3. concat
    durations = [video_length(f) for f in chapter_files]
    starts = [sum(durations[:i]) for i in range(len(durations))]
    (work / "concat.txt").write_text("".join(f"file '{f.name}'\n" for f in chapter_files), encoding="utf-8")
    joined = work / "joined.mp4"
    ffmpeg("-f", "concat", "-safe", 0, "-i", work / "concat.txt", "-c", "copy", joined)

    # 4. chapter markers
    meta = [";FFMETADATA1", f"title={ffmeta_escape(script['title'])}"]
    for ch, start, dur in zip(chapters, starts, durations):
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(round(start * 1000))}",
                 f"END={int(round((start + dur) * 1000))}",
                 f"title={ffmeta_escape(str(ch['number']) + '. ' + ch['title'])}"]
    (work / "meta.txt").write_text("\n".join(meta) + "\n", encoding="utf-8")
    final = cwd / f"{sid}.mp4"
    ffmpeg("-i", joined, "-i", work / "meta.txt", "-map_metadata", 1, "-codec", "copy",
           "-movflags", "+faststart", final)
    total = video_length(final)

    # 5. captions
    cues = []
    for mp4, start in zip(scenes, starts):
        srt = mp4.with_suffix(".srt")
        if srt.is_file():
            cues += [(s + start, e + start, text) for s, e, text in srt_cues(srt)]
    vtt = cwd / f"{sid}.vtt"
    if cues:
        body = "\n\n".join(f"{vtt_time(s)} --> {vtt_time(e)}\n{text}" for s, e, text in cues)
        vtt.write_text(f"WEBVTT\n\n{body}\n", encoding="utf-8")
    elif vtt.exists():
        vtt.unlink()

    # 6. poster
    poster_t = parse_poster(args.poster, script, starts, beats_by_scene)
    if poster_t is None:
        first = beats_by_scene.get(chapters[0]["scene"], {})
        if first:
            ch1_end = starts[0] + durations[0]
            last = starts[0] + max(first.values())
            poster_t = max((last + ch1_end - FADE_OUT_S) / 2, last + POSTER_OFFSET_S)
            poster_t = min(poster_t, ch1_end - 0.1)
        else:
            poster_t = max(0.0, durations[0] - 0.5)
    poster_t = max(0.0, min(poster_t, total - 0.1))
    poster = cwd / f"{sid}.jpg"
    ffmpeg("-ss", f"{poster_t:.3f}", "-i", final, "-frames:v", 1, "-q:v", 3, poster)

    # 7. block
    prefix = cwd.name
    block = {"type": "video", "id": sid, "label": script["title"],
             "src": f"{prefix}/{sid}.mp4", "poster": f"{prefix}/{sid}.jpg"}
    if cues:
        block["track"] = f"{prefix}/{sid}.vtt"
    block["chapters"] = [{"t": round(start, 3), "label": f"{ch['number']}. {ch['title']}"}
                         for ch, start in zip(chapters, starts)]
    block["chapters"][0]["t"] = 0
    block["caption"] = ""
    text = json.dumps(block, ensure_ascii=False, indent=2) + "\n"
    (cwd / f"{sid}.block.json").write_text(text, encoding="utf-8")
    print(text, end="")

    # 8. cleanup
    if not args.keep:
        shutil.rmtree(media)
    print(f"stitch: {sid}.mp4 {total:.1f} s, {len(chapters)} chapters, "
          f"voice={'yes' if voiced else 'no'}, captions={len(cues)}")


if __name__ == "__main__":
    try:
        main()
    except (StitchError, NarrateError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)
