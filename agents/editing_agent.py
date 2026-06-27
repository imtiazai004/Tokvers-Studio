import os
from tools.ffmpeg_tool import (
    merge_video_clips,
    add_audio_to_video,
    burn_captions,
    add_background_music,
    convert_to_tiktok_format
)
from tools.whisper_tool import generate_captions

MUSIC_DIR = "assets/music"

async def run_editing_agent(video_paths: list[str], audio_path: str, job_id: str) -> dict:
    output_base = f"output/videos/{job_id}"
    os.makedirs(output_base, exist_ok=True)

    merged_path = f"{output_base}/merged.mp4"
    await merge_video_clips(video_paths, merged_path)

    with_voice_path = f"{output_base}/with_voice.mp4"
    await add_audio_to_video(merged_path, audio_path, with_voice_path)

    srt_path = f"{output_base}/captions.srt"
    await generate_captions(audio_path, srt_path)

    with_captions_path = f"{output_base}/with_captions.mp4"
    await burn_captions(with_voice_path, srt_path, with_captions_path)

    final_input = with_captions_path
    music_file = _find_music()
    if music_file:
        with_music_path = f"{output_base}/with_music.mp4"
        await add_background_music(with_captions_path, music_file, with_music_path)
        final_input = with_music_path

    final_path = f"{output_base}/final_tiktok.mp4"
    await convert_to_tiktok_format(final_input, final_path)

    return {
        "final_video": final_path,
        "captions_file": srt_path,
        "job_id": job_id
    }

def _find_music() -> str | None:
    if not os.path.exists(MUSIC_DIR):
        return None
    for f in os.listdir(MUSIC_DIR):
        if f.endswith((".mp3", ".wav", ".m4a")):
            return os.path.join(MUSIC_DIR, f)
    return None
