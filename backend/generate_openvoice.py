import sys
import io
import os
import asyncio
import subprocess
import json
import uuid
import ssl
import aiohttp
from generate_video import generate_video_for_name
from word_trimming import trim_audio_by_word, transcribe_audio
import edge_tts
import shutil

# Disable SSL verification globally for edge_tts
ssl._create_default_https_context = ssl._create_unverified_context

# UTF-8 stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# === Unique run ID for parallel safety ===
RUN_ID = f"{os.getpid()}_{uuid.uuid4().hex[:6]}"

# === Constants & Directories (process-specific) ===
BASE_UPLOAD_DIR = "uploads"
BASE_VIDEO_DIR = "generated_videos"
BASE_TTS_DIR = "tts"
BASE_CLONED_DIR = "cloned_voices"
BASE_REFERENCE_AUDIO_DIR = "voice_reference"

UPLOAD_DIR = os.path.join(BASE_UPLOAD_DIR, RUN_ID)
VIDEO_DIR = os.path.join(BASE_VIDEO_DIR, RUN_ID)
TTS_DIR = os.path.join(BASE_TTS_DIR, RUN_ID)
CLONED_DIR = os.path.join(BASE_CLONED_DIR, RUN_ID)
REFERENCE_AUDIO_DIR = os.path.join(BASE_REFERENCE_AUDIO_DIR, RUN_ID)

LANGUAGE = "mr"
LANGUAGE_VOICE = "hi-IN-MadhurNeural"
MESSAGE_TEMPLATE = "नमस्कार {name} नमस्कार {name} तुमचं स्वागत आहे {name} तुमचं स्वागत आहे {name}"

# OpenVoice configuration
OPENVOICE_DIR = r"C:\AtulDevelopment\AbhiyanAI\Git\AbhiyaanAI\backend\AbhiyanAI\AbhiyanAI.VideoWorkerService\backend\openvoice"

# Create all required folders
for directory in [UPLOAD_DIR, VIDEO_DIR, TTS_DIR, CLONED_DIR, REFERENCE_AUDIO_DIR]:
    os.makedirs(directory, exist_ok=True)


def safe_delete(path: str):
    """Delete a file safely if it exists."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑 Deleted temporary file: {path}")
    except Exception as e:
        print(f"⚠ Could not delete {path}: {e}")


def extract_reference_audio(video_path: str, output_wav_path: str):
    """
    Extracts audio from base video and converts it to WAV format (24kHz mono PCM).
    Normalizes first to 44.1kHz stereo to standardize quality.
    """
    try:
        temp_normalized = f"temp_normalized_audio_{RUN_ID}.wav"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            temp_normalized
        ], check=True)

        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_normalized,
            "-ar", "24000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_wav_path
        ], check=True)

        safe_delete(temp_normalized)
        print(f"✅ Reference voice extracted: {output_wav_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to extract reference voice: {e}")


async def generate_tts(text: str, file_path: str):
    """Generate TTS using Edge-TTS with Hindi voice optimized for Marathi names"""
    try:
        print(f"🎤 Generating TTS for: {text}")
        
        # Use Hindi voice which can pronounce Marathi names better
        voice = LANGUAGE_VOICE
        
        communicate = edge_tts.Communicate(text, voice)
        
        # Generate to MP3 first (Edge-TTS default)
        temp_mp3 = file_path.replace('.wav', '_temp.mp3')
        await communicate.save(temp_mp3)
        
        # Convert MP3 to WAV using ffmpeg for better quality and compatibility
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_mp3,
            '-ar', '24000',  # 24kHz sample rate to match reference
            '-ac', '1',      # Mono
            '-c:a', 'pcm_s16le',  # 16-bit PCM
            file_path
        ], check=True, capture_output=True)
        
        # Clean up temporary MP3
        safe_delete(temp_mp3)
        
        print(f"✅ TTS generated: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")
        return False


async def generate_openvoice_tts(text: str, file_path: str, reference_wav_path: str):
    """
    Generate speech using OpenVoice TTS with voice cloning.
    This uses the reference voice to generate TTS directly.
    """
    try:
        print(f"🧬 Generating OpenVoice TTS for: {text}")
        print(f"📁 Using reference: {reference_wav_path}")
        
        # Ensure OpenVoice directory exists
        if not os.path.exists(OPENVOICE_DIR):
            print(f"❌ OpenVoice directory not found: {OPENVOICE_DIR}")
            return False
        
        # Set environment for offline operation
        env = os.environ.copy()
        env.update({
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',
            'SSL_VERIFY': '0',
            'PYTHONHTTPSVERIFY': '0',
            'HF_HUB_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1',
            'PYTORCH_TRANSFORMERS_CACHE': os.path.join(OPENVOICE_DIR, 'cache'),
            'HF_HOME': os.path.join(OPENVOICE_DIR, 'hf_cache')
        })
        
        # Try OpenVoice CLI for TTS generation with voice cloning
        try:
            result = subprocess.run([
                sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{OPENVOICE_DIR}')
from api import BaseSpeakerTTS, ToneColorConverter

# Initialize TTS
base_speaker_tts = BaseSpeakerTTS('{OPENVOICE_DIR}/checkpoints/base_speakers/EN')
tone_color_converter = ToneColorConverter('{OPENVOICE_DIR}/checkpoints/converter')

# Generate base TTS
base_speaker_tts.tts('{text}', '{file_path}', speaker='default', language='English')

# Apply voice conversion using reference
tone_color_converter.convert(
    audio_src_path='{file_path}',
    src_se='{OPENVOICE_DIR}/checkpoints/base_speakers/EN/en_default_se.pth',
    tgt_se='{reference_wav_path}',
    output_path='{file_path}'
)
print('✅ OpenVoice TTS with cloning completed')
"""], 
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ OpenVoice TTS generated successfully: {file_path}")
                return True
            else:
                print(f"❌ OpenVoice TTS failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ OpenVoice TTS timed out")
            return False
            
    except Exception as e:
        print(f"❌ OpenVoice TTS failed: {e}")
        return False


