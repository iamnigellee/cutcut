#!/usr/bin/env python3
"""Generate voiceover audio + SRT + sentence-time JSON from a text script.

Default engine is edge-tts (free, Chinese voices, word-level timing).

Usage:
    python3 tts.py <script.txt> <output_dir>
        [--voice zh-CN-YunjianNeural]
        [--rate +0%] [--volume +0%]

Output:
    <output_dir>/vo.mp3    — synthesized audio
    <output_dir>/vo.srt    — word-level subtitles (for in-app sub track)
    <output_dir>/vo.json   — sentence-level timing for downstream cut planning
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

DEFAULT_VOICE = "zh-CN-YunjianNeural"
SENTENCE_TERMINATORS = "。！？!?…\n"


def _load_edge_tts():
    try:
        import edge_tts  # noqa: F401
        return edge_tts
    except ImportError:
        sys.exit(
            "edge-tts is not installed.\n"
            "Install it with:  python3 -m pip install --user edge-tts"
        )


def split_sentences(text: str) -> list[str]:
    """Split text into sentences keeping the terminator punctuation."""
    out, buf = [], []
    for ch in text:
        buf.append(ch)
        if ch in SENTENCE_TERMINATORS:
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def write_srt(word_events: list[dict], path: Path) -> None:
    lines = []
    for i, w in enumerate(word_events, 1):
        start_s = w["offset_us"] / 1_000_000
        end_s = (w["offset_us"] + w["duration_us"]) / 1_000_000
        lines.append(
            f"{i}\n{_format_srt_time(start_s)} --> {_format_srt_time(end_s)}\n{w['text']}\n"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


async def _synth(script: str, out_mp3: Path, voice: str, rate: str, volume: str) -> list[dict]:
    edge_tts = _load_edge_tts()
    communicate = edge_tts.Communicate(script, voice=voice, rate=rate, volume=volume)
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    events: list[dict] = []
    with out_mp3.open("wb") as f:
        async for chunk in communicate.stream():
            t = chunk.get("type")
            if t == "audio":
                f.write(chunk["data"])
            elif t == "WordBoundary":
                # edge-tts emits offset/duration in 100ns ticks. Convert to us.
                events.append(
                    {
                        "text": chunk["text"],
                        "offset_us": int(chunk["offset"]) // 10,
                        "duration_us": int(chunk["duration"]) // 10,
                    }
                )
    return events


def map_sentences(sentences: list[str], events: list[dict]) -> list[dict]:
    """Walk word events and the script in lockstep to time-stamp each sentence."""
    flat: list[tuple[str, int]] = []
    for i, w in enumerate(events):
        for ch in w["text"]:
            flat.append((ch, i))

    cursor = 0
    out: list[dict] = []
    drop = re.compile(r"[\s。！？!?…，,、；;：:]")
    for s in sentences:
        s_clean = drop.sub("", s)
        start_idx = end_idx = None
        matched = 0
        while cursor < len(flat) and matched < len(s_clean):
            ch, w_idx = flat[cursor]
            if ch == s_clean[matched]:
                if start_idx is None:
                    start_idx = w_idx
                end_idx = w_idx
                matched += 1
            cursor += 1
        if start_idx is not None and end_idx is not None:
            start_us = events[start_idx]["offset_us"]
            end_us = events[end_idx]["offset_us"] + events[end_idx]["duration_us"]
        else:
            start_us = end_us = 0
        out.append(
            {
                "text": s,
                "start_us": start_us,
                "end_us": end_us,
                "duration_us": max(0, end_us - start_us),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("script", help="Path to a UTF-8 text file holding the narration")
    ap.add_argument("output_dir", help="Directory to write vo.mp3 / vo.srt / vo.json")
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                    help=f"edge-tts voice ID (default: {DEFAULT_VOICE})")
    ap.add_argument("--rate", default="+0%",
                    help="Speech rate, e.g. -10%% / +5%% (default: +0%%)")
    ap.add_argument("--volume", default="+0%",
                    help="Output volume, e.g. +0%% (default: +0%%)")
    args = ap.parse_args()

    script_path = Path(args.script).expanduser().resolve()
    script_text = script_path.read_text(encoding="utf-8").strip()
    if not script_text:
        sys.exit(f"script is empty: {script_path}")

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp3 = out_dir / "vo.mp3"
    out_srt = out_dir / "vo.srt"
    out_json = out_dir / "vo.json"

    events = asyncio.run(_synth(script_text, out_mp3, args.voice, args.rate, args.volume))
    if not events:
        sys.exit("edge-tts returned no audio. Check the voice ID and network.")

    write_srt(events, out_srt)

    sentences = split_sentences(script_text)
    sent_times = map_sentences(sentences, events)
    total_us = max((s["end_us"] for s in sent_times), default=0)

    out_json.write_text(
        json.dumps(
            {
                "voice": args.voice,
                "rate": args.rate,
                "duration_us": total_us,
                "duration_s": round(total_us / 1_000_000, 3),
                "sentences": sent_times,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "vo_mp3": str(out_mp3),
                "vo_srt": str(out_srt),
                "vo_json": str(out_json),
                "duration_s": round(total_us / 1_000_000, 3),
                "sentence_count": len(sent_times),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
