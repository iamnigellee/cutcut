#!/usr/bin/env python3
"""Build a 剪映专业版 draft on macOS from a mix-spec JSON.

Spec schema (full reference: references/spec_schema.md):
    {
      "draft_name": "my_mix",
      "canvas": {"width": 1920, "height": 1080},
      "fps": 30,
      "clips": [
        {"path": "/abs/clip1.mp4"},
        {"path": "/abs/clip2.mp4", "trim_start_s": 1.0, "trim_end_s": 5.5},
        {"path": "/abs/photo.jpg", "duration_s": 3.0}
      ],
      "voiceover": {"path": "/abs/vo.mp3", "volume": 1.0},
      "sfx": [
        {"category": "transition.whoosh.fast", "at_s": 1.84, "volume": 0.5},
        {"category": "emphasis.ding.bright",   "at_s": 5.20, "volume": 0.6}
      ]
    }

BGM is intentionally not supported — add background music inside 剪映 using
its built-in music library. SFX categories are defined in
assets/sfx_manifest.json and synthesized with scripts/generate_sfx.py.

Usage:
    python3 build_draft.py <spec.json> [--draft-root <dir>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# probe_media.py lives next to this script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_media import probe  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SFX_MANIFEST_PATH = SKILL_DIR / "assets" / "sfx_manifest.json"
SFX_DIR = SKILL_DIR / "assets" / "sfx"
DEFAULT_DRAFT_ROOT = (
    Path.home() / "Movies/JianyingPro/User Data/Projects/com.lveditor.draft"
)
PHOTO_DEFAULT_DURATION_S = 3.0


def _populate_meta(draft_dir: Path, draft_name: str, total_us: int) -> None:
    """Fill draft_meta_info.json fields pyJianYingDraft leaves empty.

    Without this, JianYing self-heals on first scan but the new draft
    initially appears unnamed and may take a list-refresh before
    showing up correctly.
    """
    import time
    import uuid
    meta_path = draft_dir / "draft_meta_info.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    now_us = int(time.time() * 1_000_000)
    # pyJianYingDraft's stub hardcodes the same draft_id for every draft;
    # generate a fresh one so JianYing doesn't see duplicates.
    meta["draft_id"] = str(uuid.uuid4()).upper()
    meta["draft_name"] = draft_name
    meta["draft_fold_path"] = str(draft_dir)
    meta["draft_root_path"] = str(draft_dir.parent)
    meta["tm_draft_create"] = now_us
    meta["tm_draft_modified"] = now_us
    meta["tm_duration"] = int(total_us)
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def s_to_us(seconds: float) -> int:
    return int(round(seconds * 1_000_000))


def _load_pyjy():
    try:
        import pyJianYingDraft as draft
        from pyJianYingDraft import Timerange, TrackType
    except ImportError:
        sys.exit(
            "pyJianYingDraft is not installed.\n"
            "Install it with:  python3 -m pip install --user pyJianYingDraft"
        )
    return draft, Timerange, TrackType


def _ensure_sfx_files(categories_used: set[str]) -> dict[str, Path]:
    """Resolve each used category to an absolute file path; auto-generate if missing."""
    if not categories_used:
        return {}
    if not SFX_MANIFEST_PATH.exists():
        raise FileNotFoundError(f"SFX manifest missing: {SFX_MANIFEST_PATH}")
    manifest = json.loads(SFX_MANIFEST_PATH.read_text(encoding="utf-8"))
    cats = manifest.get("categories", {})

    unknown = categories_used - set(cats.keys())
    if unknown:
        known = ", ".join(sorted(cats.keys()))
        raise ValueError(f"unknown sfx categories: {sorted(unknown)}\nKnown: {known}")

    resolved: dict[str, Path] = {}
    missing_files = []
    for c in categories_used:
        f = SFX_DIR / cats[c]["filename"]
        resolved[c] = f
        if not f.exists() or f.stat().st_size == 0:
            missing_files.append(c)

    if missing_files:
        # Auto-run generate_sfx.py for the missing files.
        print(f"Generating {len(missing_files)} missing SFX file(s)...", file=sys.stderr)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "generate_sfx.py")],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            raise RuntimeError("generate_sfx.py failed; install ffmpeg with 'brew install ffmpeg'")
        for c in missing_files:
            if not resolved[c].exists():
                raise RuntimeError(f"sfx file still missing after generation: {resolved[c]}")
    return resolved


def build(spec: dict, draft_root: Path) -> dict:
    draft, Timerange, TrackType = _load_pyjy()
    draft_name = spec["draft_name"]
    canvas = spec.get("canvas", {"width": 1920, "height": 1080})
    fps = int(spec.get("fps", 30))

    clips = spec.get("clips") or []
    if not clips:
        raise ValueError("spec.clips must be a non-empty list")

    voiceover = spec.get("voiceover")
    sfx_entries = spec.get("sfx") or []

    sfx_paths = _ensure_sfx_files({e["category"] for e in sfx_entries})

    draft_root.mkdir(parents=True, exist_ok=True)
    folder = draft.DraftFolder(str(draft_root))
    script = folder.create_draft(
        draft_name,
        int(canvas["width"]),
        int(canvas["height"]),
        fps=fps,
        allow_replace=True,
    )

    script.add_track(TrackType.video, track_name="main_video")
    if voiceover:
        script.add_track(TrackType.audio, track_name="voiceover")
    if sfx_entries:
        script.add_track(TrackType.audio, track_name="sfx")

    cursor_us = 0
    clip_reports = []

    for i, c in enumerate(clips):
        path = c["path"]
        info = probe(path)

        if info["kind"] == "image":
            duration_us = s_to_us(float(c.get("duration_s", PHOTO_DEFAULT_DURATION_S)))
            source_start_us = 0
        elif info["kind"] == "video":
            full_us = info["duration_us"]
            start_s = float(c.get("trim_start_s", 0.0))
            end_s = float(c["trim_end_s"]) if c.get("trim_end_s") is not None else full_us / 1_000_000
            source_start_us = s_to_us(start_s)
            source_end_us = s_to_us(end_s)
            if source_end_us <= source_start_us:
                raise ValueError(f"clip[{i}] {path}: trim_end_s must be > trim_start_s")
            if source_end_us > full_us:
                source_end_us = full_us
            duration_us = source_end_us - source_start_us
        else:
            raise ValueError(f"clip[{i}] {path} is not a video or image (kind={info['kind']})")

        material = draft.VideoMaterial(path)
        seg = draft.VideoSegment(
            material,
            target_timerange=Timerange(cursor_us, duration_us),
            source_timerange=Timerange(source_start_us, duration_us),
        )
        script.add_segment(seg, track_name="main_video")

        clip_reports.append(
            {
                "index": i,
                "path": path,
                "kind": info["kind"],
                "target_start_us": cursor_us,
                "duration_us": duration_us,
            }
        )
        cursor_us += duration_us

    total_us = cursor_us

    if voiceover:
        vo_path = voiceover["path"]
        vo_info = probe(vo_path)
        if vo_info["kind"] != "audio":
            raise ValueError(f"voiceover {vo_path} is not an audio file (kind={vo_info['kind']})")
        vo_dur = min(vo_info["duration_us"], total_us)
        vo_seg = draft.AudioSegment(
            vo_path,
            Timerange(0, vo_dur),
            volume=float(voiceover.get("volume", 1.0)),
        )
        script.add_segment(vo_seg, track_name="voiceover")

    sfx_reports = []
    for j, e in enumerate(sfx_entries):
        cat = e["category"]
        at_us = s_to_us(float(e["at_s"]))
        if at_us >= total_us:
            sfx_reports.append({"index": j, "category": cat, "at_us": at_us, "status": "skipped_past_end"})
            continue
        sfx_file = sfx_paths[cat]
        sfx_info = probe(str(sfx_file))
        sfx_dur = min(sfx_info["duration_us"], total_us - at_us)
        sfx_seg = draft.AudioSegment(
            str(sfx_file),
            Timerange(at_us, sfx_dur),
            volume=float(e.get("volume", 0.5)),
        )
        script.add_segment(sfx_seg, track_name="sfx")
        sfx_reports.append({
            "index": j, "category": cat, "at_us": at_us,
            "duration_us": sfx_dur, "file": str(sfx_file), "status": "added",
        })

    script.save()

    _populate_meta(draft_root / draft_name, draft_name, total_us)

    return {
        "draft_name": draft_name,
        "draft_path": str(draft_root / draft_name),
        "duration_us": total_us,
        "duration_s": round(total_us / 1_000_000, 3),
        "clip_count": len(clips),
        "has_voiceover": bool(voiceover),
        "sfx_count": len(sfx_reports),
        "clips": clip_reports,
        "sfx": sfx_reports,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="Path to mix-spec JSON")
    ap.add_argument("--draft-root", default=str(DEFAULT_DRAFT_ROOT),
                    help="JianYing drafts directory (default: macOS standard)")
    args = ap.parse_args()

    spec_path = Path(args.spec).expanduser().resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    report = build(spec, Path(args.draft_root).expanduser())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
