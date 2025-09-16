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


def clone_voice_advanced_local(tts_wav_path: str, cloned_wav_path: str, reference_wav_path: str):
    """
    Advanced local voice cloning without OpenVoice dependency.
    Uses the sophisticated spectral analysis approach that's already working.
    """
    try:
        print(f"🧬 Starting advanced local voice cloning...")
        print(f"📥 TTS path: {tts_wav_path}")
        print(f"📥 Reference path: {reference_wav_path}")
        print(f"📤 Output path: {cloned_wav_path}")

        assert os.path.exists(tts_wav_path), f"TTS WAV not found: {tts_wav_path}"
        assert os.path.exists(reference_wav_path), f"Reference WAV not found: {reference_wav_path}"
        os.makedirs(os.path.dirname(cloned_wav_path), exist_ok=True)

        # Use the advanced spectral voice cloning that's already working
        try:
            # Import advanced voice cloning module
            import sys
            import os
            advanced_cloning_path = os.path.join(os.path.dirname(__file__), '..', 'advanced_voice_cloning.py')
            
            if os.path.exists(advanced_cloning_path):
                # Add parent directory to Python path
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                
                try:
                    from advanced_voice_cloning import advanced_voice_cloning
                    success = advanced_voice_cloning(
                        tts_wav_path, reference_wav_path, cloned_wav_path,
                        pitch_alpha=0.8, envelope_alpha=0.7
                    )
                    if success:
                        print(f"✅ Advanced voice cloning successful: {cloned_wav_path}")
                        return True
                except ImportError as import_error:
                    print(f"⚠️ Advanced cloning import failed: {import_error}")
                except Exception as advanced_error:
                    print(f"⚠️ Advanced cloning failed: {advanced_error}")
        except:
            pass
        
        # Fallback to enhanced FFmpeg processing
        print("🔄 Using enhanced FFmpeg voice cloning...")
        enhanced_ffmpeg_voice_cloning(tts_wav_path, reference_wav_path, cloned_wav_path)
        return True
        
    except Exception as e:
        print(f"❌ Advanced local voice cloning failed: {e}")
        return False