def clone_voice_openvoice(tts_wav_path: str, cloned_wav_path: str, reference_wav_path: str):
    """Clone voice using OpenVoice - main cloning function"""
    try:
        print(f"🧬 Starting OpenVoice cloning...")
        print(f"📥 TTS path: {tts_wav_path}")
        print(f"📥 Reference path: {reference_wav_path}")
        print(f"📤 Output path: {cloned_wav_path}")

        assert os.path.exists(tts_wav_path), f"TTS WAV not found: {tts_wav_path}"
        assert os.path.exists(reference_wav_path), f"Reference WAV not found: {reference_wav_path}"
        os.makedirs(os.path.dirname(cloned_wav_path), exist_ok=True)

        # Ensure OpenVoice directory exists
        if not os.path.exists(OPENVOICE_DIR):
            print(f"❌ OpenVoice directory not found: {OPENVOICE_DIR}")
            return False

        # Set environment for offline operation
        env = os.environ.copy()
        env.update({
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',
            'SSL_VERIFY': '0',
            'PYTHONHTTPSVERIFY': '0',
            'HF_HUB_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1',
            'PYTORCH_TRANSFORMERS_CACHE': os.path.join(OPENVOICE_DIR, 'cache'),
            'HF_HOME': os.path.join(OPENVOICE_DIR, 'hf_cache')
        })

        # Method 1: Try OpenVoice CLI
        try:
            print("🔄 Trying OpenVoice CLI...")
            result = subprocess.run([
                sys.executable, "-m", "openvoice_cli", "single",
                "-i", tts_wav_path,
                "-r", reference_wav_path,
                "-o", cloned_wav_path
            ], env=env, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(cloned_wav_path):
                print(f"✅ OpenVoice CLI cloning successful: {cloned_wav_path}")
                return True
            else:
                print(f"❌ OpenVoice CLI failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("❌ OpenVoice CLI timed out")
        except Exception as cli_error:
            print(f"❌ OpenVoice CLI error: {cli_error}")

        # Method 2: Try OpenVoice API directly
        try:
            print("🔄 Trying OpenVoice API directly...")
            result = subprocess.run([
                sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{OPENVOICE_DIR}')
import torch
from api import ToneColorConverter

# Initialize converter
converter = ToneColorConverter('{OPENVOICE_DIR}/checkpoints/converter')

# Load source and target speaker embeddings
src_path = '{tts_wav_path}'
tgt_path = '{reference_wav_path}'
output_path = '{cloned_wav_path}'

print(f'Loading source audio: {{src_path}}')
print(f'Loading target reference: {{tgt_path}}')

# Convert voice
converter.convert(
    audio_src_path=src_path,
    src_se=None,  # Will be computed from source
    tgt_se=tgt_path,  # Target speaker embedding from reference
    output_path=output_path,
    message='Converting voice...'
)
print('✅ OpenVoice API conversion completed')
"""], 
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=120
            )
            
            if result.returncode == 0 and os.path.exists(cloned_wav_path):
                print(f"✅ OpenVoice API cloning successful: {cloned_wav_path}")
                return True
            else:
                print(f"❌ OpenVoice API failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("❌ OpenVoice API timed out")
        except Exception as api_error:
            print(f"❌ OpenVoice API error: {api_error}")

        # Method 3: Try alternative OpenVoice approach
        try:
            print("🔄 Trying alternative OpenVoice approach...")
            result = subprocess.run([
                sys.executable, "-c", f"""
import sys
import os
sys.path.insert(0, '{OPENVOICE_DIR}')

try:
    import torch
    from openvoice import se_extractor
    from openvoice.api import ToneColorConverter
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f'Using device: {{device}}')
    
    # Initialize model
    ckpt_converter = '{OPENVOICE_DIR}/checkpoints/converter'
    converter = ToneColorConverter(ckpt_converter, device=device)
    
    # Extract speaker embeddings
    target_se, audio_name = se_extractor.get_se('{reference_wav_path}', converter, target_dir='temp', vad=True)
    
    # Convert voice
    converter.convert(
        audio_src_path='{tts_wav_path}',
        src_se=None,
        tgt_se=target_se, 
        output_path='{cloned_wav_path}',
        message="Voice conversion"
    )
    print('✅ Alternative OpenVoice conversion completed')
    
except Exception as e:
    print(f'❌ Alternative approach failed: {{e}}')
    import traceback
    traceback.print_exc()
"""], 
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=180
            )
            
            if result.returncode == 0 and os.path.exists(cloned_wav_path):
                print(f"✅ Alternative OpenVoice cloning successful: {cloned_wav_path}")
                return True
            else:
                print(f"❌ Alternative OpenVoice failed: {result.stderr}")
                print(f"❌ Alternative OpenVoice stdout: {result.stdout}")
                
        except Exception as alt_error:
            print(f"❌ Alternative OpenVoice error: {alt_error}")

        return False

    except Exception as e:
        print(f"❌ OpenVoice cloning failed: {e}")
        return False


def clone_voice_fallback(tts_wav_path: str, cloned_wav_path: str, reference_wav_path: str):
    """Fallback voice cloning using basic audio processing when OpenVoice fails"""
    try:
        print("🔄 Using fallback voice processing...")
        
        # Basic audio processing using ffmpeg
        subprocess.run([
            'ffmpeg', '-y',
            '-i', tts_wav_path,
            '-af', 'equalizer=f=1000:width_type=o:width=2:g=3,compand=attacks=0.1:decays=0.2:points=-90/-90|-70/-60|-40/-40|-20/-20|0/0',
            '-ar', '24000',
            '-ac', '1',
            cloned_wav_path
        ], check=True, capture_output=True)
        
        print(f"✅ Fallback voice processing completed: {cloned_wav_path}")
        return True
        
    except Exception as e:
        print(f"❌ Fallback processing failed: {e}")
        # Final fallback: copy original TTS
        try:
            shutil.copy2(tts_wav_path, cloned_wav_path)
            print(f"🔄 Copied TTS as final fallback: {cloned_wav_path}")
            return True
        except Exception as copy_error:
            print(f"❌ Final fallback copy failed: {copy_error}")
            return False


async def generate_progress(input_name: str, base_video_path: str):
    """Main function to generate personalized video with voice cloning"""
    try:
        print(f"🚀 Starting video generation for: {input_name}")
        print(f"📹 Base video: {base_video_path}")
        
        # Step 1: Extract reference audio from base video
        reference_wav_path = os.path.join(REFERENCE_AUDIO_DIR, f"{input_name}_{RUN_ID}_reference.wav")
        print("🎤 Extracting reference audio from base video...")
        extract_reference_audio(base_video_path, reference_wav_path)
        
        if not os.path.exists(reference_wav_path):
            print("❌ Failed to extract reference audio")
            return
        
        # Step 2: Generate TTS - Try OpenVoice TTS first
        tts_wav = os.path.join(TTS_DIR, f"{input_name}.wav")
        name_text = input_name
        
        print("🎙️ Attempting OpenVoice TTS with voice cloning...")
        tts_success = await generate_openvoice_tts(name_text, tts_wav, reference_wav_path)
        
        if not tts_success:
            print("🔄 OpenVoice TTS failed, falling back to Edge-TTS...")
            tts_success = await generate_tts(name_text, tts_wav)
            
            if not tts_success:
                print("❌ All TTS methods failed")
                return
        
        # Step 3: Voice cloning (if using Edge-TTS)
        cloned_wav = os.path.join(CLONED_DIR, f"{input_name}.wav")
        
        if tts_success and not await generate_openvoice_tts(name_text, tts_wav, reference_wav_path):
            # We used Edge-TTS, so we need to clone the voice
            print("🧬 Starting voice cloning process...")
            
            cloning_success = clone_voice_openvoice(tts_wav, cloned_wav, reference_wav_path)
            
            if not cloning_success:
                print("🔄 OpenVoice cloning failed, using fallback...")
                cloning_success = clone_voice_fallback(tts_wav, cloned_wav, reference_wav_path)
                
            if not cloning_success:
                print("❌ All voice cloning methods failed")
                return
        else:
            # OpenVoice TTS succeeded, use it directly
            cloned_wav = tts_wav
        
        # Step 4: Detect silence in base video for name insertion
        print("🔍 Analyzing base video for silent segments...")
        
        # Use word_trimming to find silent segments
        transcript_result = transcribe_audio(base_video_path)
        if not transcript_result:
            print("❌ Failed to transcribe base video")
            return
        
        segments, full_transcript = transcript_result
        
        # Find a suitable silent gap (longer than 1.5 seconds)
        silent_segments = []
        for i in range(len(segments) - 1):
            current_end = segments[i]['end']
            next_start = segments[i + 1]['start'] 
            gap_duration = next_start - current_end
            
            if gap_duration >= 1.5:  # At least 1.5 seconds of silence
                silent_segments.append({
                    'start': current_end,
                    'end': next_start,
                    'duration': gap_duration
                })
        
        if not silent_segments:
            print("⚠️ No suitable silent segments found, using end of video")
            # Get video duration and insert at the end
            probe_result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', base_video_path
            ], capture_output=True, text=True, check=True)
            video_duration = float(probe_result.stdout.strip())
            insert_time = video_duration - 0.5  # Insert 0.5 seconds before end
        else:
            # Use the first suitable silent segment
            chosen_segment = silent_segments[0]
            insert_time = chosen_segment['start'] + 0.2  # Insert 0.2 seconds into the silence
            print(f"📍 Found silent segment: {chosen_segment['start']:.2f}s - {chosen_segment['end']:.2f}s")
        
        print(f"⏰ Inserting name at time: {insert_time:.2f}s")
        
        # Step 5: Generate the final video
        print("🎬 Generating final video...")
        output_video_path = await generate_video_for_name(
            input_name, 
            base_video_path, 
            cloned_wav, 
            insert_time
        )
        
        if output_video_path and os.path.exists(output_video_path):
            print(f"✅ Video generation completed: {output_video_path}")
            
            # Clean up temporary files
            safe_delete(reference_wav_path)
            if tts_wav != cloned_wav:  # Only delete if they're different files
                safe_delete(tts_wav)
            safe_delete(cloned_wav)
            
        else:
            print("❌ Video generation failed")
        
    except Exception as e:
        print(f"❌ Video generation process failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate.py \"<Full Name>\" \"<Base Video Path>\"")
        sys.exit(1)

    input_name = sys.argv[1]
    base_video_path = sys.argv[2]
    asyncio.run(generate_progress(input_name, base_video_path))
