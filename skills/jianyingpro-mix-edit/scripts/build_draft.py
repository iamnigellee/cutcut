#!/usr/bin/env python3
"""Build a 剪映专业版 draft on macOS from a mix-spec JSON.

Spec schema (see references/spec_schema.md):
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
      "bgm": {"path": "/abs/bgm.mp3", "volume": 0.3, "loop": true}
    }

Usage:
    python3 build_draft.py <spec.json> [--draft-root <dir>]

Prints a JSON report to stdout on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# probe_media.py lives next to this script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_media import probe  # noqa: E402

DEFAULT_DRAFT_ROOT = (
    Path.home() / "Movies/JianyingPro/User Data/Projects/com.lveditor.draft"
)
PHOTO_DEFAULT_DURATION_S = 3.0


def s_to_us(seconds: float) -> int:
    return int(round(seconds * 1_000_000))


def _load_pyjy():
    """Lazy import so --help works without the dependency installed."""
    try:
        import pyJianYingDraft as draft
        from pyJianYingDraft import Timerange, TrackType
    except ImportError:
        sys.exit(
            "pyJianYingDraft is not installed.\n"
            "Install it with:  python3 -m pip install --user pyJianYingDraft"
        )
    return draft, Timerange, TrackType


def build(spec: dict, draft_root: Path) -> dict:
    draft, Timerange, TrackType = _load_pyjy()
    draft_name = spec["draft_name"]
    canvas = spec.get("canvas", {"width": 1920, "height": 1080})
    fps = int(spec.get("fps", 30))

    clips = spec.get("clips") or []
    if not clips:
        raise ValueError("spec.clips must be a non-empty list")

    voiceover = spec.get("voiceover")
    bgm = spec.get("bgm")

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
    if bgm:
        script.add_track(TrackType.audio, track_name="bgm")

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

    if bgm:
        bgm_path = bgm["path"]
        bgm_info = probe(bgm_path)
        if bgm_info["kind"] != "audio":
            raise ValueError(f"bgm {bgm_path} is not an audio file (kind={bgm_info['kind']})")
        bgm_volume = float(bgm.get("volume", 0.3))
        bgm_loop = bool(bgm.get("loop", True))

        if bgm_loop and bgm_info["duration_us"] < total_us:
            t = 0
            while t < total_us:
                seg_dur = min(bgm_info["duration_us"], total_us - t)
                seg = draft.AudioSegment(
                    bgm_path,
                    Timerange(t, seg_dur),
                    volume=bgm_volume,
                )
                script.add_segment(seg, track_name="bgm")
                t += seg_dur
        else:
            seg_dur = min(bgm_info["duration_us"], total_us)
            seg = draft.AudioSegment(
                bgm_path,
                Timerange(0, seg_dur),
                volume=bgm_volume,
            )
            script.add_segment(seg, track_name="bgm")

    script.save()

    return {
        "draft_name": draft_name,
        "draft_path": str(draft_root / draft_name),
        "duration_us": total_us,
        "duration_s": round(total_us / 1_000_000, 3),
        "clip_count": len(clips),
        "has_voiceover": bool(voiceover),
        "has_bgm": bool(bgm),
        "clips": clip_reports,
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
