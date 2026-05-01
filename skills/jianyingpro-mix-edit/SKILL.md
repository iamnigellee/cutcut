---
name: jianyingpro-mix-edit
description: Generate a 剪映 (JianYing Pro) draft on macOS that stitches video clips, synthesizes a TTS voiceover via edge-tts, and auto-places sound effects. Use for 剪映 / 混剪 / 配音 / 配音效 / TTS / 文案稿剪片 / 音效 / sfx / voiceover / 拼视频 / multi-clip mix on macOS.
metadata:
  openclaw:
    emoji: 🎬
    requires:
      anyBins: [ffmpeg]
---

# JianYing Pro 多素材混剪 Skill (macOS)

This skill generates 剪映专业版 drafts on macOS for two related workflows:

- **Mode A — Clips + Voiceover + SFX**: user has video clips ready, gives a narration script, the skill produces a TTS voiceover, places sound effects on the beats, and lays everything into a draft.
- **Mode B — Script-driven cut**: user has a finished narration script and a pile of raw clips, no editing plan yet. The skill TTS's the script, returns sentence-level timing, and helps decide which clip plays during which sentence + where SFX go. Then builds the draft.

In both modes the user finishes inside 剪映: transitions, captions, color, BGM, export. The skill **does not** handle BGM — 剪映 has a rich built-in music library and that's the right tool for the job.

## When to use

Invoke this skill when the user wants to:
- Stitch N video clips with TTS-generated narration over the top.
- Auto-place sound effects (whoosh / ding / boom / pop) at scene transitions, punchlines, emphasis points.
- Convert a finished script into a roughed-out draft that's 80% done before opening 剪映.

If the user wants headless export (no 剪映 GUI), this skill is wrong — fall back to ffmpeg.

## Prerequisites — verify before running

```bash
test "$(uname)" = "Darwin"                         || echo "ABORT: macOS only"
test -d "/Applications/JianyingPro.app"            || echo "MISSING: 剪映专业版"
command -v ffmpeg ffprobe                          || echo "MISSING: brew install ffmpeg"
python3 --version
python3 -c "import pyJianYingDraft, edge_tts" 2>/dev/null \
  || python3 -m pip install --user -r "$SKILL_DIR/scripts/requirements.txt"
```

`$SKILL_DIR` is the directory containing this `SKILL.md`. If the SFX library hasn't been generated yet, the build script regenerates it on demand — no separate setup step.

---

## Mode A — Clips + Voiceover + SFX

The user has clips and a narration script.

### Step 1 — Gather inputs

Ask if anything is unclear:
- Ordered list of clip absolute paths.
- Path to a `.txt` file with the narration script, **or** the script inline.
- Voice preference: a natural-language description ("沉稳纪录片"/"轻快 vlog"/"young female") or a specific edge-tts voice ID. See `references/tts_styles.md`.
- Canvas size + FPS (default 1920×1080 @ 30).
- SFX intensity preference: "minimal" / "balanced" / "punchy" (controls SFX density: ~1 per 10s / ~1 per 5s / ~1 per 3s).

### Step 2 — TTS the script

```bash
python3 "$SKILL_DIR/scripts/tts.py" /tmp/script.txt /tmp/vo_out --voice zh-CN-YunjianNeural
```

Outputs:
- `/tmp/vo_out/vo.mp3` — the audio.
- `/tmp/vo_out/vo.srt` — word-level subtitle timings.
- `/tmp/vo_out/vo.json` — sentence-level timings, the input you reason from.

Read `vo.json`. Each sentence has `text`, `start_us`, `end_us`, `duration_us`.

### Step 3 — Plan the SFX placements (your judgement)

Read the `sentences` array. For each sentence decide whether a beat warrants an SFX. **Cap density** to user-chosen intensity (default ~1 per 5s). Pick categories from `assets/sfx_manifest.json`:

| Beat type | Suggested category |
|---|---|
| Major scene change between sentences | `transition.whoosh.slow` or `transition.whoosh.fast` |
| Subtle continuation, soft transition | `transition.swoosh` |
| Punchline, reveal, joke landing | `emphasis.ding.bright` or `reaction.boing` |
| Soft emphasis, gentle highlight | `emphasis.ding.soft` |
| Short punctuation between thoughts | `emphasis.pop` or `meta.click.tick` |
| Heavy reveal, dramatic moment | `impact.boom` or `impact.thud` |
| Topic / chapter change | `meta.bell.chapter` or `meta.page.flip` |
| Photo / freeze-frame | `meta.camera.shutter` |

Default placement timing: **at the start of the next sentence**, not on top of speech. Tiny ticks/clicks can land mid-sentence at commas. Whooshes belong at sentence boundaries.

If the user wants a real laugh track / applause / ambient rain — those are not in the synthesized library. Tell them to pick from 剪映's built-in audio library after the draft opens; flag the timestamp in your handoff.

### Step 4 — Write the spec and build

```json
{
  "draft_name": "vlog_20260427",
  "canvas": {"width": 1920, "height": 1080},
  "fps": 30,
  "clips": [
    {"path": "/Users/me/Videos/a.mp4"},
    {"path": "/Users/me/Videos/b.mp4", "trim_start_s": 2.0, "trim_end_s": 8.5}
  ],
  "voiceover": {"path": "/tmp/vo_out/vo.mp3", "volume": 1.0},
  "sfx": [
    {"category": "transition.whoosh.fast", "at_s": 1.84, "volume": 0.5},
    {"category": "emphasis.ding.bright",   "at_s": 5.20, "volume": 0.55}
  ]
}
```

