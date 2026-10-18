#!/usr/bin/env python3
"""narrate.py: validate a report-video script and produce its voice clips plus timestamps.json.

    python3 narrate.py <id>.script.md [--provider auto|elevenlabs|say|dir|none]
                       [--voice ID_OR_NAME] [--out DIR] [--force]

Run in the media folder before rendering. Per narration line (a `>` line under a beat)
it makes one clip `<out>/<chapter>-<beat>.<ext>` (default out: `<id>.voice` beside the
script), measures it with ffprobe and writes `timestamps.json` next to the script:

    {"title": "<the script's H1>",
     "provider": "elevenlabs",
     "beats": [{"chapter": 1, "beat": 2, "scene": "Ch1Answer", "text": "...",
                "duration_s": 3.42, "file": "demo.voice/1-2.mp3"}]}

Silent beats are omitted; `file` is null for provider `none`. The scenes read the
durations as the time budget of each beat. `stitch.py` imports `parse_script`.

Providers
  auto        elevenlabs when a key is found, else macOS `say`, else none
  elevenlabs  ELEVENLABS_API_KEY from the environment, a `.env` from cwd upward, or ~/.env
  say         macOS `say`, converted to 44.1 kHz wav
  dir         generates nothing; expects <out>/<ch>-<beat>.(wav|mp3) written by a harness TTS
  none        no audio; durations estimated as words / 2.5 + 0.6 s

A clip is regenerated only when <out>/<ch>-<beat>.txt (the text it was made from)
differs from the narration or the audio file is missing; --force regenerates all.
A changed voice or model is not detected: use --force then.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
SAY_BIN = "/usr/bin/say"
SAY_VOICES = {"de": "Anna", "en": "Samantha"}
PROVIDERS = ("auto", "elevenlabs", "say", "dir", "none")
MAX_WORDS = 30
WORDS_PER_SECOND = 2.5
CLIP_RE = re.compile(r"^\d+-\d+\.(wav|mp3|aiff|txt)$")


class NarrateError(Exception):
    """Raised with a complete `narrate: ...` message; the CLI prints it and exits 1."""


def fail(msg):
    return NarrateError(f"narrate: {msg}")


# --------------------------------------------------------------------------- parser

_CHAPTER_RE = re.compile(r"^##\s+(\d+)\.\s+(.*?)\s*(\{[^{}]*\})?\s*$")
_BEAT_RE = re.compile(r"^(\d+)\.\s+(.*\S)\s*$")
_KEY_RE = re.compile(r"^(Goal|Carry|Concepts|Shots):\s*(.*?)\s*$")
_META_RE = re.compile(r"^-\s+([A-Za-z][\w-]*):\s*(.*?)\s*$")


def estimate_s(text):
    """Duration estimate used when no audio exists: words / 2.5 + 0.6 seconds."""
    return len(text.split()) / WORDS_PER_SECOND + 0.6


def parse_script(path):
    """Parse a `<id>.script.md` and return a plain dict. No file is written.

    Grammar: `# <title>`, `- key: value` header lines, then chapters `## <n>. <Title> {scene=<Class> section=<id>}`
    with the fields Goal/Carry/Concepts/Shots (a field may continue on indented lines) and numbered
    beats `<n>. <visual> | <technique>`. A beat has at most one `>` narration line (one sentence,
    hard limit 30 words); beats and narration never continue on further lines.

    Raises NarrateError (message `narrate: <path>:<line>: <reason>`) on any grammar error.

    Return shape::

        {"path": str,                      # the path as given
         "title": str,                     # the H1
         "title_line": int,
         "meta": {"report": "demo.json", "lang": "de", "brand": "default", "arc": ..., "target": ...},
                                           # keys lower-cased, values as written; only keys present
         "lang": str | None,               # meta["lang"]
         "brand": str | None,              # meta["brand"]
         "chapters": [
           {"number": 1, "title": "Antwort", "line": 12,
            "attrs": {"scene": "Ch1Answer", "section": "answer"},
            "scene": "Ch1Answer", "section": "answer" | None,
            "goal": str | None, "carry": str | None, "concepts": str | None, "shots": str | None,
            "beats": [
              {"number": 1, "line": 18,
               "visual": "what appears", "technique": "helper" | None,
               "narration": "one sentence" | None,     # None = silent beat
               "narration_line": int | None}]}]}
    """
    path = str(path)
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise fail(f"{path}: {e.strerror or e}")

    def err(n, reason):
        return fail(f"{path}:{n}: {reason}")

    title = None
    title_line = 0
    meta = {}
    chapters = []
    ch = None
    beat = None
    last = None  # (dict, key) that an indented continuation line extends

    for n, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        s = line.strip()

        if s.startswith("# ") or s == "#":
            if title is not None:
                raise err(n, "second H1; the script has one `# <title>`")
            title = s[1:].strip()
            if not title:
                raise err(n, "empty video title")
            title_line = n
            last = None
            continue
        if title is None:
            raise err(n, "expected `# <Video title>` first")

        if s.startswith("##"):
            m = _CHAPTER_RE.match(s)
            if not m:
                raise err(n, "chapter heading must be `## <n>. <Title> {scene=<Class> section=<id>}`")
            num = int(m.group(1))
            if num != len(chapters) + 1:
                raise err(n, f"chapter {num} out of sequence (expected {len(chapters) + 1})")
            attrs = {}
            for tok in (m.group(3) or "")[1:-1].split():
                k, eq, v = tok.partition("=")
                if not eq or not k or not v:
                    raise err(n, f"attribute `{tok}` must be key=value")
                attrs[k] = v
            if "scene" not in attrs:
                raise err(n, f"chapter {num} has no scene= attribute")
            if any(c["scene"] == attrs["scene"] for c in chapters):
                raise err(n, f"scene {attrs['scene']} is used by two chapters")
            if not m.group(2):
                raise err(n, f"chapter {num} has no title")
            if ch is not None and not ch["beats"]:
                raise err(ch["line"], f"chapter {ch['number']} has no beats")
            ch = {"number": num, "title": m.group(2), "line": n, "attrs": attrs,
                  "scene": attrs["scene"], "section": attrs.get("section"),
                  "goal": None, "carry": None, "concepts": None, "shots": None, "beats": []}
            chapters.append(ch)
            beat = None
            last = None
            continue

        if ch is None:
            m = _META_RE.match(s)
            if not m:
                raise err(n, "expected `- key: value` header lines or a `## 1. ...` chapter")
            meta[m.group(1).lower()] = m.group(2)
            continue

        if s.startswith(">"):
            if beat is None:
                raise err(n, "narration line before the first beat")
            if beat["narration"] is not None:
                raise err(n, f"beat {beat['number']} has more than one narration line")
            text = s[1:].strip()
            if not text:
                raise err(n, "empty narration line")
            words = len(text.split())
            if words > MAX_WORDS:
                raise err(n, f"narration has {words} words (hard limit {MAX_WORDS}, style rule 20)")
            beat["narration"] = text
            beat["narration_line"] = n
            last = None
            continue

        if raw[:1] in (" ", "\t") and last is not None and not _BEAT_RE.match(s):
            d, k = last
            d[k] = (d[k] + " " + s) if d[k] else s
            continue

        m = _KEY_RE.match(s)
        if m:
            ch[m.group(1).lower()] = m.group(2)
            last = (ch, m.group(1).lower())
            beat = None
            continue

        m = _BEAT_RE.match(s)
        if m:
            num = int(m.group(1))
            if num != len(ch["beats"]) + 1:
                raise err(n, f"beat {num} out of sequence")
            visual, sep, technique = m.group(2).partition(" | ")
            beat = {"number": num, "line": n, "visual": visual.strip(),
                    "technique": technique.strip() if sep else None,
                    "narration": None, "narration_line": None}
            ch["beats"].append(beat)
            last = None
            continue

        raise err(n, "unrecognised line (expected Goal/Carry/Concepts/Shots, a numbered beat or a `>` narration line)")

    if title is None:
        raise fail(f"{path}:1: no `# <Video title>`")
    if not chapters:
        raise fail(f"{path}:{title_line}: no `## 1. <Title> {{scene=...}}` chapter")
    if not ch["beats"]:
        raise fail(f"{path}:{ch['line']}: chapter {ch['number']} has no beats")
    return {"path": path, "title": title, "title_line": title_line, "meta": meta,
            "lang": meta.get("lang"), "brand": meta.get("brand"), "chapters": chapters}


# --------------------------------------------------------------------------- brand + key

def script_id(script_path):
    name = Path(script_path).name
    return name[: -len(".script.md")] if name.endswith(".script.md") else Path(script_path).stem


def load_brand_voice(script_path, brand_ref):
    """The `voice` dict of the brand JSON. Lookup: REPORT_BRAND, the script `brand:` path (unless
    `default`), `<media stem>.brand.json` and `brand.json` beside the media folder, else {}."""
    media = Path(script_path).resolve().parent
    candidates = []
    if os.environ.get("REPORT_BRAND"):
        candidates.append(Path(os.environ["REPORT_BRAND"]).expanduser())
    if brand_ref and brand_ref.lower() != "default":
        ref = Path(brand_ref).expanduser()
        p = ref if ref.is_absolute() else media / ref
        if not p.is_file():
            raise fail(f"{script_path}: brand file {brand_ref} not found")
        candidates.append(p)
    stem = media.name[: -len(".media")] if media.name.endswith(".media") else media.name
    candidates.append(media.parent / f"{stem}.brand.json")
    candidates.append(media.parent / "brand.json")
    for p in candidates:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise fail(f"{p}: cannot read brand file: {e}")
            voice = data.get("voice") if isinstance(data, dict) else None
            return voice if isinstance(voice, dict) else {}
    return {}


def _env_value(path, key):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        k, eq, v = line.partition("=")
        if not eq or k.strip() != key:
            continue
        v = v.strip()
        if v[:1] in ("'", '"'):
            end = v.find(v[0], 1)
            v = v[1:end] if end > 0 else v[1:]
        else:
            v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
        if v:
            return v
    return None


def find_key(name="ELEVENLABS_API_KEY"):
    """Environment, then `.env` from cwd upward to `/` (first hit wins), then ~/.env."""
    if os.environ.get(name):
        return os.environ[name]
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        v = _env_value(d / ".env", name)
        if v:
            return v
    return _env_value(Path.home() / ".env", name)


# --------------------------------------------------------------------------- providers

def probe_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True)
    except FileNotFoundError:
        raise fail("ffprobe not found (install ffmpeg)")
    try:
        d = float(r.stdout.strip())
    except ValueError:
        raise fail(f"ffprobe could not measure {path}: {r.stderr.strip()[:200]}")
    if d <= 0:
        raise fail(f"{path} has no audio")
    return d


def tts_elevenlabs(text, dest, key, voice_id, model_id, prev, nxt):
    body = {"text": text, "model_id": model_id}
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    url = ("https://api.elevenlabs.io/v1/text-to-speech/" + urllib.parse.quote(voice_id, safe="")
           + "?output_format=mp3_44100_128")
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg",
        "User-Agent": "report-video-narrate/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            status, data = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        raise fail(f"elevenlabs {e.code}: {e.read(200).decode('utf-8', 'replace')}")
    except (urllib.error.URLError, OSError) as e:
        raise fail(f"elevenlabs: {getattr(e, 'reason', e)}")
    if status != 200 or not data:
        raise fail(f"elevenlabs {status}: {data[:200].decode('utf-8', 'replace')}")
    dest.write_bytes(data)


def tts_say(text, dest, voice):
    aiff = dest.with_suffix(".aiff")
    cmd = [SAY_BIN] + (["-v", voice] if voice else []) + ["-o", str(aiff), "-f", "-"]
    r = subprocess.run(cmd, input=text, capture_output=True, text=True)
    if r.returncode != 0:
        aiff.unlink(missing_ok=True)
        raise fail(f"say failed: {r.stderr.strip()[:200]}")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "44100", str(dest)],
                       capture_output=True, text=True)
    aiff.unlink(missing_ok=True)
    if r.returncode != 0:
        dest.unlink(missing_ok=True)
        raise fail(f"ffmpeg failed on {aiff.name}: {r.stderr.strip()[:200]}")


def choose_provider(requested, key):
    if requested != "auto":
        return requested
    if key:
        return "elevenlabs"
    if Path(SAY_BIN).exists():
        return "say"
    print("narrate: no TTS provider, captions only")
    return "none"


# --------------------------------------------------------------------------- main

def run(args):
    script = Path(args.script)
    parsed = parse_script(script)
    base = script.resolve().parent
    out = Path(args.out) if args.out else script.resolve().parent / f"{script_id(script)}.voice"

    voice_cfg = load_brand_voice(script, parsed["brand"])
    requested = args.provider or voice_cfg.get("provider") or "auto"
    if requested not in PROVIDERS:
        raise fail(f"unknown provider {requested!r} (auto|elevenlabs|say|dir|none)")

    key = find_key() if requested in ("auto", "elevenlabs") else None
    provider = choose_provider(requested, key)
    if provider == "elevenlabs" and not key:
        raise fail("elevenlabs: no ELEVENLABS_API_KEY in the environment, a .env from cwd upward or ~/.env")
    if provider == "say" and not Path(SAY_BIN).exists():
        raise fail(f"say: {SAY_BIN} not found (macOS only)")

    items = [(c, b) for c in parsed["chapters"] for b in c["beats"] if b["narration"]]
    exts = {"elevenlabs": ("mp3", "txt"), "say": ("wav", "txt"), "dir": ("wav", "mp3", "txt")}.get(provider)
    ext = {"elevenlabs": "mp3", "say": "wav"}.get(provider)
    clip = lambda c, b, e: out / f"{c['number']}-{b['number']}.{e}"

    def prune():
        """Remove clips of beats no longer in the script and clips of the other extension."""
        keep = {clip(c, b, e).name for c, b in items for e in exts}
        for p in out.iterdir():
            if CLIP_RE.match(p.name) and p.name not in keep:
                p.unlink()

    if provider == "dir":
        files = []
        for c, b in items:
            found = [p for p in (clip(c, b, "wav"), clip(c, b, "mp3")) if p.is_file()]
            if not found:
                raise fail(f"dir: missing {clip(c, b, 'wav')}")
            files.append(max(found, key=lambda p: p.stat().st_mtime))
        prune()
    else:
        files = []
        if ext:
            out.mkdir(parents=True, exist_ok=True)
            say_voice = args.voice or voice_cfg.get("say_voice")
            if not say_voice:
                say_voice = SAY_VOICES.get((parsed["lang"] or "").split("-")[0].lower())
            voice_id = args.voice or voice_cfg.get("voice_id") or DEFAULT_VOICE_ID
            model_id = voice_cfg.get("model_id") or DEFAULT_MODEL_ID
            for i, (c, b) in enumerate(items):
                audio, txt = clip(c, b, ext), clip(c, b, "txt")
                text = b["narration"]
                cached = (not args.force and audio.is_file() and txt.is_file()
                          and txt.read_text(encoding="utf-8") == text)
                if not cached:
                    txt.unlink(missing_ok=True)
                    if provider == "elevenlabs":
                        prev = items[i - 1][1]["narration"] if i > 0 else None
                        nxt = items[i + 1][1]["narration"] if i + 1 < len(items) else None
                        tts_elevenlabs(text, audio, key, voice_id, model_id, prev, nxt)
                    else:
                        tts_say(text, audio, say_voice)
                    txt.write_text(text, encoding="utf-8")
                files.append(audio)
            prune()

    beats, total = [], 0.0
    for i, (c, b) in enumerate(items):
        text = b["narration"]
        d = probe_duration(files[i]) if files else estimate_s(text)
        d = math.ceil(d * 100 - 1e-9) / 100
        total += d
        beats.append({"chapter": c["number"], "beat": b["number"], "scene": c["scene"], "text": text,
                      "duration_s": d,
                      "file": Path(os.path.relpath(files[i], base)).as_posix() if files else None})
    (base / "timestamps.json").write_text(
        json.dumps({"title": parsed["title"], "provider": provider, "beats": beats}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"narrate: {len(beats)} clips, {provider}, {total:.1f} s")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="narrate.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("script", help="<id>.script.md")
    ap.add_argument("--provider", choices=PROVIDERS, default=None,
                    help="default: brand voice.provider, else auto")
    ap.add_argument("--voice", help="ElevenLabs voice id, or the `say` voice name")
    ap.add_argument("--out", help="clip folder (default: <id>.voice beside the script)")
    ap.add_argument("--force", action="store_true", help="regenerate every clip")
    args = ap.parse_args(argv)
    try:
        run(args)
    except NarrateError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
