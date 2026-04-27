# Mode B — Script-driven Cut, End-to-End

The user has a finished narration script and a pile of raw clips, no editing plan. The skill helps decide the cut, generates the voiceover, plans SFX, and builds the draft. The user finishes inside 剪映 (transitions, captions, color, BGM, export).

## Working example

### Inputs

`/Users/me/scripts/shenzhenwan.txt`:

```
今天我们来到深圳湾，天气特别好。
海风迎面吹来，远处的高楼一字排开。
没想到这里居然这么安静，完全不像是在大城市。
最让我惊喜的是岸边的红树林，居然能看到白鹭在觅食。
推荐大家有空一定来走走，比想象的还要好。
```

`/Users/me/clips/`:

```
01_skyline_pan.mp4         12s    1920×1080
02_seabreeze_face.mp4       6s    1920×1080
03_park_silence.mp4         8s    1920×1080
04_mangrove_birds.mp4      14s    1920×1080
05_couple_walking.mp4       9s    1920×1080
```

### Step 1 — TTS

```bash
python3 scripts/tts.py /Users/me/scripts/shenzhenwan.txt /tmp/vo --voice zh-CN-YunjianNeural --rate -5%
```

Output `/tmp/vo/vo.json` (truncated):

```json
{
  "voice": "zh-CN-YunjianNeural",
  "duration_s": 18.2,
  "sentences": [
    {"text": "今天我们来到深圳湾，天气特别好。",            "start_us": 0,         "end_us": 3300000,  "duration_us": 3300000},
    {"text": "海风迎面吹来，远处的高楼一字排开。",         "start_us": 3300000,   "end_us": 7100000,  "duration_us": 3800000},
    {"text": "没想到这里居然这么安静，完全不像是在大城市。", "start_us": 7100000,   "end_us": 11600000, "duration_us": 4500000},
    {"text": "最让我惊喜的是岸边的红树林，居然能看到白鹭在觅食。", "start_us": 11600000,  "end_us": 16500000, "duration_us": 4900000},
    {"text": "推荐大家有空一定来走走，比想象的还要好。",   "start_us": 16500000,  "end_us": 18200000, "duration_us": 1700000}
  ]
}
```

### Step 2 — Map sentences to clips

Read filenames. They're descriptive enough — propose:

| # | Sentence (start–end) | Proposed clip(s) | Trim |
|---|---|---|---|
| 1 | 今天我们来到深圳湾… (0.0–3.3s) | `01_skyline_pan.mp4` | first 3.3s |
| 2 | 海风迎面吹来… (3.3–7.1s) | `02_seabreeze_face.mp4` | first 3.8s |
| 3 | 没想到这里居然这么安静… (7.1–11.6s) | `03_park_silence.mp4` | full 4.5s of 8s |
| 4 | 最让我惊喜的是… (11.6–16.5s) | `04_mangrove_birds.mp4` | first 4.9s |
| 5 | 推荐大家有空… (16.5–18.2s) | `05_couple_walking.mp4` | first 1.7s |

Show this table to the user, ask "OK 这个映射？" before proceeding. **Do not silently commit to a guess** — wrong mapping wastes more time than 30 seconds of confirmation.

If the filenames are uninformative (e.g. `IMG_2451.mp4`), ask the user for one-line descriptions per clip first.

### Step 3 — Plan SFX

5 sentences × ~18s total. With "balanced" intensity (~1 per 5s), aim for 3–4 SFX:

| At    | SFX                       | Why |
|-------|---------------------------|-----|
| 0.0s  | `transition.whoosh.fast`  | Opening hit |
| 3.3s  | `transition.swoosh`       | Soft transition into "海风" |
| 7.1s  | `meta.bell.chapter`       | Chapter shift to "没想到" |
| 11.6s | `emphasis.ding.bright`    | Highlight "最让我惊喜" |
| 16.5s | `transition.swoosh`       | Outro lead-in |

Skip applause / laughter / ambient — flag for the user to drag in from 剪映's audio library if they want.

### Step 4 — Build the spec

