---
name: jianyingpro-mix-edit
description: Generate a 剪映专业版 (JianYing Pro) draft on macOS that stitches multiple video clips together with a voiceover track and a background-music track, then opens 剪映 to that draft for the user to fine-tune and export. Use whenever the user asks to "做混剪 / 多素材剪辑 / 拼视频 / 配音配乐 / batch edit clips / mix clips with VO and BGM" and intends to finish in 剪映 on a Mac. Triggers on keywords: 剪映, JianYing, 混剪, 配音, 配乐, BGM, 草稿, multi-clip mix, voiceover, background music, draft, macOS video editing.
license: MIT
version: 0.1.0
---

# JianYing Pro 多素材混剪 Skill (macOS)

This skill assembles a 剪映专业版 draft from a list of media files plus a voiceover and a BGM track, places it in 剪映's drafts directory, and opens 剪映 so the user can polish and export. It targets macOS only.

## When to use

Invoke this skill when the user wants to:
- Splice N video clips end-to-end on the main video track.
- Lay one voiceover (配音) audio track over the result.
- Lay one BGM (配乐) track underneath, usually at lower volume, with optional looping.
- Hand off the finished draft to 剪映 for human-in-the-loop fine-tuning (transitions, captions, color, export).

If the user wants a fully headless render (no 剪映 GUI), this skill is the wrong tool — fall back to ffmpeg.

## Prerequisites — verify before running

Run these checks once per session and tell the user what's missing:

```bash
# 1. macOS
test "$(uname)" = "Darwin" || echo "ABORT: this skill is macOS-only"

# 2. JianYing installed
test -d "/Applications/JianyingPro.app" || echo "MISSING: 剪映专业版"

# 3. ffprobe (ffmpeg) for media probing
command -v ffprobe || echo "MISSING: install with 'brew install ffmpeg'"

# 4. Python 3.9+
python3 --version

# 5. pyJianYingDraft (the library this skill depends on)
python3 -c "import pyJianYingDraft" 2>/dev/null || \
  python3 -m pip install --user -r "$SKILL_DIR/scripts/requirements.txt"
```

`$SKILL_DIR` here is the directory containing this `SKILL.md`. Resolve it from the skill's install path (e.g. `~/.claude/skills/jianyingpro-mix-edit`).

## Workflow

### Step 1 — Gather inputs from the user

You need:
- An ordered list of video clip absolute paths (the splice order).
- One voiceover audio path (optional — skip if the user has none).
- One BGM audio path (optional — skip if the user has none).
- A draft name (default: ask, fall back to `mix_<YYYYMMDD_HHMMSS>`).
- Canvas size (default: 1920x1080) and FPS (default: 30).
- BGM volume (default: 0.3) and voiceover volume (default: 1.0).
- Per-clip optional trim (`trim_start_s`, `trim_end_s`).

If anything is ambiguous (e.g. clip order, which file is VO vs BGM), **ask the user** with `AskUserQuestion` before proceeding. Do not guess at media intent.

### Step 2 — Write a spec JSON

Create a `mix_spec.json` (anywhere — `/tmp` is fine) following the schema in `references/spec_schema.md`. A complete example is at `assets/example_spec.json`. Minimum form:

```json
{
  "draft_name": "my_mix_20260427",
  "canvas": {"width": 1920, "height": 1080},
  "fps": 30,
  "clips": [
    {"path": "/Users/me/Videos/a.mp4"},
    {"path": "/Users/me/Videos/b.mp4", "trim_start_s": 2.0, "trim_end_s": 8.5}
  ],
  "voiceover": {"path": "/Users/me/Audio/vo.mp3", "volume": 1.0},
  "bgm": {"path": "/Users/me/Audio/bgm.mp3", "volume": 0.3, "loop": true}
}
```

### Step 3 — Build the draft

```bash
python3 "$SKILL_DIR/scripts/build_draft.py" /tmp/mix_spec.json
```

The script:
1. Probes each media file with `ffprobe` to get duration and dimensions (handles rotation metadata).
2. Uses `pyJianYingDraft` to generate `draft_content.json` and `draft_meta_info.json`.
3. Writes the draft folder under `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/<draft_name>/`.
4. Prints a JSON report with `draft_path`, total `duration_us`, and clip count.

If 剪映's draft directory has been moved (Settings → 全局设置 → 草稿位置), pass `--draft-root /custom/path` to the script.

### Step 4 — Open 剪映

```bash
bash "$SKILL_DIR/scripts/open_jianying.sh" "<draft_name>"
```

The script does `pkill -x JianyingPro` then `open -a JianyingPro`. The relaunch is necessary because **剪映 caches the draft list** and won't show a freshly-written draft until restart. Warn the user that any unsaved work in 剪映 will be lost.

### Step 5 — Hand off to the user

Tell the user:
- Draft name and folder path.
- That the new draft should be visible at the top of 剪映's "草稿" list.
- That export must be done manually inside 剪映 (no headless export on macOS — 剪映 disables it).
- If the draft does not appear: see `references/troubleshooting.md`.

## Inputs that need clarification

If the user gives a vague request like "把这些视频拼一下加段音乐", ask:
1. Order of clips? (You may suggest filename-alphabetical and confirm.)
2. Is there a voiceover, or just BGM?
3. Target aspect (16:9 / 9:16 / 1:1)?
4. Trim any clip, or use full length?

## Common adjustments

- **Vertical (TikTok/抖音) format**: set `canvas: {"width": 1080, "height": 1920}`. The script does not auto-crop — clips with mismatched aspect will letterbox/pillarbox in 剪映 until the user adjusts scale in the GUI.
- **Photos as clips**: supported. For a still image, set `"duration_s": 3.0` on the clip entry; the script holds the photo for that many seconds.
- **No voiceover or no BGM**: omit the `voiceover` or `bgm` key entirely.
- **Multiple BGM tracks (e.g. swap halfway)**: not supported by the spec; build the draft, then split inside 剪映.

## When something fails

- `pyJianYingDraft` import fails → run `pip install pyJianYingDraft` (script tries this automatically with `--user`).
- ffprobe missing → `brew install ffmpeg`.
- Draft does not appear in 剪映 → quit 剪映 fully (`pkill -x JianyingPro`) and reopen. See `references/troubleshooting.md` for more.
- 剪映 says "无法读取媒体" → the media file may have macOS quarantine xattr; strip with `xattr -d com.apple.quarantine <file>`.
- 剪映 6.x and above: generation works fine; only **loading** existing 6.x-encrypted drafts is broken in third-party tools, which doesn't affect this skill since we always write fresh drafts.

## Reference files

Consult on demand — do not load all of these eagerly:

- `references/spec_schema.md` — full spec JSON schema with every optional field.
- `references/draft_format.md` — internals of `draft_content.json` / `draft_meta_info.json` for advanced customization beyond what `build_draft.py` exposes (e.g. transitions, text overlays, keyframes).
- `references/troubleshooting.md` — diagnostic flowchart for when 剪映 misbehaves.
- `assets/example_spec.json` — runnable example spec.

## Bundled tools

- `scripts/build_draft.py` — main entry point. Reads a spec, writes a draft.
- `scripts/probe_media.py` — standalone ffprobe wrapper; useful if you want to inspect a file before adding it.
- `scripts/open_jianying.sh` — restarts 剪映 so the new draft shows up.
- `scripts/requirements.txt` — pip dependencies.
