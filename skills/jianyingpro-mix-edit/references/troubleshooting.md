# Troubleshooting

## The new draft does not appear in 剪映's draft list

Most common cause: **剪映 caches the draft list at startup.** A draft folder dropped in while 剪映 is running is invisible until restart.

```bash
pkill -x JianyingPro
sleep 1
open -a JianyingPro
```

If still not visible:

1. Confirm the draft is under the path 剪映 reads. Default is `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/`. The user may have changed it via 剪映 → 全局设置 → 草稿位置.
2. Confirm both `draft_content.json` and `draft_meta_info.json` exist.
3. Open `draft_meta_info.json` and verify `draft_fold_path` and `draft_root_path` are correct absolute paths for this machine.
4. Test with an ASCII-only `draft_name` to rule out encoding issues.

## 剪映 says "无法读取媒体" / "Media unavailable"

- Path is wrong, moved, or relative. Grep `draft_content.json` for the path.
- macOS quarantine xattr on a downloaded file:
  ```bash
  xattr -d com.apple.quarantine "<file>"
  ```
- 剪映 needs Files-and-Folders permission for the source directory the first time. System Settings → Privacy & Security → Files and Folders → JianyingPro. Approve, restart 剪映.

## `pyJianYingDraft` import fails

```bash
python3 -m pip install --user -r scripts/requirements.txt
```

If multiple Pythons are installed (system + Homebrew + asdf), use the absolute path of the one you want and install with that interpreter.

## `edge-tts` import fails or hangs

```bash
python3 -m pip install --user edge-tts
```

If `tts.py` hangs forever: edge-tts needs network access to Microsoft's Edge TTS endpoint. Check connectivity. There's no offline fallback.

If edge-tts returns "no audio data": the voice ID is wrong or temporarily unavailable. Try `edge-tts --list-voices | grep zh-CN` to confirm and pick another.

## `ffmpeg` / `ffprobe` not found

```bash
brew install ffmpeg
```

The skill needs:
- `ffprobe` for media probing in `probe_media.py`.
- `ffmpeg` for SFX synthesis in `generate_sfx.py`.

Both ship together with `ffmpeg`. There's no fallback.

## SFX sounds wrong / too soft / too loud

The synthesis recipes are in `assets/sfx_manifest.json`. Each is a single ffmpeg lavfi source + filter chain. Edit the recipe (e.g. raise `volume=0.5` to `volume=0.7`) and run:

```bash
python3 scripts/generate_sfx.py --force
```

Forces regeneration of all files. Re-run `build_draft.py` to embed the new versions.

If you want a category that isn't synthesizable (applause, laughter, ambient rain): there is no shortcut. Use 剪映's built-in audio library after the draft opens.

## `generate_sfx.py` fails with ffmpeg error

The error is printed to stderr. Common causes:
- Old ffmpeg without `lavfi` source (very old; reinstall via Homebrew).
- Missing `vibrato` / `afade` / `anoisesrc` filter (extremely rare; reinstall ffmpeg).
- Output directory not writable.

Run `ffmpeg -filters | grep <filter>` to confirm the filter is available.

## SFX timing drifts vs. voiceover

Symptoms: ding lands a beat after the punchline, whoosh is half a second early.

Causes:
- `vo.json` is built from edge-tts WordBoundary events; for very fast speech rates (`+30%` and above) the timing accuracy degrades.
- Punctuation (commas) doesn't have its own WordBoundary event, so commas inside a sentence are interpolated, not measured.

Mitigations:
- Use `--rate -5%` to `+10%` for best timing accuracy.
- Round SFX `at_s` to sentence boundaries, not mid-sentence words, when possible.
- After the draft opens, nudge SFX positions by a few frames inside 剪映 — fast and reliable.

## 剪映 crashes opening the draft

Almost always malformed `draft_content.json`. `pyJianYingDraft` produces well-formed JSON, so a crash usually means:

- Hand-edit introduced a bug → re-run `build_draft.py`.
- A required empty array was lost → re-run `build_draft.py`.
- Top-level `duration` is `0` because all clips somehow got skipped → check the build report's `duration_s`.

Don't hand-edit `draft_content.json` unless you understand `references/draft_format.md`.

## TTS output is in the wrong language

edge-tts auto-detects from the voice. If the voice is `zh-CN-*`, the script must be Chinese. If you mix English in a Chinese voice it's pronounced phonetically (sometimes badly). For mixed-language scripts:

- Wrap English chunks in `<lang xml:lang="en-US">…</lang>` and use SSML mode (see `tts_styles.md`).
- Or split the script into language-pure chunks and TTS each separately, concatenate with ffmpeg.

## Draft total duration looks wrong

`build_draft.py` prints `duration_s`. It's the sum of clip durations on the main track, ignoring trailing silence in the voiceover. If your VO is longer than the video, the tail of the VO plays over a black frame in 剪映 — extend the last clip or add a still image to fill.

## "out of disk" during SFX generation

The full library is ~1 MB total (13 mono WAVs at 44.1 kHz). If you hit a disk-full error, it's not the SFX. Check `/tmp` (where TTS output may live) and `~/Movies/JianyingPro/`.

## Different macOS user / shared draft

If you generate the draft as user A and another user B opens 剪映, the absolute paths in `draft_content.json` won't resolve. Two fixes:

- Generate again as user B with their paths.
- Copy media files into the draft folder itself, then sed-replace paths in `draft_content.json` to relative-from-folder. (剪映 does not officially support relatives; this is fragile.)
