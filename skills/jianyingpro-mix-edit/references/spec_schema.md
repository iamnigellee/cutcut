# Mix-Spec JSON Schema

`build_draft.py` consumes a single JSON file with this shape. All paths must be **absolute** — 剪映 stores absolute paths and does not resolve relatives.

## Top level

| Field        | Type   | Required | Default            | Notes |
|--------------|--------|----------|--------------------|-------|
| `draft_name` | string | yes      | —                  | Folder name under 剪映's drafts directory. Avoid `/`. Chinese OK. |
| `canvas`     | object | no       | `{1920, 1080}`     | See *Canvas*. |
| `fps`        | number | no       | `30`               | Project default frame rate. Segments are timed in microseconds, not frames. |
| `clips`      | array  | yes      | —                  | Ordered list of video/image clips for the main track. Min length 1. |
| `voiceover`  | object | no       | omit               | Single audio segment laid over the project (typically TTS output). |
| `sfx`        | array  | no       | omit               | Sound effects placed at specific timestamps. See *SFX*. |

**BGM is intentionally absent** — add background music inside 剪映 using its built-in library (音频 → 音乐).

## Canvas

```json
{"width": 1920, "height": 1080}
```

Common presets:
- `1920 × 1080` — landscape 16:9
- `1080 × 1920` — vertical 9:16 (抖音 / TikTok / 小红书)
- `1080 × 1080` — square 1:1
- `3840 × 2160` — 4K landscape

The script does not auto-crop or scale clips. Mismatched aspects letterbox in 剪映; user adjusts in the GUI.

## Clip entry

```json
{
  "path": "/abs/path/to/file.mp4",
  "trim_start_s": 0.0,
  "trim_end_s": 12.5,
  "duration_s": 3.0
}
```

| Field          | Type   | Applies to    | Notes |
|----------------|--------|---------------|-------|
| `path`         | string | all           | Absolute path. |
| `trim_start_s` | number | video only    | Seconds into source where this clip begins. Default `0`. |
| `trim_end_s`   | number | video only    | Seconds into source where this clip ends. Default = source duration. |
| `duration_s`   | number | image only    | How long to hold the still on screen. Default `3.0`. |

`trim_end_s` clamps to source duration if it exceeds it. `trim_end_s > trim_start_s` is enforced.

Supported source kinds: video (mp4/mov/mkv/webm/…) and image (jpeg/png).

## Voiceover

```json
{"path": "/abs/vo.mp3", "volume": 1.0}
```

| Field    | Type   | Required | Default | Notes |
|----------|--------|----------|---------|-------|
| `path`   | string | yes      | —       | Audio file (mp3, wav, m4a, …). |
| `volume` | number | no       | `1.0`   | Linear gain. `0.0` = mute, `1.0` = unity, `>1.0` = boost. |

Placement: starts at `target_start = 0`, length = `min(VO duration, total project duration)`. To delay it, pad the front of the audio with silence (e.g. ffmpeg `adelay`) or move it inside 剪映.

## SFX

```json
[
  {"category": "transition.whoosh.fast", "at_s": 1.84, "volume": 0.5},
  {"category": "emphasis.ding.bright",   "at_s": 5.20, "volume": 0.6}
]
```

| Field      | Type   | Required | Default | Notes |
|------------|--------|----------|---------|-------|
| `category` | string | yes      | —       | Must match a key in `assets/sfx_manifest.json`. See list below. |
| `at_s`     | number | yes      | —       | Start time on the project timeline, seconds. |
| `volume`   | number | no       | `0.5`   | Linear gain. SFX usually sit lower than VO so narration stays primary. |

The skill resolves `category` to a file via the manifest, runs `generate_sfx.py` if the file doesn't exist (idempotent), and adds the segment to the `sfx` audio track.

If `at_s` is past the project end, the entry is skipped (reported in the build output).

### Available SFX categories

| Category | Intent | Approx. duration |
|---|---|---|
| `transition.whoosh.fast`  | Quick whoosh — tight cuts                  | 0.45 s |
| `transition.whoosh.slow`  | Long whoosh — major scene changes          | 1.0 s |
| `transition.swoosh`       | Subtle airy swoosh — gentle transition     | 0.7 s |
| `emphasis.ding.bright`    | Bright bell — punchline / hard emphasis    | 0.5 s |
| `emphasis.ding.soft`      | Soft chime — gentle emphasis               | 0.6 s |
| `emphasis.pop`            | Quick pop — punctuation                    | 0.15 s |
| `impact.boom`             | Low boom — dramatic impact / reveal        | 1.0 s |
| `impact.thud`             | Heavy thud — physical hit                  | 0.5 s |
| `reaction.boing`          | Cartoon boing — comedic / surprise         | 0.6 s |
| `meta.click.tick`         | Tiny tick — bullet point / list item       | 0.06 s |
| `meta.page.flip`          | Paper page flip — chapter break            | 0.4 s |
| `meta.camera.shutter`     | Camera shutter — photo / freeze moment     | 0.25 s |
| `meta.bell.chapter`       | Sustained soft bell — section change       | 1.5 s |

**Not synthesizable, not in this library** — fetch from 剪映's built-in audio library after the draft opens:
- Applause / 鼓掌
- Human laughter / 笑声
- Voiceover-like human SFX
- Complex ambient: rain, crowd, traffic, café

## Output

`build_draft.py` writes:

```
~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/<draft_name>/
├── draft_content.json
└── draft_meta_info.json
```

(Override the parent with `--draft-root`.)

stdout is a JSON report:

```json
{
  "draft_name": "demo_mix",
  "draft_path": "/Users/.../com.lveditor.draft/demo_mix",
  "duration_us": 23456789,
  "duration_s": 23.457,
  "clip_count": 3,
  "has_voiceover": true,
  "sfx_count": 4,
  "clips": [...],
  "sfx":   [...]
}
```

## What this skill does NOT cover

These belong in 剪映 (or in advanced custom edits to `draft_content.json`; see `draft_format.md`):

- BGM / 背景音乐.
- Real recorded SFX (applause, laughter, ambient).
- Transitions between clips (zoom, dissolve, etc.).
- Text overlays / captions / 字幕 (you can import `vo.srt` inside 剪映).
- Color grading, LUTs, filters.
- Speed ramps, slow motion.
- Picture-in-picture, multi-track video composites.
- Effects, animations, keyframes.
