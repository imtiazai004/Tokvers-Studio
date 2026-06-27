import asyncio
import os

async def _run_ffmpeg(*args):
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise Exception(f"FFmpeg error: {stderr.decode()}")
    return stdout.decode()

async def merge_video_clips(clip_paths: list[str], output_path: str) -> str:
    list_file = output_path.replace(".mp4", "_list.txt")
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    await _run_ffmpeg(
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    )
    os.remove(list_file)
    return output_path

async def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> str:
    await _run_ffmpeg(
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path
    )
    return output_path

async def burn_captions(video_path: str, srt_path: str, output_path: str) -> str:
    srt_abs = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
    await _run_ffmpeg(
        "-i", video_path,
        "-vf", f"subtitles={srt_abs}:force_style='FontSize=18,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Bold=1'",
        "-c:a", "copy",
        output_path
    )
    return output_path

async def add_background_music(video_path: str, music_path: str, output_path: str, music_volume: float = 0.15) -> str:
    await _run_ffmpeg(
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        f"[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path
    )
    return output_path

async def convert_to_tiktok_format(input_path: str, output_path: str) -> str:
    await _run_ffmpeg(
        "-i", input_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "copy",
        "-r", "30",
        output_path
    )
    return output_path
