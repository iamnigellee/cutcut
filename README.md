# jianyingpro-mix-edit — 剪映专业版混剪 Skill

An [Anthropic Skill](https://github.com/anthropics/skills) for macOS that takes a list of video clips, a voiceover, and a BGM track, generates a 剪映专业版 draft, and opens 剪映 to it for the human to fine-tune and export.

The skill itself lives at [`skills/jianyingpro-mix-edit/`](skills/jianyingpro-mix-edit/).

## Install

The skill follows the standard Anthropic Skill layout (a `SKILL.md` plus bundled scripts and references), so any Claude client that loads skills from `~/.claude/skills/` will pick it up.

```bash
# 1. Clone this repo somewhere persistent.
git clone https://github.com/iamnigellee/cutcut ~/code/cutcut

# 2. Symlink (or copy) the skill folder into your skills directory.
mkdir -p ~/.claude/skills
ln -s ~/code/cutcut/skills/jianyingpro-mix-edit ~/.claude/skills/jianyingpro-mix-edit

# 3. Install the runtime dependencies.
brew install ffmpeg
python3 -m pip install --user -r ~/.claude/skills/jianyingpro-mix-edit/scripts/requirements.txt
```

Restart your Claude client. The skill becomes available; ask "用剪映把这几个素材混剪一下，加一段配音和 BGM" and it triggers.

## Requirements

- macOS (the skill is macOS-only).
- 剪映专业版 installed at `/Applications/JianyingPro.app`.
- Python 3.9+.
- ffmpeg / ffprobe.
- [`pyJianYingDraft`](https://github.com/GuanYixuan/pyJianYingDraft) ≥ 0.2.6.

## What the skill does

Given media files plus a description, the skill:

1. Probes each media file with `ffprobe` (handles rotation metadata).
2. Generates `draft_content.json` and `draft_meta_info.json` via `pyJianYingDraft`, laying clips end-to-end on the main video track and adding voiceover + BGM tracks.
3. Writes the draft folder under `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/`.
4. Restarts 剪映 (it caches the draft list, so a restart is necessary) and tells the user where to find the new draft.

The user finishes inside 剪映: transitions, captions, color, export.

## What the skill does **not** do

- Headless export. 剪映 disables export on macOS for third-party-generated drafts; export is manual.
- Transitions, captions, color grading, effects. Add these in 剪映.
- Multi-track video composites or PIP. Out of scope.

## Layout

```
skills/jianyingpro-mix-edit/
├── SKILL.md
├── scripts/
│   ├── build_draft.py          # Main: spec.json → draft folder
│   ├── probe_media.py          # ffprobe wrapper
│   ├── open_jianying.sh        # Restart 剪映 to refresh the draft list
│   └── requirements.txt
├── references/
│   ├── spec_schema.md          # Input spec format
│   ├── draft_format.md         # Internals of draft_content.json
│   └── troubleshooting.md      # Diagnostic flowchart
└── assets/
    └── example_spec.json
```

## Manual usage (without an LLM client)

```bash
# Edit a copy of the example to point at your media.
cp skills/jianyingpro-mix-edit/assets/example_spec.json /tmp/mix.json
$EDITOR /tmp/mix.json

# Build.
python3 skills/jianyingpro-mix-edit/scripts/build_draft.py /tmp/mix.json

# Open 剪映.
bash skills/jianyingpro-mix-edit/scripts/open_jianying.sh demo_mix
```

## License

MIT.