```bash
python3 "$SKILL_DIR/scripts/build_draft.py" /tmp/mix_spec.json
```

`build_draft.py` auto-runs `generate_sfx.py` if any referenced SFX file is missing. ffmpeg synthesizes them on the fly (~2s for the full library).

### Step 5 — Open 剪映

```bash
bash "$SKILL_DIR/scripts/open_jianying.sh" "<draft_name>"
```

Restarts 剪映 (it caches the draft list). Warn the user any unsaved 剪映 work will be lost.

### Step 6 — Hand off

Tell the user:
- Draft name + path.
- Total duration.
- Where you placed each SFX and why (1 line each).
- That BGM should be added inside 剪映 (音频 → 音乐).
- Any "real" SFX you flagged (applause/laughter) that they should drag in from 剪映's audio library.

---

## Mode B — Script-driven cut

User has narration text and a clip folder, no editing plan yet.

### Step 1 — Gather inputs

- Path to script `.txt`.
- Path to folder containing raw clips (or an explicit list).
- Voice preference.
- Canvas + FPS.
- SFX intensity preference.

### Step 2 — TTS first

Same `tts.py` invocation as Mode A. Get `vo.json` with sentence-level timings.

### Step 3 — Probe and list the clips

```bash
for f in /path/to/clips/*; do
  python3 "$SKILL_DIR/scripts/probe_media.py" "$f"
done
```

Build a clip table: filename, duration, kind (video/image), width×height. Read filenames for semantic hints (e.g. `01_morning_commute.mp4` clearly maps to morning-commute sentences).

If filenames are uninformative, ask the user for one-line descriptions per clip. Don't guess randomly — wrong mapping wastes their time more than asking.

### Step 4 — Map sentences to clips

You decide. Output a table back to the user before building, e.g.:

```
sentence 1 (0.0s–2.4s, "今天我们来到深圳湾...")  →  03_skyline_pan.mp4 (full)
sentence 2 (2.4s–5.1s, "天气特别好...")         →  07_blue_sky.mp4 (trim 0–2.7s)
sentence 3 (5.1s–8.3s, "海风迎面吹来...")        →  09_seabreeze.mp4 + 11_waves.mp4
```

Rules of thumb:
- Each clip's effective duration must equal its sentence's duration. Trim if longer; concat multiple clips if shorter.
- For images (still photos), `duration_s` defaults to 3s — adjust to match sentence length.
- Avoid same clip back-to-back unless the user wants it.

User confirms / edits the mapping. Don't proceed without confirmation if you had to guess.

### Step 5 — Plan SFX

Same logic as Mode A Step 3, but you now know the clip boundaries too. Place transition SFX at clip cuts that coincide with sentence breaks (best landing). Place emphasis SFX inside sentences at their punchline.

### Step 6 — Write spec, build, open 剪映

Same as Mode A Steps 4–6.

---

## Voice selection

See `references/tts_styles.md` for the full voice + style table. Quick defaults:

| User intent | Voice | Notes |
|---|---|---|
| 沉稳纪录片 / 体育 / 男声旁白 | `zh-CN-YunjianNeural` | Default. Deep male. |
| 通用女声 | `zh-CN-XiaoxiaoNeural` | Versatile. Supports SSML `mstts:express-as` styles. |
| 年轻男声 / 口语 / vlog | `zh-CN-YunxiNeural` | Casual male. |
| 温柔女声 | `zh-CN-XiaoyiNeural` | Soft female. |

For style modulation (cheerful / sad / news / customerservice / affectionate), pass `--rate +5%` for upbeat or `--rate -10%` for slower delivery. SSML express-as requires you to wrap the script in SSML tags before passing — see the reference.

## What this skill does NOT do

- ❌ Background music (BGM): use 剪映's built-in music library.
- ❌ Real recorded SFX (applause, laughter, ambient rain): use 剪映's audio library; flag the timestamp.
- ❌ Headless export: 剪映 disables third-party draft export on macOS. User exports manually.
- ❌ Captions / subtitle text overlays: only the SRT file is produced; user imports it in 剪映 (字幕 → 导入字幕) or auto-generates inside 剪映.
- ❌ Color grading, transitions, effects: 剪映 GUI.
- ❌ Picture-in-picture, multi-track video composites: out of scope.

## Reference files (load on demand)

- `references/spec_schema.md` — every spec.json field with defaults and validation.
- `references/script_workflow.md` — Mode B detailed walkthrough with example.
- `references/tts_styles.md` — voice IDs, rate/volume controls, SSML for style.
- `references/draft_format.md` — internals of `draft_content.json` for advanced customization.
- `references/troubleshooting.md` — diagnostic flowchart for failures.
- `assets/example_spec.json` — runnable example spec.
- `assets/sfx_manifest.json` — all 13 SFX categories with their ffmpeg recipes.

## Bundled tools

- `scripts/tts.py` — script.txt → vo.mp3 + vo.srt + vo.json (edge-tts).
- `scripts/probe_media.py` — ffprobe wrapper, JSON output.
- `scripts/generate_sfx.py` — ffmpeg-synthesized SFX library, idempotent.
- `scripts/build_draft.py` — spec.json → 剪映 draft folder.
- `scripts/open_jianying.sh` — restart 剪映 to refresh draft list.
- `scripts/requirements.txt` — `edge-tts`, `pyJianYingDraft`.
