#!/usr/bin/env python3
"""Synthesize the SFX library with ffmpeg from sfx_manifest.json.

Idempotent: files already present are skipped (use --force to regenerate).
Each recipe is a single ffmpeg lavfi source + filter chain producing a mono WAV.

Usage:
    python3 generate_sfx.py [--out-dir <dir>] [--force]

Output:
    <out_dir>/<filename>.wav for every category in the manifest.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = SCRIPT_DIR.parent / "assets" / "sfx_manifest.json"
DEFAULT_OUT_DIR = SCRIPT_DIR.parent / "assets" / "sfx"


def synth(category: str, recipe: dict, out_dir: Path, force: bool) -> dict:
    out_path = out_dir / recipe["filename"]
    if out_path.exists() and out_path.stat().st_size > 0 and not force:
        return {"category": category, "file": str(out_path), "status": "skipped"}

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", recipe["ffmpeg_input"],
        "-af", recipe["ffmpeg_filter"],
        "-ar", "44100", "-ac", "1",
        str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {
            "category": category,
            "file": str(out_path),
            "status": "failed",
            "stderr": proc.stderr.strip(),
        }
    return {"category": category, "file": str(out_path), "status": "generated"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST),
                    help=f"Path to sfx_manifest.json (default: {DEFAULT_MANIFEST})")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                    help=f"Where to write WAV files (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--force", action="store_true",
                    help="Regenerate even if file already exists")
    args = ap.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found. Install with:  brew install ffmpeg")

    manifest_path = Path(args.manifest).expanduser().resolve()
    if not manifest_path.exists():
        sys.exit(f"manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [synth(c, r, out_dir, args.force) for c, r in manifest["categories"].items()]
    failed = [r for r in results if r["status"] == "failed"]

    summary = {
        "out_dir": str(out_dir),
        "total": len(results),
        "generated": sum(1 for r in results if r["status"] == "generated"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "failed": len(failed),
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
