"""
Caption generation via Deepgram's hosted speech-to-text API.

Kept the module name + `generate_captions(audio_path, output_srt)` signature so
the editing agent does not need to change. Previously this ran Whisper locally
(heavy CPU/RAM); now transcription happens on Deepgram for better accuracy and a
much lighter server.
"""
import os
import httpx
from config.client_config import get_key

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def generate_captions(audio_path: str, output_srt: str) -> str:
    out_dir = os.path.dirname(output_srt)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Priority: user's Settings key -> DEEPGRAM_API_KEY env fallback
    api_key = get_key("deepgram_api_key")
    if not api_key:
        raise RuntimeError("Deepgram API key is not set — add it in Settings (or DEEPGRAM_API_KEY env).")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    params = {
        "model": "nova-2",
        "smart_format": "true",
        "punctuate": "true",
        "utterances": "true",
    }
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": _content_type(audio_path),
    }

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(DEEPGRAM_URL, params=params, headers=headers, content=audio_bytes)
        resp.raise_for_status()
        data = resp.json()

    segments = _extract_segments(data)
    srt_content = _to_srt(segments)
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return output_srt


def _content_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
        ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac",
    }.get(ext, "audio/mpeg")


def _extract_segments(data: dict) -> list:
    results = data.get("results", {})

    # Preferred: utterance-level segments (natural caption lines).
    utterances = results.get("utterances") or []
    if utterances:
        return [
            {"start": u["start"], "end": u["end"], "text": u.get("transcript", "")}
            for u in utterances if u.get("transcript", "").strip()
        ]

    # Fallback: group words into short lines (~7 words each).
    try:
        words = results["channels"][0]["alternatives"][0].get("words", [])
    except (KeyError, IndexError):
        words = []

    segments, chunk = [], []
    for w in words:
        chunk.append(w)
        if len(chunk) >= 7:
            segments.append(_chunk_to_segment(chunk))
            chunk = []
    if chunk:
        segments.append(_chunk_to_segment(chunk))
    return segments


def _chunk_to_segment(chunk: list) -> dict:
    return {
        "start": chunk[0]["start"],
        "end": chunk[-1]["end"],
        "text": " ".join(w.get("punctuated_word", w.get("word", "")) for w in chunk),
    }


def _to_srt(segments: list) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_time(seg["start"])
        end = _format_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