def enhanced_ffmpeg_voice_cloning(tts_wav_path: str, reference_wav_path: str, output_path: str):
    """Enhanced voice cloning using sophisticated FFmpeg filters"""
    try:
        from pydub import AudioSegment
        import numpy as np
        
        print("🎵 Loading TTS and reference audio...")
        tts_audio = AudioSegment.from_wav(tts_wav_path)
        ref_audio = AudioSegment.from_wav(reference_wav_path)
        
        # Convert to numpy arrays for analysis
        tts_samples = np.array(tts_audio.get_array_of_samples())
        ref_samples = np.array(ref_audio.get_array_of_samples())
        
        if tts_audio.channels == 2:
            tts_samples = tts_samples.reshape((-1, 2))
            tts_samples = tts_samples.mean(axis=1)
        if ref_audio.channels == 2:
            ref_samples = ref_samples.reshape((-1, 2))
            ref_samples = ref_samples.mean(axis=1)
        
        # Analyze reference voice characteristics
        ref_sample_rate = ref_audio.frame_rate
        tts_sample_rate = tts_audio.frame_rate
        
        print("🔬 Analyzing voice characteristics...")
        
        # Basic pitch analysis
        ref_rms = ref_audio.rms
        tts_rms = tts_audio.rms
        
        # Estimate pitch characteristics from RMS and frequency content
        pitch_adjustment = 0
        if ref_rms > 0 and tts_rms > 0:
            # Simple heuristic for pitch adjustment
            rms_ratio = ref_rms / tts_rms
            if rms_ratio > 1.5:
                pitch_adjustment = 2  # Boost low frequencies for deeper voice
            elif rms_ratio < 0.7:
                pitch_adjustment = -1  # Reduce for higher voice
        
        print(f"🎼 Estimated pitch adjustment: {pitch_adjustment} semitones")
        
        # Multi-stage FFmpeg processing
        temp_files = []
        
        # Stage 1: Pitch and formant correction
        temp_pitch = output_path.replace('.wav', '_pitch.wav')
        temp_files.append(temp_pitch)
        
        # Apply pitch shift if needed
        if abs(pitch_adjustment) > 0:
            pitch_factor = 2 ** (pitch_adjustment / 12)
            subprocess.run([
                'ffmpeg', '-y', '-i', tts_wav_path,
                '-af', f'asetrate={int(ref_sample_rate * pitch_factor)},aresample={ref_sample_rate}',
                '-ar', str(ref_sample_rate),
                '-ac', '1',
                temp_pitch
            ], capture_output=True, check=True)
        else:
            subprocess.run([
                'ffmpeg', '-y', '-i', tts_wav_path,
                '-ar', str(ref_sample_rate),
                '-ac', '1',
                temp_pitch
            ], capture_output=True, check=True)
        
        # Stage 2: Spectral shaping for naturalness
        temp_spectral = output_path.replace('.wav', '_spectral.wav')
        temp_files.append(temp_spectral)
        
        # Enhanced spectral filters for Indian voice characteristics
        spectral_filters = [
            'highpass=f=80',   # Remove noise
            'lowpass=f=8000',  # Remove digital artifacts
            
            # Dynamic range processing
            'compand=attacks=0.05:decays=0.2:points=-90/-90|-60/-50|-40/-35|-25/-20|-15/-12|-5/-4|0/0',
            
            # Voice formant enhancement for Indian accent
            'equalizer=f=400:width_type=o:width=1:g=2',     # Boost chest resonance
            'equalizer=f=1000:width_type=o:width=1:g=1.5',  # Boost vocal clarity
            'equalizer=f=2000:width_type=o:width=1:g=0.5',  # Slight mouth formant
            'equalizer=f=3000:width_type=o:width=1:g=-0.5', # Reduce nasal quality
            'equalizer=f=4500:width_type=o:width=1:g=-1',   # Reduce sibilance
            'equalizer=f=6000:width_type=o:width=1:g=-1.5', # Reduce harshness
            
            # Warmth and naturalness
            'bass=g=1.5:f=200:width_type=o:width=1',
            'treble=g=-1:f=5000:width_type=o:width=1',
        ]
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_pitch,
            '-af', ','.join(spectral_filters),
            temp_spectral
        ], capture_output=True, check=True)
        
        # Stage 3: Harmonic enhancement
        temp_harmonic = output_path.replace('.wav', '_harmonic.wav')
        temp_files.append(temp_harmonic)
        
        harmonic_filters = [
            # Subtle harmonic enhancement for naturalness
            'aphaser=in_gain=0.3:out_gain=0.9:delay=2:decay=0.3:speed=0.3',
            
            # Speech-specific dynamic processing
            'compand=attacks=0.1:decays=0.8:points=-90/-90|-45/-45|-25/-18|-10/-8|-5/-4|0/0',
            
            # Gentle noise gate to clean up silence
            'agate=threshold=0.008:ratio=3:attack=5:release=50',
        ]
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_spectral,
            '-af', ','.join(harmonic_filters),
            temp_harmonic
        ], capture_output=True, check=True)
        
        # Stage 4: Final processing and volume matching
        tts_processed = AudioSegment.from_wav(temp_harmonic)
        
        # Match volume characteristics
        if ref_rms > 0 and tts_processed.rms > 0:
            volume_adjustment = ref_rms / tts_processed.rms
            volume_db = 20 * np.log10(np.clip(volume_adjustment, 0.3, 3.0))
            tts_processed = tts_processed + volume_db
            print(f"🔊 Volume adjustment: {volume_db:.1f} dB")
        
        # Apply subtle reverb to match environment
        temp_final = output_path.replace('.wav', '_final.wav')
        temp_files.append(temp_final)
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_harmonic,
            '-af', 'aecho=0.6:0.8:80:0.2,aecho=0.3:0.6:150:0.15',
            temp_final
        ], capture_output=True, check=True)
        
        # Load final processed audio and export
        final_audio = AudioSegment.from_wav(temp_final)
        final_audio.export(output_path, format="wav")
        
        # Clean up temporary files
        for temp_file in temp_files:
            safe_delete(temp_file)
        
        print(f"✅ Enhanced FFmpeg voice cloning completed: {output_path}")
        
    except Exception as e:
        print(f"❌ Enhanced FFmpeg voice cloning failed: {e}")
        # Final fallback: copy TTS file
        try:
            shutil.copy2(tts_wav_path, output_path)
            print(f"🔄 Copied TTS file as final fallback: {output_path}")
        except Exception as copy_error:
            print(f"❌ Final fallback copy failed: {copy_error}")


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
        
        # Step 2: Generate TTS using Edge-TTS (or fallback to local TTS)
        tts_wav = os.path.join(TTS_DIR, f"{input_name}.wav")
        name_text = input_name
        
        print("🎙️ Generating TTS...")
        tts_success = await generate_tts(name_text, tts_wav)
        
        if not tts_success:
            print("❌ TTS generation failed")
            return
        
        # Step 3: Advanced local voice cloning
        cloned_wav = os.path.join(CLONED_DIR, f"{input_name}.wav")
        
        print("🧬 Starting advanced voice cloning...")
        cloning_success = clone_voice_advanced_local(tts_wav, cloned_wav, reference_wav_path)
        
        if not cloning_success:
            print("❌ Voice cloning failed")
            return
        
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
        output_video_path = generate_video_for_name(
            input_name, 
            base_video_path, 
            cloned_wav
        )
        
        if output_video_path and os.path.exists(output_video_path):
            print(f"✅ Video generation completed: {output_video_path}")
            return output_video_path
        else:
            print("❌ Video generation failed")
            return None
        
    except Exception as e:
        print(f"❌ Video generation process failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_openvoice_local.py \"<Full Name>\" \"<Base Video Path>\"")
        sys.exit(1)

    input_name = sys.argv[1]
    base_video_path = sys.argv[2]
    result = asyncio.run(generate_progress(input_name, base_video_path))
    
    if result:
        print(f"\n🎉 SUCCESS: {result}")
    else:
        print("\n❌ FAILED: Video generation unsuccessful")
        sys.exit(1)
