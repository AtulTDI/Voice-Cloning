import sys
import os
sys.path.append(os.path.abspath("openvoice"))
from openvoice.api import infer_voice
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import shutil
import os
import time
import json
import pandas as pd
import zipfile
import asyncio
import subprocess
import edge_tts
from generate_video import generate_video_for_name

  # if you refactor API logic

# For direct call via C#
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python generate_video.py \"Name Here\"")
        sys.exit(1)

    name = sys.argv[1]
    asyncio.run(generate_progress(name))

# === FastAPI App ===
app = FastAPI()

# === CORS Config ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Constants & Directories ===
UPLOAD_DIR = "uploads"
VIDEO_DIR = "generated_videos"
TTS_DIR = "tts"
CLONED_DIR = "cloned_voices"
REFERENCE_AUDIO = "voice_reference/reference.wav"
LANGUAGE_VOICE = "hi-IN-MadhurNeural"
MESSAGE_TEMPLATE = "{name}, SpeakNShare में आपका स्वागत है। मैं आपकी मदद के लिए यहां हूं।"

for directory in [UPLOAD_DIR, VIDEO_DIR, TTS_DIR, CLONED_DIR]:
    os.makedirs(directory, exist_ok=True)

uploaded_excel = ""

def extract_reference_audio(video_path: str, output_wav_path: str):
    """
    Extracts audio from base video and converts it to WAV format (24kHz mono PCM).
    """
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-ar", "24000",        # 24kHz
            "-ac", "1",            # Mono
            "-c:a", "pcm_s16le",   # PCM format
            output_wav_path
        ], check=True)
        print(f"✅ Reference voice extracted: {output_wav_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to extract reference voice: {e}")

# === 1. Generate TTS Audio using Edge-TTS ===
async def generate_tts(text: str, file_path: str):
    voice = LANGUAGE_VOICE
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(file_path)
        print(f"✅ TTS saved: {file_path}")
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")

# === 2. Clone voice using openvoice_cli ===
# def clone_voice(tts_wav_path: str, cloned_wav_path: str):
#     try:
#         subprocess.run([
#             "python", "openvoice/openvoice/api.py", "infer",
#             "-i", tts_wav_path,
#             "-r", REFERENCE_AUDIO,
#             "-o", cloned_wav_path
#         ], check=True)
#         print(f"✅ Cloned voice saved: {cloned_wav_path}")
#     except subprocess.CalledProcessError as e:
#         print(f"❌ Voice cloning failed: {e}")
def clone_voice(tts_wav_path: str, cloned_wav_path: str):
    try:
        print(f"📥 TTS WAV path: {tts_wav_path}")
        print(f"📥 Reference voice path: {REFERENCE_AUDIO}")
        print(f"📤 Output path: {cloned_wav_path}")

        assert os.path.exists(tts_wav_path), f"TTS WAV not found at: {tts_wav_path}"
        assert os.path.exists(REFERENCE_AUDIO), f"Reference voice not found at: {REFERENCE_AUDIO}"
        os.makedirs(os.path.dirname(cloned_wav_path), exist_ok=True)

        infer_voice(tts_wav_path, REFERENCE_AUDIO, cloned_wav_path)

        print(f"✅ Cloned voice saved: {cloned_wav_path}")
    except Exception as e:
        print(f"❌ Voice cloning failed: {e}")

# === 3. Upload Excel ===
@app.post("/start-generation")
def start_generation(file: UploadFile = File(...)):
    global uploaded_excel
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    uploaded_excel = file_path

    df = pd.read_excel(uploaded_excel)
    names = df["Name"].dropna().astype(str).tolist()
    return {"status": "started", "names": names}

# === 4. Stream Progress (TTS + Cloning + Video) ===
# @app.get("/generate-progress")
# async def generate_progress():
#     async def event_stream():
#         # Step 0: Generate reference.wav from base video if not already done
#         if not os.path.exists(REFERENCE_AUDIO):
#             extract_reference_audio("templates/base_video.mp4", REFERENCE_AUDIO)

#         df = pd.read_excel(uploaded_excel)
#         total = len(df)

