# Troubleshooting

## The new draft does not appear in 剪映's draft list

Most common cause: **剪映 caches the draft list at startup.** A draft folder dropped in while 剪映 is running is invisible until restart.

Fix:
```bash
pkill -x JianyingPro
sleep 1
open -a JianyingPro
```

If it still doesn't appear:

1. Confirm the draft folder is actually under the path 剪映 is reading from. The default is `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/`, but the user may have moved it via 剪映 → 全局设置 → 草稿位置. Verify with:
   ```bash
   defaults read com.lveditor.JianyingPro 2>/dev/null | grep -i draft
   ```
2. Confirm both `draft_content.json` and `draft_meta_info.json` exist in the folder.
3. Open `draft_meta_info.json` and verify `draft_fold_path` and `draft_root_path` are absolute and correct for this machine.
4. Look for the draft folder name itself with weird characters; rename to ASCII-only as a test.

## 剪映 opens but says "无法读取媒体" / "Media unavailable"

- The media file path in `draft_content.json` is wrong (typo, moved file, relative). Open the JSON and grep for the path.
- The file has a macOS quarantine xattr and 剪映 refuses to open it:
  ```bash
  xattr -d com.apple.quarantine "<file>"
  ```
- The first time 剪映 reads files outside `~/Movies`, macOS prompts for Files-and-Folders permission. Approve it (System Settings → Privacy & Security → Files and Folders → JianyingPro). To avoid this entirely, copy media into the draft folder.

## `pyJianYingDraft` import fails

```bash
python3 -m pip install --user pyJianYingDraft
```

If `pip` is missing:
```bash
python3 -m ensurepip --user
```

If you have multiple Python interpreters (e.g. system Python + Homebrew + asdf), make sure the same interpreter is used for installation and for running the script. Check with `which -a python3` and use the absolute path.

## `ffprobe` not found

```bash
brew install ffmpeg
```

The skill uses `ffprobe` (bundled with ffmpeg) to read width / height / duration / rotation from media. There is no fallback.

## 剪映 crashes on opening the draft

Almost always a malformed `draft_content.json`. Common causes:

- A required empty array was omitted from `materials` (e.g. `materials.audio_fades`). The full list of buckets must exist.
- A segment is missing `extra_material_refs`, `common_keyframes`, or `keyframe_refs`.
- Top-level `duration` is `0` or shorter than the longest segment.

Fix: re-run `build_draft.py` so pyJianYingDraft regenerates from its template. Don't hand-edit unless you know what you're doing.

## Draft total duration looks wrong

`build_draft.py` reports `duration_s` in its JSON output. Sanity-check it against the sum of clip lengths you intended. If a clip's `trim_end_s` exceeds the source duration the script clamps silently to source length — re-probe with `scripts/probe_media.py <path>` to see the true source duration.

## BGM ends abruptly mid-project

You set `loop: false` and the BGM is shorter than the project. Either set `loop: true`, or pick a longer BGM, or add a fade-out manually inside 剪映.

## Voiceover starts at the wrong time

The script always places the voiceover at `target_start = 0`. To delay it, either pad the front of the voiceover audio with silence (e.g. via ffmpeg `adelay`), or move the segment manually inside 剪映.

## 剪映 6+ doesn't recognize the draft after I edit it from outside

剪映 6.x re-saves drafts in an encrypted form. Once you save a draft inside 剪映 6+, third-party tools (including this skill) can no longer read or modify it. Workflow: always **regenerate from spec** rather than round-tripping; treat 剪映 as the final-mile editor.

## Export is greyed out / missing in 剪映 7

剪映 7 hides export controls in some builds. This is upstream behavior unrelated to draft generation. Workarounds documented in 剪映 community forums; not in scope for this skill.
