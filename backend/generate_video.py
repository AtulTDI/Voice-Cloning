from moviepy.editor import VideoFileClip, AudioFileClip
from pydub import AudioSegment
from pydub.silence import detect_silence
import os
import pandas as pd
import glob
import time

#TTS_DIR = "cloned_voices"
OUTPUT_DIR = "generated_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_video_for_name(name: str, basevideo: str, trimmed_path : str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # # === 1. Find latest trimmed audio for this name ===
    # trimmed_pattern = os.path.join(TTS_DIR, f"{name}_trimmed_*.wav")
    # trimmed_files = glob.glob(trimmed_pattern)
    # if not trimmed_files:
    #     raise FileNotFoundError(f"❌ No trimmed voice found for: {name}")
    # tts_path = max(trimmed_files, key=os.path.getctime)  # latest one
    print(f"trimmed_path: {trimmed_path}")
    ##tts_path = os.path.join(trimmed_path)
    # === 2. Load custom voice ===
    custom_voice = AudioSegment.from_file(trimmed_path).set_channels(2).set_frame_rate(44100)

    # === 3. Load base video & audio ===
    base_video = VideoFileClip(basevideo)
    timestamp = int(time.time() * 1000)
    base_audio_path = os.path.join(OUTPUT_DIR, f"{name}_original_audio_{timestamp}.mp3")
    base_video.audio.write_audiofile(base_audio_path, fps=44100)

    original_audio = AudioSegment.from_file(base_audio_path)

    # === 4. Detect silence ===
    silence_thresh = original_audio.dBFS - 16
    silent_segments = detect_silence(original_audio, min_silence_len=500, silence_thresh=silence_thresh)
    if not silent_segments:
        raise Exception("No silent region found in base audio!")

    silent_segments = [seg for seg in silent_segments if seg[0] > 500]
    start_ms, _ = silent_segments[0]
    start_ms += 500
    print(f"Detected silent segment starting at: {start_ms}ms")

    # === 5. Normalize & crossfade ===
    target_dbfs = original_audio.dBFS
    gain = (target_dbfs - custom_voice.dBFS) + 3
    replacement_voice = custom_voice.apply_gain(gain)

    CROSSFADE_MS = 200
    before = original_audio[:start_ms]
    after = original_audio[start_ms + len(replacement_voice):]

    modified_audio = before.append(replacement_voice, crossfade=CROSSFADE_MS)\
                            .append(after, crossfade=CROSSFADE_MS)

    # === 6. Save modified audio ===
    final_audio_path = os.path.join(OUTPUT_DIR, f"{name}_final_audio_{timestamp}.mp3")
    modified_audio.export(final_audio_path, format="mp3")

    # === 7. Attach to video ===
    final_audio_clip = AudioFileClip(final_audio_path)
    final_video_path = os.path.join(OUTPUT_DIR, f"{name}_{timestamp}.mp4")
    final_video = base_video.set_audio(final_audio_clip)
    final_video.write_videofile(
        final_video_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(OUTPUT_DIR, f"{name}_temp_audio_{timestamp}.m4a"),
        remove_temp=True,
        fps=24
    )

    # === 8. Cleanup ===
    base_video.close()
    final_audio_clip.close()
    os.remove(base_audio_path)
    os.remove(final_audio_path)

    print(f"✅ Generated video for {name}: {final_video_path}")
    print(final_video_path, flush=True)  # ✅ Ensure .NET sees it
    return final_video_path

def process_excel(file_path: str):
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        name = str(row["Name"]).strip()
        print(f"🎬 Generating video for: {name}")
        generate_video_for_name(name)