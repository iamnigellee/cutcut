#!/usr/bin/env python3
"""Probe a media file with ffprobe and return JSON: duration_us, width, height, kind.

Usage:
    python3 probe_media.py <path>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def probe(path: str) -> dict:
    p = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-print_format", "json",
            "-show_streams", "-show_format",
            path,
        ],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(p.stdout)

    fmt = info.get("format", {})
    duration_s = float(fmt.get("duration", 0.0))
    duration_us = int(round(duration_s * 1_000_000))

    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    width = height = 0
    if video is not None:
        width = int(video.get("width", 0))
        height = int(video.get("height", 0))
        for sd in video.get("side_data_list", []) or []:
            rot = int(sd.get("rotation", 0) or 0)
            if abs(rot) == 90 or abs(rot) == 270:
                width, height = height, width
                break

    if video is not None and (video.get("codec_name") or "") not in {"mjpeg", "png"}:
        kind = "video"
    elif video is not None:
        kind = "image"
    elif audio is not None:
        kind = "audio"
    else:
        kind = "unknown"

    return {
        "path": str(Path(path).resolve()),
        "duration_us": duration_us,
        "width": width,
        "height": height,
        "kind": kind,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: probe_media.py <path>", file=sys.stderr)
        return 2
    print(json.dumps(probe(sys.argv[1]), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
