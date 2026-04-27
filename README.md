# jianyingpro-mix-edit — 剪映专业版混剪 Skill

An [Anthropic Skill](https://github.com/anthropics/skills) for macOS that:

1. Stitches a list of video clips end-to-end.
2. (Optional) Synthesizes a voiceover from a text script via [edge-tts](https://github.com/rany2/edge-tts) — free, no API key.
3. (Optional) Auto-places sound effects (whoosh / ding / boom / pop / boing / …) at semantically appropriate moments. SFX are **synthesized procedurally with ffmpeg** — no license issues, no network dependency, no missing files.
4. Generates a 剪映专业版 draft and opens 剪映 to it.
5. Hands off to the user for transitions, captions, color grading, BGM, and export.

The skill itself lives at [`skills/jianyingpro-mix-edit/`](skills/jianyingpro-mix-edit/).

## Two workflows

- **Mode A — Clips + script**: user has clips, gives a narration script. Skill TTSs, places SFX on the beats, builds the draft.
- **Mode B — Script-driven cut**: user has script + raw clips. Skill TTSs, helps map sentences to clips, places SFX, builds the draft.

In both modes, **BGM is added inside 剪映** (剪映 has a great built-in music library).

## Install

The skill follows the standard Anthropic Skill layout (`SKILL.md` + bundled scripts + references), so any Claude client that loads skills from `~/.claude/skills/` will pick it up.

```bash
# 1. Clone this repo somewhere persistent.
git clone https://github.com/iamnigellee/cutcut ~/code/cutcut

# 2. Symlink (or copy) the skill folder into your skills directory.
mkdir -p ~/.claude/skills
ln -s ~/code/cutcut/skills/jianyingpro-mix-edit ~/.claude/skills/jianyingpro-mix-edit

# 3. Install runtime dependencies.
brew install ffmpeg
python3 -m pip install --user -r ~/.claude/skills/jianyingpro-mix-edit/scripts/requirements.txt
```

Restart your Claude client. Ask "用剪映把这些素材混剪一下，文案我给你"，skill 自动触发。

## Requirements

- macOS (skill is macOS-only).
- 剪映专业版 installed at `/Applications/JianyingPro.app`.
- Python 3.9+.
- ffmpeg / ffprobe (`brew install ffmpeg`).
- [`pyJianYingDraft`](https://github.com/GuanYixuan/pyJianYingDraft) ≥ 0.2.6 — draft file generation.
- [`edge-tts`](https://github.com/rany2/edge-tts) ≥ 6.1.0 — voiceover synthesis (free, no API key).

## What the skill does

1. **TTS** — `tts.py` calls edge-tts, writes `vo.mp3` + word-level SRT + sentence-level timing JSON.
2. **Probe** — `probe_media.py` runs ffprobe on each media file (handles rotation metadata).
3. **SFX** — `generate_sfx.py` synthesizes 13 categories of SFX with ffmpeg lavfi (sine waves, filtered noise, vibrato, fades). Idempotent; runs on demand.
4. **Build** — `build_draft.py` generates `draft_content.json` and `draft_meta_info.json` via `pyJianYingDraft`. Lays clips on the main video track, voiceover on track 2, SFX on track 3.
5. **Open** — `open_jianying.sh` restarts 剪映 (it caches the draft list).

## What the skill does **not** do

- ❌ Background music (BGM): use 剪映's built-in music library.
- ❌ Real recorded SFX (applause, laughter, ambient rain): use 剪映's audio library; the skill flags timestamps for the user to drag them in.
- ❌ Headless export: 剪映 disables third-party draft export on macOS.
- ❌ Transitions, color grading, captions, effects: 剪映 GUI.

## SFX library — procedural synthesis

13 categories synthesized with ffmpeg's lavfi sources:

```
transition.whoosh.fast   transition.whoosh.slow   transition.swoosh
emphasis.ding.bright     emphasis.ding.soft       emphasis.pop
impact.boom              impact.thud              reaction.boing
meta.click.tick          meta.page.flip           meta.camera.shutter
meta.bell.chapter
```

Each is a single ffmpeg recipe in [`assets/sfx_manifest.json`](skills/jianyingpro-mix-edit/assets/sfx_manifest.json). Edit the recipe + `python3 scripts/generate_sfx.py --force` to retune.

Why procedural instead of bundled audio files: zero copyright risk, zero network dependency, zero file-rot risk. The waveforms are simple but adequate for short-video punctuation. For complex sounds (applause, laughter, ambient), use 剪映's built-in audio library.

## Layout

```
skills/jianyingpro-mix-edit/
├── SKILL.md
├── scripts/
│   ├── tts.py                  # script.txt → vo.mp3 + vo.srt + vo.json
│   ├── probe_media.py          # ffprobe wrapper
│   ├── generate_sfx.py         # ffmpeg-synthesized SFX library
│   ├── build_draft.py          # spec.json → 剪映 draft folder
│   ├── open_jianying.sh        # Restart 剪映 to refresh draft list
│   └── requirements.txt
├── references/
│   ├── spec_schema.md
│   ├── script_workflow.md      # Mode B end-to-end walkthrough
│   ├── tts_styles.md           # voice + style decision table
│   ├── draft_format.md
│   └── troubleshooting.md
└── assets/
    ├── example_spec.json
    ├── sfx_manifest.json       # 13 SFX recipes
    └── sfx/                    # generated WAVs (created on first run)
```

## Manual usage (without an LLM client)

```bash
# 1. TTS the script.
python3 skills/jianyingpro-mix-edit/scripts/tts.py \
    /tmp/script.txt /tmp/vo --voice zh-CN-YunjianNeural

# 2. Edit a copy of the example to point at your media + the TTS output.
cp skills/jianyingpro-mix-edit/assets/example_spec.json /tmp/mix.json
$EDITOR /tmp/mix.json

# 3. Build (auto-synthesizes SFX library on first run).
python3 skills/jianyingpro-mix-edit/scripts/build_draft.py /tmp/mix.json

# 4. Open 剪映.
bash skills/jianyingpro-mix-edit/scripts/open_jianying.sh demo_mix
```

## License

MIT. SFX waveforms are generated procedurally and not subject to third-party copyright. TTS output is subject to Microsoft's edge-tts terms of use.