```json
{
  "draft_name": "shenzhenwan_20260427",
  "canvas": {"width": 1920, "height": 1080},
  "fps": 30,
  "clips": [
    {"path": "/Users/me/clips/01_skyline_pan.mp4",     "trim_start_s": 0, "trim_end_s": 3.3},
    {"path": "/Users/me/clips/02_seabreeze_face.mp4",  "trim_start_s": 0, "trim_end_s": 3.8},
    {"path": "/Users/me/clips/03_park_silence.mp4",    "trim_start_s": 0, "trim_end_s": 4.5},
    {"path": "/Users/me/clips/04_mangrove_birds.mp4",  "trim_start_s": 0, "trim_end_s": 4.9},
    {"path": "/Users/me/clips/05_couple_walking.mp4",  "trim_start_s": 0, "trim_end_s": 1.7}
  ],
  "voiceover": {"path": "/tmp/vo/vo.mp3", "volume": 1.0},
  "sfx": [
    {"category": "transition.whoosh.fast", "at_s": 0.0,  "volume": 0.5},
    {"category": "transition.swoosh",      "at_s": 3.3,  "volume": 0.45},
    {"category": "meta.bell.chapter",      "at_s": 7.1,  "volume": 0.5},
    {"category": "emphasis.ding.bright",   "at_s": 11.6, "volume": 0.55},
    {"category": "transition.swoosh",      "at_s": 16.5, "volume": 0.45}
  ]
}
```

### Step 5 — Build & open

```bash
python3 scripts/build_draft.py /tmp/spec.json
bash scripts/open_jianying.sh shenzhenwan_20260427
```

### Step 6 — Hand-off message

```
草稿已生成：shenzhenwan_20260427
- 5 段视频拼接，总长 18.2s，配音用 zh-CN-YunjianNeural（-5% 语速）
- 5 处音效已自动嵌入（whoosh/swoosh/bell/ding）
- 字幕：vo.srt 已生成，剪映里"字幕 → 导入字幕"可一键加上
- BGM：未自动添加，请在剪映"音频 → 音乐"里挑一首
- 导出：剪映右上角"导出"，建议 1080p / H.264

如果 SFX 过多/过少，告诉我我重新规划。
```

## Common variations

### Filenames are uninformative

If clips are named `IMG_4521.mp4` etc., ask before TTS:

> 帮我用一行话描述每个素材，我才能映射到文案的句子上。比如：
> ```
> IMG_4521.mp4 = 海边远景
> IMG_4522.mp4 = 海风吹脸特写
> ...
> ```

### Script too long for the available footage

If `Σ clip_durations < vo.duration`, you have:
- Loop a clip (split it into multiple segments inside 剪映 — this skill doesn't auto-loop video).
- Use a still image to fill: `{"path": ".../filler.jpg", "duration_s": <gap>}`.
- Slow down a clip (set `target_timerange.duration > source_timerange.duration` — needs hand-edit of the JSON; not exposed by `build_draft.py`).
- Tell the user to record more footage or shorten the script.

### User changes their mind on the mapping

Re-run `build_draft.py` with the updated spec. `allow_replace=True` overwrites the existing draft folder. The user must restart 剪映 to see the new version (`open_jianying.sh` does this automatically).

### Multiple takes / TTS variants

Run `tts.py` with different voices into different output directories:

```bash
python3 scripts/tts.py script.txt /tmp/vo_yunjian --voice zh-CN-YunjianNeural
python3 scripts/tts.py script.txt /tmp/vo_xiaoxiao --voice zh-CN-XiaoxiaoNeural
```

Build two drafts, let the user A/B in 剪映.

## Anti-patterns

- ❌ Don't auto-pick a clip mapping when filenames are unclear and proceed silently. Ask.
- ❌ Don't put every SFX from the manifest into one project. Density >1 per 3s gets noisy.
- ❌ Don't put SFX on top of speech mid-sentence (except tiny `meta.click.tick` at commas). Whooshes belong at sentence boundaries.
- ❌ Don't try to fake BGM with looped SFX. BGM is a 剪映 step.
- ❌ Don't ship draft with `allow_replace=False` — the user will iterate and need to overwrite.