#         for idx, row in df.iterrows():
#             name = str(row["Name"]).strip()
#             safe_name = name.replace(" ", "_")

#             tts_mp3 = os.path.join(TTS_DIR, f"{safe_name}.mp3")
#             tts_wav = os.path.join(TTS_DIR, f"{safe_name}.wav")
#             cloned_wav = os.path.join(CLONED_DIR, f"{safe_name}.wav")

#             # Step 1: Generate TTS
#             message = MESSAGE_TEMPLATE.format(name=name)
#             await generate_tts(message, tts_mp3)

#             # Step 2: Convert MP3 to WAV
#             os.system(f"ffmpeg -y -i \"{tts_mp3}\" \"{tts_wav}\"")

#             # Step 3: Clone Voice
#             clone_voice(tts_wav, cloned_wav)

#             # Step 4: Generate Final Video
#             generate_video_for_name(safe_name)

#             yield f"data: {json.dumps({'current': idx + 1, 'total': total, 'name': name})}\n\n"
#             await asyncio.sleep(0.1)

#     return StreamingResponse(event_stream(), media_type="text/event-stream")

async def generate_progress(name: str):
    async def event_stream():
        # Step 0: Ensure reference.wav is generated once
        if not os.path.exists(REFERENCE_AUDIO):
            extract_reference_audio("templates/base_video.mp4", REFERENCE_AUDIO)

        safe_name = name.strip().replace(" ", "_")
        tts_mp3 = os.path.join(TTS_DIR, f"{safe_name}.mp3")
        tts_wav = os.path.join(TTS_DIR, f"{safe_name}.wav")
        cloned_wav = os.path.join(CLONED_DIR, f"{safe_name}.wav")

        # Step 1: Generate TTS
        message = MESSAGE_TEMPLATE.format(name=name)
        await generate_tts(message, tts_mp3)
        yield f"data: {json.dumps({'step': 'TTS Generated', 'name': name})}\n\n"

        # Step 2: Convert MP3 to WAV
        os.system(f"ffmpeg -y -i \"{tts_mp3}\" \"{tts_wav}\"")
        yield f"data: {json.dumps({'step': 'Converted to WAV', 'name': name})}\n\n"

        # Step 3: Clone Voice
        clone_voice(tts_wav, cloned_wav)
        yield f"data: {json.dumps({'step': 'Voice Cloned', 'name': name})}\n\n"

        # Step 4: Generate Final Video
        generate_video_for_name(safe_name)
        yield f"data: {json.dumps({'step': 'Video Generated', 'name': name})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

    

# === 5. Download Individual Video ===
@app.get("/download/{name}")
def download_individual(name: str):
    file_path = os.path.join(VIDEO_DIR, f"{name}.mp4")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=f"{name}.mp4")
    return JSONResponse(status_code=404, content={"message": "File not found"})

# === 6. Download All Videos as ZIP ===
@app.get("/download-all")
def download_all():
    zip_path = "generated_videos.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in os.listdir(VIDEO_DIR):
            zipf.write(os.path.join(VIDEO_DIR, file), arcname=file)
    return FileResponse(zip_path, media_type="application/zip", filename="all_videos.zip")

# === 7. List All Videos ===
@app.get("/videos")
def list_videos():
    return [f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")]

# === 8. WhatsApp Link for Single Video ===
@app.get("/whatsapp-link/{name}")
def whatsapp_link(name: str):
    video_url = f"http://localhost:8000/download/{name}"
    message = f"📹 Here's your personalized video: {video_url}"
    wa_url = f"https://wa.me/?text={message}"
    return {"url": wa_url}

# === 9. WhatsApp Link for All Videos ===
@app.get("/whatsapp-link-all")
def whatsapp_link_all():
    links = []
    for filename in os.listdir(VIDEO_DIR):
        if filename.endswith(".mp4"):
            name = os.path.splitext(filename)[0]
            link = f"http://localhost:8000/download/{name}"
            links.append(f"📹 {name}: {link}")
    message = "\n".join(links)
    wa_url = f"https://wa.me/?text={message}"
    return {"url": wa_url}