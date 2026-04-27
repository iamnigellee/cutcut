# Mix-Spec JSON Schema

The `build_draft.py` script consumes a single JSON file with this shape. Every path **must be absolute**; 剪映 stores absolute paths and does not resolve relatives.

## Top level

| Field        | Type   | Required | Default            | Notes |
|--------------|--------|----------|--------------------|-------|
| `draft_name` | string | yes      | —                  | Folder name under 剪映's drafts directory. Avoid `/`. Chinese OK. |
| `canvas`     | object | no       | `{1920, 1080}`     | See *Canvas* below. |
| `fps`        | number | no       | `30`               | Project default frame rate. Segments are timed in microseconds, not frames. |
| `clips`      | array  | yes      | —                  | Ordered list of video/image clips for the main track. Min length 1. |
| `voiceover`  | object | no       | omit               | One audio segment laid over the full project. See *Audio Track*. |
| `bgm`        | object | no       | omit               | Background music segment. See *Audio Track*. |

## Canvas

```json
{"width": 1920, "height": 1080}
```

Common presets:
- `1920 × 1080` — landscape 16:9
- `1080 × 1920` — vertical 9:16 (抖音 / TikTok / 小红书)
- `1080 × 1080` — square 1:1
- `3840 × 2160` — 4K landscape

The script does **not** auto-crop or auto-scale clips to fit the canvas. Clips with a different aspect will be letterboxed; the user adjusts in 剪映.

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

Trim semantics: `trim_end_s > trim_start_s` is enforced. If `trim_end_s` exceeds the source duration, it is clamped.

Supported source kinds:
- Video: anything ffprobe identifies as a non-still video stream (mp4, mov, mkv, webm, …).
- Image: jpeg, png (codec_name `mjpeg` / `png`). Treated as a still held for `duration_s`.

## Voiceover

```json
{"path": "/abs/vo.mp3", "volume": 1.0}
```

| Field    | Type   | Required | Default | Notes |
|----------|--------|----------|---------|-------|
| `path`   | string | yes      | —       | Audio file (mp3, wav, m4a, …). |
| `volume` | number | no       | `1.0`   | Linear gain. `0.0` = mute, `1.0` = unity, `>1.0` = boost. |

Placement: starts at `target_start = 0`, length = `min(VO duration, total project duration)`. If the VO is longer than the video, it is trimmed; if shorter, the tail is silent. To delay the VO, edit inside 剪映.

## BGM

```json
{"path": "/abs/bgm.mp3", "volume": 0.3, "loop": true}
```

| Field    | Type    | Required | Default | Notes |
|----------|---------|----------|---------|-------|
| `path`   | string  | yes      | —       | Audio file. |
| `volume` | number  | no       | `0.3`   | Typically lower than voiceover so narration is intelligible. |
| `loop`   | boolean | no       | `true`  | If true and BGM is shorter than the project, BGM is repeated end-to-end. If false, the tail is silent. |

When BGM is longer than the project, it is trimmed to project length regardless of `loop`.

## Output

`build_draft.py` writes the draft to:

```
~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/<draft_name>/
├── draft_content.json
└── draft_meta_info.json
```

(Override the parent directory with `--draft-root`.)

It prints a JSON report to stdout:

```json
{
  "draft_name": "demo_mix",
  "draft_path": "/Users/.../com.lveditor.draft/demo_mix",
  "duration_us": 23456789,
  "duration_s": 23.457,
  "clip_count": 3,
  "has_voiceover": true,
  "has_bgm": true,
  "clips": [
    {"index": 0, "path": "...", "kind": "video", "target_start_us": 0, "duration_us": 5000000},
    {"index": 1, "path": "...", "kind": "video", "target_start_us": 5000000, "duration_us": 6500000},
    {"index": 2, "path": "...", "kind": "image", "target_start_us": 11500000, "duration_us": 3000000}
  ]
}
```

## What this skill does NOT cover

These need to be done inside 剪映 (or with custom edits to `draft_content.json`; see `draft_format.md`):

- Transitions between clips.
- Text overlays / captions / 字幕.
- Color grading, LUTs, filters.
- Speed ramps, slow motion.
- Picture-in-picture, multi-track video composites.
- Effects, animations, keyframes.
- Multiple BGM tracks or BGM with volume automation.
