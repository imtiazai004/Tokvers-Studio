import asyncio
import os

async def generate_captions(audio_path: str, output_srt: str) -> str:
    os.makedirs(os.path.dirname(output_srt) if os.path.dirname(output_srt) else ".", exist_ok=True)

    loop = asyncio.get_event_loop()

    def _transcribe():
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, task="transcribe")
        return result

    result = await loop.run_in_executor(None, _transcribe)

    srt_content = _to_srt(result["segments"])
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return output_srt

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
