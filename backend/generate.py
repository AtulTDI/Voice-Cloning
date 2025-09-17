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

async def generate_tts(text: str, file_path: str, voice_gender="male"):
    """Generate speech using existing voice samples and text manipulation"""
    try:
        # Define available voice samples
        voice_samples = {
            "male": ["Amol_Adkitee.wav", "Atul_Kadam.wav", "Atul_Patil.wav"],
            "female": []  # Add female voice samples here if available
        }
        
        # Select voice sample based on gender preference
        available_voices = voice_samples.get(voice_gender, voice_samples["male"])
        if not available_voices:
            available_voices = voice_samples["male"]  # Fallback to male voices
        
        # Try multiple voice samples until we find one that exists
        reference_voice = None
        for voice in available_voices:
            voice_paths = [
                f"tts/{voice}",  # Look in tts folder
                voice,  # Look in current directory
                f"backend/tts/{voice}",  # Look in backend/tts folder
            ]
            
            # Also try .mp3 version
            if voice.endswith('.wav'):
                mp3_voice = voice.replace('.wav', '.mp3')
                voice_paths.extend([
                    f"tts/{mp3_voice}",
                    mp3_voice,
                    f"backend/tts/{mp3_voice}"
                ])
            
            for path in voice_paths:
                if os.path.exists(path):
                    reference_voice = path
                    break
            
            if reference_voice:
                break
        
        if not reference_voice:
            print(f"⚠ No reference voice samples found in: {available_voices}")
            print("🔄 Creating silence as fallback...")
            await create_silence_audio(file_path, duration=3)
            return
        
        print(f"🎤 Using voice reference: {reference_voice}")
        print(f"📝 Text to synthesize: {text}")
        
        # Use our custom TTS function
        create_tts_from_voice_sample(text, reference_voice, file_path)
        
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")
        print("🔄 Creating silence as fallback...")
        await create_silence_audio(file_path, duration=2)



OPENVOICE_DIR = r"C:\AtulDevelopment\AbhiyanAI\Git\AbhiyaanAI\backend\AbhiyanAI\AbhiyanAI.VideoWorkerService\backend\openvoice"

async def generate_openvoicetts(text: str, file_path: str, reference_wav_path: str):
    """
    Generate speech using OpenVoice CLI from the embedded local openvoice folder.
    """
    try:
        print(f"📥 TTS file path: {file_path}")
        print(f"📥 Reference voice path: {reference_wav_path}")

        output_dir = os.path.dirname(file_path)
        output_filename = os.path.basename(file_path)
        os.makedirs(output_dir, exist_ok=True)

        command = [
        sys.executable, "cli_wrapper.py",
        "--text", text,
        "--reference_audio", reference_wav_path,
        "--output", file_path,
        "--language", "mr",
        "--emotion", "neutral"
        ]

        print("▶️ Running command:", " ".join(command))
        result = subprocess.run(command, cwd=OPENVOICE_DIR, capture_output=True, text=True, check=True)
        print(f"✅ TTS generated at: {file_path}")
        print(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"❌ TTS generation failed:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
    except Exception as e:
        print(f"❌ Unexpected error during TTS generation: {e}")

def clone_voice(tts_wav_path: str, cloned_wav_path: str, reference_wav_path: str):
    """Clone voice using simple audio manipulation - fallback when OpenVoice fails"""
    try:
        print(f"📥 TTS WAV path: {tts_wav_path}")
        print(f"📥 Reference voice path: {reference_wav_path}")
        print(f"📤 Output path: {cloned_wav_path}")

        assert os.path.exists(tts_wav_path), f"TTS WAV not found at: {tts_wav_path}"
        assert os.path.exists(reference_wav_path), f"Reference voice not found at: {reference_wav_path}"
        os.makedirs(os.path.dirname(cloned_wav_path), exist_ok=True)

        # Try OpenVoice first with offline environment
        try:
            print("🧬 Attempting OpenVoice cloning...")
            
            # ALWAYS extend audio files to prevent "too short" errors
            print("⚡ Pre-processing audio files...")
            extended_tts = extend_short_audio(tts_wav_path, min_duration=3.0)
            extended_ref = extend_short_audio(reference_wav_path, min_duration=5.0)
            
            print(f"📥 Using TTS audio: {extended_tts}")
            print(f"📥 Using reference audio: {extended_ref}")
            
            # Set environment variables and try OpenVoice with smart fallback
            try:
                # First attempt: Online mode for model downloads
                env = os.environ.copy()
                env.update({
                    'CURL_CA_BUNDLE': '',
                    'REQUESTS_CA_BUNDLE': '',
                    'SSL_VERIFY': '0',
                    'PYTHONHTTPSVERIFY': '0'
                })

                subprocess.run([
                    sys.executable, "-m", "openvoice_cli", "single",
                    "-i", extended_tts,
                    "-r", extended_ref,
                    "-o", cloned_wav_path
                ], check=True, env=env, timeout=120)
                
                print(f"✅ OpenVoice cloning successful: {cloned_wav_path}")
                
                # Clean up extended files if they were created
                if extended_tts != tts_wav_path:
                    safe_delete(extended_tts)
                if extended_ref != reference_wav_path:
                    safe_delete(extended_ref)
                return
                
            except subprocess.CalledProcessError as network_error:
                # If network/model error, try offline mode with cached models
                error_msg = str(network_error)
                if any(keyword in error_msg.lower() for keyword in 
                      ["localentrynotfound", "offlinemode", "cannot reach", 
                       "connection", "ssl", "certificate"]):
                    
                    print("🌐 Network error, trying offline mode with cached models...")
                    
                    env_offline = os.environ.copy()
                    env_offline.update({
                        'CURL_CA_BUNDLE': '',
                        'REQUESTS_CA_BUNDLE': '',
                        'SSL_VERIFY': '0',
                        'PYTHONHTTPSVERIFY': '0',
                        'HF_HUB_OFFLINE': '1',
                        'TRANSFORMERS_OFFLINE': '1'
                    })
                    
                    try:
                        subprocess.run([
                            sys.executable, "-m", "openvoice_cli", "single",
                            "-i", extended_tts,
                            "-r", extended_ref,
                            "-o", cloned_wav_path
                        ], check=True, env=env_offline, timeout=60)
                        
                        print(f"✅ OpenVoice cloning successful (offline): {cloned_wav_path}")
                        
                        # Clean up extended files if they were created
                        if extended_tts != tts_wav_path:
                            safe_delete(extended_tts)
                        if extended_ref != reference_wav_path:
                            safe_delete(extended_ref)
                        return
                        
                    except Exception:
                        # If offline also fails, raise original error to trigger fallback
                        raise network_error
                else:
                    # Re-raise if not a network-related error
                    raise network_error
        except Exception as openvoice_error:
            # Clean up extended files if they were created
            if 'extended_tts' in locals() and extended_tts != tts_wav_path:
                safe_delete(extended_tts)
            if 'extended_ref' in locals() and extended_ref != reference_wav_path:
                safe_delete(extended_ref)
                
            error_msg = str(openvoice_error)
            print(f"❌ OpenVoice failed: {openvoice_error}")
            
            # Check if it's the "input audio is too short" error or related issues
            if any(keyword in error_msg.lower() for keyword in ["too short", "assertionerror", "num_splits > 0"]):
                print("⚡ Attempting minimal voice clone for short audio...")
                if create_minimal_voice_clone(tts_wav_path, reference_wav_path, cloned_wav_path):
                    return
            
            # Check if it's an SSL or network related error
            if any(keyword in error_msg.lower() for keyword in ["ssl", "certificate", "connection", "network"]):
                print("🌐 Network/SSL error detected, skipping OpenVoice...")
            
            # Check if it's a model loading error
            if any(keyword in error_msg.lower() for keyword in ["model", "checkpoint", "load", "download"]):
                print("📦 Model loading error detected, trying alternative...")
            
        # Fallback: Simple voice cloning using audio manipulation
        print("🔄 Using simple voice cloning fallback...")
        simple_voice_cloning(tts_wav_path, reference_wav_path, cloned_wav_path)
        
    except Exception as e:
        print(f"❌ Voice cloning failed: {e}")
        # Final fallback: copy the TTS file as cloned output
        print(f"🔄 Using TTS output as final fallback...")
        try:
            import shutil
            shutil.copy2(tts_wav_path, cloned_wav_path)
            print(f"✅ Fallback cloned voice saved: {cloned_wav_path}")
        except Exception as fallback_e:
            print(f"❌ Fallback also failed: {fallback_e}")

def simple_voice_cloning(tts_wav_path: str, reference_wav_path: str, output_path: str):
    """Enhanced voice cloning using advanced spectral analysis and synthesis"""
    try:
        # Try advanced voice cloning first
        print("🧬 Attempting advanced spectral voice cloning...")
        
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
                    tts_wav_path, reference_wav_path, output_path,
                    pitch_alpha=0.8, envelope_alpha=0.7
                )
                if success:
                    print(f"✅ Advanced voice cloning successful: {output_path}")
                    return
            except ImportError as import_error:
                print(f"⚠️ Advanced cloning import failed: {import_error}")
            except Exception as advanced_error:
                print(f"⚠️ Advanced cloning failed: {advanced_error}")
        
        # Fallback to enhanced FFmpeg-based approach
        print("🔄 Using enhanced FFmpeg voice cloning...")
        enhanced_ffmpeg_voice_cloning(tts_wav_path, reference_wav_path, output_path)
        
    except Exception as e:
        print(f"❌ Enhanced voice cloning failed: {e}")
        # Final fallback: basic audio processing
        basic_voice_cloning_fallback(tts_wav_path, reference_wav_path, output_path)

def enhanced_ffmpeg_voice_cloning(tts_wav_path: str, reference_wav_path: str, output_path: str):
    """Enhanced voice cloning using sophisticated FFmpeg filters"""
    try:
        from pydub import AudioSegment
        import numpy as np
        
        print("� Loading TTS and reference audio...")
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
        
        # 1. Analyze pitch
        ref_pitch = analyze_pitch(ref_samples, ref_sample_rate)
        tts_pitch = analyze_pitch(tts_samples, tts_sample_rate)
        
        print(f"📊 Reference pitch: {ref_pitch:.1f} Hz, TTS pitch: {tts_pitch:.1f} Hz")
        
        # 2. Calculate optimal transformations
        if tts_pitch > 0 and ref_pitch > 0:
            pitch_shift_ratio = ref_pitch / tts_pitch
            pitch_shift_ratio = np.clip(pitch_shift_ratio, 0.6, 1.8)  # Reasonable limits
            semitones = 12 * np.log2(pitch_shift_ratio)
        else:
            semitones = 0
        
        print(f"🎼 Pitch adjustment: {semitones:.1f} semitones")
        
        # 3. Advanced FFmpeg processing with multiple stages
        temp_files = []
        
        # Stage 1: Pitch and formant correction
        temp_pitch = output_path.replace('.wav', '_pitch.wav')
        temp_files.append(temp_pitch)
        
        pitch_filter = f'asetrate={int(ref_sample_rate * pitch_shift_ratio)},aresample={ref_sample_rate}'
        
        subprocess.run([
            'ffmpeg', '-y', '-i', tts_wav_path,
            '-af', pitch_filter,
            '-ar', str(ref_sample_rate),
            '-ac', '1',
            temp_pitch
        ], capture_output=True, check=True)
        
        # Stage 2: Spectral shaping to match reference characteristics
        temp_spectral = output_path.replace('.wav', '_spectral.wav')
        temp_files.append(temp_spectral)
        
        # Create a sophisticated filter chain for voice matching
        spectral_filters = [
            # Remove noise and artifacts
            'highpass=f=80',
            'lowpass=f=8000',
            
            # Dynamic range processing to match reference
            'compand=attacks=0.05:decays=0.2:points=-90/-90|-70/-60|-50/-40|-30/-25|-20/-15|-10/-8|-5/-4|-2/-2|0/0',
            
            # Formant enhancement based on typical male voice characteristics
            f'equalizer=f=500:width_type=o:width=1:g={2 if ref_pitch < 150 else 1}',   # Boost chest voice
            f'equalizer=f=1200:width_type=o:width=1:g={1.5 if ref_pitch < 150 else 0.5}',  # Throat formant
            f'equalizer=f=2500:width_type=o:width=1:g={0.5 if ref_pitch < 150 else -0.5}',  # Mouth formant
            'equalizer=f=4000:width_type=o:width=1:g=-1',  # Reduce sibilance
            'equalizer=f=6000:width_type=o:width=1:g=-2',  # Reduce digital harshness
            
            # Add natural voice characteristics
            'bass=g=1:f=150:width_type=o:width=1',  # Warmth
            'treble=g=-0.5:f=6000:width_type=o:width=1',  # Reduce digital artifacts
        ]
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_pitch,
            '-af', ','.join(spectral_filters),
            temp_spectral
        ], capture_output=True, check=True)
        
        # Stage 3: Harmonic enhancement and natural breathing
        temp_harmonic = output_path.replace('.wav', '_harmonic.wav')
        temp_files.append(temp_harmonic)
        
        harmonic_filters = [
            # Add subtle harmonic distortion for naturalness
            'aexciter=amount=0.3:blend=harmonic',  # Harmonic enhancement
            'aphaser=in_gain=0.4:out_gain=0.8:delay=3:decay=0.4:speed=0.5',  # Subtle phasing for depth
            
            # Dynamic processing for natural speech patterns
            'compand=attacks=0.1:decays=0.8:points=-90/-90|-45/-45|-25/-15|-5/-5|0/0',
            
            # Gate to remove inter-word artifacts
            'agate=threshold=0.01:ratio=2:attack=5:release=50',
        ]
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_spectral,
            '-af', ','.join(harmonic_filters),
            temp_harmonic
        ], capture_output=True, check=True)
        
        # Stage 4: Final acoustic matching with reference environment
        temp_acoustic = output_path.replace('.wav', '_acoustic.wav')
        temp_files.append(temp_acoustic)
        
        # Extract acoustic characteristics from reference
        ref_analysis = analyze_acoustic_environment(reference_wav_path)
        
        acoustic_filters = [
            # Match room acoustics with subtle reverb
            f'aecho=0.8:0.88:{int(ref_analysis.get("reverb_delay", 100))}:0.3',
            f'aecho=0.4:0.7:{int(ref_analysis.get("reverb_delay", 100) * 1.8)}:0.2',
            
            # Final EQ to match reference spectral balance
            'equalizer=f=1000:width_type=o:width=2:g=0.5',  # Presence boost
            'equalizer=f=3000:width_type=o:width=2:g=-0.3',  # Reduce nasal quality
        ]
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_harmonic,
            '-af', ','.join(acoustic_filters),
            temp_acoustic
        ], capture_output=True, check=True)
        
        # Stage 5: Volume and dynamics matching
        tts_processed = AudioSegment.from_wav(temp_acoustic)
        
        # Match volume characteristics
        ref_rms = ref_audio.rms
        tts_rms = tts_processed.rms
        
        if tts_rms > 0:
            volume_adjustment = ref_rms / tts_rms
            volume_db = 20 * np.log10(np.clip(volume_adjustment, 0.3, 3.0))
            tts_processed = tts_processed + volume_db
            print(f"🔊 Volume adjustment: {volume_db:.1f} dB")
        
        # Export final result
        tts_processed.export(output_path, format="wav")
        
        # Clean up temporary files
        for temp_file in temp_files:
            safe_delete(temp_file)
        
        print(f"✅ Enhanced FFmpeg voice cloning completed: {output_path}")
        
    except Exception as e:
        print(f"❌ Enhanced FFmpeg voice cloning failed: {e}")
        raise e

def basic_voice_cloning_fallback(tts_wav_path: str, reference_wav_path: str, output_path: str):
    """Basic voice cloning fallback when advanced methods fail"""
    try:
        print("🔄 Using basic voice cloning fallback...")
        from pydub import AudioSegment
        import numpy as np
        
        # Load audio
        tts_audio = AudioSegment.from_wav(tts_wav_path)
        ref_audio = AudioSegment.from_wav(reference_wav_path)
        
        # Basic processing
        cloned_audio = tts_audio.set_frame_rate(ref_audio.frame_rate).set_channels(1)
        
        # Simple volume matching
        if ref_audio.rms > 0 and cloned_audio.rms > 0:
            volume_diff = ref_audio.rms / cloned_audio.rms
            volume_db = 20 * np.log10(np.clip(volume_diff, 0.5, 2.0))
            cloned_audio = cloned_audio + volume_db
        
        # Basic EQ
        # This is a simplified approach - boost mid frequencies and reduce harshness
        cloned_audio = cloned_audio.low_pass_filter(8000).high_pass_filter(80)
        
        cloned_audio.export(output_path, format="wav")
        print(f"✅ Basic voice cloning fallback completed: {output_path}")
        
    except Exception as e:
        print(f"❌ Basic voice cloning fallback failed: {e}")
        # Final fallback: copy TTS file
        import shutil
        shutil.copy2(tts_wav_path, output_path)
        print(f"🔄 Copied TTS file as final fallback: {output_path}")

def analyze_acoustic_environment(audio_path: str):
    """Analyze acoustic environment characteristics of reference audio"""
    try:
        from pydub import AudioSegment
        import numpy as np
        
        audio = AudioSegment.from_wav(audio_path)
        
        # Basic acoustic analysis
        analysis = {
            'reverb_delay': 100,  # Default reverb delay in ms
            'room_size': 'medium',  # Estimated room size
            'brightness': 0.5,  # Spectral brightness (0-1)
        }
        
        # Estimate reverb characteristics from audio tail
        if len(audio) > 1000:  # If audio is longer than 1 second
            # Look at the last 500ms for reverb tail
            tail = audio[-500:]
            if tail.rms > 0:
                # Simple reverb detection based on decay
                decay_rate = tail.rms / audio.rms if audio.rms > 0 else 0
                if decay_rate > 0.1:
                    analysis['reverb_delay'] = 150  # Longer reverb
                elif decay_rate > 0.05:
                    analysis['reverb_delay'] = 100  # Medium reverb
                else:
                    analysis['reverb_delay'] = 50   # Short reverb
        
        return analysis
        
    except Exception as e:
        print(f"⚠️ Acoustic analysis failed: {e}")
        return {
            'reverb_delay': 100,
            'room_size': 'medium', 
            'brightness': 0.5,
        }

def analyze_pitch(audio_samples, sample_rate):
    """Analyze the fundamental frequency (pitch) of audio samples"""
    try:
        import numpy as np
        from scipy import signal
        
        # Ensure we have enough samples
        if len(audio_samples) < sample_rate // 10:  # At least 0.1 seconds
            return 150.0  # Default pitch
        
        # Convert to float and normalize
        audio_float = audio_samples.astype(np.float32)
        audio_float = audio_float / (np.max(np.abs(audio_float)) + 1e-10)
        
        # Apply window to reduce edge effects
        window_size = len(audio_float)
        window = signal.windows.hann(window_size)
        audio_windowed = audio_float * window
        
        # Auto-correlation method for pitch detection
        correlation = np.correlate(audio_windowed, audio_windowed, mode='full')
        correlation = correlation[len(correlation)//2:]
        
        # Find the first peak after the zero lag
        min_period = int(sample_rate / 500)  # Maximum frequency of 500 Hz
        max_period = int(sample_rate / 50)   # Minimum frequency of 50 Hz
        
        if max_period >= len(correlation):
            return 150.0  # Default pitch
        
        # Find peaks in the correlation function
        correlation_segment = correlation[min_period:max_period]
        
        if len(correlation_segment) == 0:
            return 150.0
        
        # Find the maximum peak
        peak_index = np.argmax(correlation_segment)
        period = peak_index + min_period
        
        # Calculate frequency
        if period > 0:
            frequency = sample_rate / period
            # Sanity check for reasonable voice frequency
            if 50 <= frequency <= 500:
                return frequency
        
        # Fallback to spectral analysis
        fft = np.fft.fft(audio_windowed)
        freqs = np.fft.fftfreq(len(fft), 1/sample_rate)
        magnitude = np.abs(fft)
        
        # Look for peak in voice frequency range
        voice_mask = (freqs >= 50) & (freqs <= 500)
        if np.any(voice_mask):
            voice_freqs = freqs[voice_mask]
            voice_magnitude = magnitude[voice_mask]
            peak_freq_index = np.argmax(voice_magnitude)
            peak_frequency = voice_freqs[peak_freq_index]
            return abs(peak_frequency)
        
        return 150.0  # Default male voice pitch
        
    except Exception as e:
        print(f"⚠️ Pitch analysis failed: {e}")
        return 150.0  # Default pitch

async def generate_progress(name: str, basevideo: str):
    """Main processing pipeline for one name"""
    safe_name = name.strip().replace(" ", "_")
    reference_wav_path = os.path.join(REFERENCE_AUDIO_DIR, f"{safe_name}_{RUN_ID}_reference.wav")
    extract_reference_audio(basevideo, reference_wav_path)

    # === Transcribe audio from base video ===
    # print(f"🔎 Transcribing base video for name injection...")
    # transcribed_text = await transcribe_audio(reference_wav_path, language=LANGUAGE)
    transcribed_text = "नमस्कार जय गनेश गन्पति वप्पा मौर्या कल्वियने आथ आनंद होता है कि सालाबाद प्रमाने यंदाच वर्षी ही पुण्णिनग्री तरुण मित्रमांड़ा तरपे सांश्कृतिक कारेक्रमांचे आयोजन करने ताल्ले है तरी आपन यास कारेक्रमां मदे परिवारा सोबच सहभागी होने कारेक्रमांचा अस्वाध गयावा "
    # === Inject name into message ===
    # injected_message = f"नमस्कार {name} {transcribed_text}"

    tts_mp3 = os.path.join(TTS_DIR, f"{safe_name}.mp3")
    tts_wav = os.path.join(TTS_DIR, f"{safe_name}.wav")
    cloned_wav = os.path.join(CLONED_DIR, f"{safe_name}.wav")
    
    # Generate only the name to replace silence in original video  
    print(f"🗣 Generating TTS for name only: {name}")
    # Try to use the reference voice more intelligently to create name audio
    create_name_audio_from_reference(name, reference_wav_path, tts_mp3)

    print(f"🔄 Converting MP3 to WAV for {name}")
    os.system(f"ffmpeg -y -i \"{tts_mp3}\" \"{tts_wav}\"")

    print(f"🧬 Cloning voice for {name}")
    clone_voice(tts_wav, cloned_wav, reference_wav_path)
    

    # === Since we're only generating the name, use the entire cloned audio ===
    print(f"📄 Using entire cloned audio for {name} (no trimming needed)")
    trimmed_path = cloned_wav  # Use the entire cloned audio

    # === Generate final video ===
    print(f"🎥 Generating video for {name}")
    final_video_path = generate_video_for_name(safe_name, basevideo, trimmed_path)
    print(f"✅ Done for {name}")

    # === Cleanup temp files for this run ===
    cleanup_run_dirs()
    safe_delete(tts_mp3)
    safe_delete(tts_wav)
    safe_delete(cloned_wav)
    safe_delete(trimmed_path)
    safe_delete(reference_wav_path)
    print(final_video_path)

def limit_words(text: str, max_words: int = 20) -> str:
   words = text.strip().split()
   return " ".join(words[:max_words])

def cleanup_run_dirs():
    """Remove all directories for this process's RUN_ID."""
    for base_dir in [BASE_UPLOAD_DIR, BASE_VIDEO_DIR, BASE_TTS_DIR, BASE_CLONED_DIR, BASE_REFERENCE_AUDIO_DIR]:
        run_dir = os.path.join(base_dir, RUN_ID)
        if os.path.exists(run_dir):
            try:
                shutil.rmtree(run_dir)
                print(f"🗑 Deleted folder: {run_dir}")
            except Exception as e:
                print(f"⚠ Could not delete folder {run_dir}: {e}")

async def create_silence_audio(file_path: str, duration: int = 2):
    """Create a silent audio file as fallback when TTS fails"""
    try:
        # Use ffmpeg to create silence
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100:duration={duration}',
            '-acodec', 'mp3', '-y', file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print(f"✅ Silent audio created: {file_path}")
        else:
            print(f"❌ Failed to create silent audio: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error creating silent audio: {e}")

def create_tts_from_voice_sample(text: str, reference_voice_path: str, output_path: str):
    """Create TTS audio by manipulating existing voice sample"""
    try:
        print(f"🎤 Creating TTS from voice sample: {reference_voice_path}")
        
        # Calculate estimated duration based on text length
        words = text.split()
        estimated_duration = len(words) * 0.6  # ~0.6 seconds per word in Marathi
        estimated_duration = max(2, min(15, estimated_duration))  # Between 2-15 seconds
        
        # For now, we'll create a modified version of the reference voice
        # This is a placeholder - in a real implementation, you'd use more sophisticated TTS
        
        # Method 1: Repeat and trim the reference voice to match estimated duration
        temp_extended = f"temp_extended_{uuid.uuid4().hex[:6]}.wav"
        temp_trimmed = f"temp_trimmed_{uuid.uuid4().hex[:6]}.wav"
        
        try:
            # First convert to WAV if it's MP3
            ref_wav = reference_voice_path
            if reference_voice_path.endswith('.mp3'):
                ref_wav = f"temp_ref_{uuid.uuid4().hex[:6]}.wav"
                subprocess.run([
                    'ffmpeg', '-y', '-i', reference_voice_path, ref_wav
                ], check=True, capture_output=True)
            
            # Get the duration of reference voice
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', ref_wav
            ], capture_output=True, text=True, check=True)
            
            original_duration = float(result.stdout.strip())
            
            # If we need longer audio, loop the reference voice
            if estimated_duration > original_duration:
                loops = int(estimated_duration / original_duration) + 1
                # Create a list of inputs for concatenation
                filter_inputs = " ".join([f"[0:a]" for _ in range(loops)])
                subprocess.run([
                    'ffmpeg', '-y', '-i', ref_wav,
                    '-filter_complex', f'{filter_inputs} concat=n={loops}:v=0:a=1[out]',
                    '-map', '[out]', temp_extended
                ], check=True, capture_output=True)
            else:
                # Use the original if it's long enough
                temp_extended = ref_wav
            
            # Trim to the desired duration and convert to MP3
            subprocess.run([
                'ffmpeg', '-y', '-i', temp_extended,
                '-t', str(estimated_duration),
                '-acodec', 'mp3', output_path
            ], check=True, capture_output=True)
            
            print(f"✅ TTS created from voice sample: {output_path} ({estimated_duration:.1f}s)")
            
        finally:
            # Cleanup temporary files
            for temp_file in [temp_extended, temp_trimmed]:
                if temp_file != ref_wav and os.path.exists(temp_file):
                    safe_delete(temp_file)
            if ref_wav != reference_voice_path and os.path.exists(ref_wav):
                safe_delete(ref_wav)
                
    except Exception as e:
        print(f"❌ Failed to create TTS from voice sample: {e}")
        # Fallback to silence
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100:duration=3',
            '-acodec', 'mp3', '-y', output_path
        ], capture_output=True)

def create_simple_name_audio(name: str, output_path: str):
    """Create a simple audio file for the name - placeholder implementation"""
    try:
        print(f"🎤 Creating simple audio for name: {name}")
        
        # Calculate duration based on name length (rough estimate)
        words = name.split()
        estimated_duration = len(words) * 0.8  # ~0.8 seconds per word
        estimated_duration = max(1.0, min(3.0, estimated_duration))  # Between 1-3 seconds
        
        # Create a simple tone/beep as placeholder (since we can't do real TTS without proper models)
        # This will be replaced by silence detection in the video generation
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={estimated_duration}', 
            '-acodec', 'mp3', '-y', output_path
        ], check=True, capture_output=True)
        
        print(f"✅ Simple name audio created: {output_path} ({estimated_duration:.1f}s)")
        
    except Exception as e:
        print(f"❌ Failed to create simple name audio: {e}")
        # Fallback to silence
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100:duration=2',
            '-acodec', 'mp3', '-y', output_path
        ], capture_output=True)

async def generate_name_only_tts(name: str, output_path: str):
    """Generate TTS audio for ONLY the name using gTTS"""
    try:
        print(f"🎤 Generating TTS for name only: {name}")
        
        # Use gTTS to generate only the name
        from gtts import gTTS
        
        # Create TTS object for the name only
        tts = gTTS(text=name, lang='hi', slow=False)  # Using Hindi for better Marathi name pronunciation
        
        # Save to file
        tts.save(output_path)
        print(f"✅ Name-only TTS created: {output_path}")
        
    except Exception as e:
        print(f"❌ Failed to generate name-only TTS: {e}")
        try:
            # Fallback: try with pyttsx3 
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(name, output_path.replace('.mp3', '.wav'))
            engine.runAndWait()
            
            # Convert WAV to MP3 if needed
            if output_path.endswith('.mp3'):
                subprocess.run([
                    'ffmpeg', '-y', '-i', output_path.replace('.mp3', '.wav'), output_path
                ], check=True, capture_output=True)
                os.remove(output_path.replace('.mp3', '.wav'))
                
        except Exception as e2:
            print(f"❌ Fallback TTS also failed: {e2}")
            # Final fallback: create silence 
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100:duration=2',
                '-acodec', 'mp3', '-y', output_path
            ], capture_output=True)

def create_synthetic_name_audio(name: str, output_path: str):
    """Create synthetic audio that 'says' the name using existing voice samples"""
    try:
        print(f"🎤 Creating synthetic name audio: {name}")
        
        # List of available voice samples (male voices)
        voice_samples = [
            "backend/tts/Amol_Adkitee.wav",
            "backend/tts/Atul_Kadam.wav", 
            "backend/tts/Atul_Patil.wav"
        ]
        
        # Find an existing voice sample
        reference_voice = None
        for sample in voice_samples:
            if os.path.exists(sample):
                reference_voice = sample
                break
        
        if not reference_voice:
            print("❌ No voice samples found, creating silence")
            # Create 2 seconds of silence as fallback
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100:duration=2',
                '-acodec', 'mp3', '-y', output_path
            ], capture_output=True, check=True)
            return
        
        print(f"🎵 Using voice sample: {reference_voice}")
        
        # For now, create a short 1-2 second audio segment
        # This is a simplified approach - in a real scenario, you'd use proper TTS
        # We'll take a portion of the existing voice sample
        
        # Get duration of the reference voice
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', reference_voice
        ], capture_output=True, text=True, check=True)
        
        original_duration = float(result.stdout.strip())
        
        # Create a 1.5-2 second segment from the middle of the reference
        # This should capture a portion that sounds like speech
        start_time = original_duration * 0.3  # Start at 30% into the audio
        duration = min(2.0, original_duration * 0.4)  # Take up to 2 seconds
        
        subprocess.run([
            'ffmpeg', '-y', '-i', reference_voice, 
            '-ss', str(start_time), '-t', str(duration),
            '-acodec', 'mp3', output_path
        ], check=True, capture_output=True)
        
        print(f"✅ Synthetic name audio created: {output_path} ({duration:.1f}s)")
        
    except Exception as e:
        print(f"❌ Failed to create synthetic name audio: {e}")
        # Create silence as fallback
        try:
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100:duration=2',
                '-acodec', 'mp3', '-y', output_path
            ], capture_output=True, check=True)
        except:
            print("❌ Even fallback silence creation failed")

def create_name_audio_from_reference(name: str, reference_voice_path: str, output_path: str):
    """
    Create audio that attempts to say the name using available voice samples and TTS.
    Enhanced approach to create more natural-sounding name pronunciation.
    """
    try:
        print(f"🎤 Creating enhanced name audio: {name}")
        
        # First check if we have a pre-recorded sample for this exact name
        sample_path = os.path.join("backend", "tts", f"{name.replace(' ', '_')}.wav")
        if os.path.exists(sample_path):
            print(f"🎯 Using pre-recorded sample: {sample_path}")
            # Convert to MP3 and apply enhancement
            subprocess.run([
                'ffmpeg', '-y', '-i', sample_path,
                '-af', 'highpass=f=100,lowpass=f=6000,volume=1.1',
                '-acodec', 'mp3', output_path
            ], capture_output=True, check=True)
            print(f"✅ Pre-recorded sample enhanced: {output_path}")
            return
        
        # Method 1: Enhanced Edge-TTS with Hindi male voice
        print("🔄 Trying enhanced Edge-TTS...")
        try:
            # Use a more natural Hindi male voice
            voice = "hi-IN-Arun-Neural"  # Natural sounding male voice
            
            # Create a more natural sentence structure for name pronunciation
            enhanced_name_text = f"{name}"  # Keep it simple but clear
            
            async def generate_enhanced_tts():
                communicate = edge_tts.Communicate(enhanced_name_text, voice)
                # Save as temporary WAV first for processing
                temp_wav = output_path.replace('.mp3', '_temp.wav')
                await communicate.save(temp_wav)
                
                # Process the TTS to make it sound more natural
                subprocess.run([
                    'ffmpeg', '-y', '-i', temp_wav,
                    '-af', 'highpass=f=80,lowpass=f=6000,equalizer=f=1000:width_type=o:width=2:g=2,volume=1.2',
                    '-acodec', 'mp3', output_path
                ], capture_output=True, check=True)
                
                safe_delete(temp_wav)
            
            # Run the async function
            try:
                asyncio.run(generate_enhanced_tts())
                print(f"✅ Enhanced Edge-TTS created: {output_path}")
                return
            except RuntimeError:
                # Handle existing event loop
                import threading
                result = [None]
                
                def run_tts():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(generate_enhanced_tts())
                        result[0] = "success"
                    except Exception as e:
                        result[0] = f"error: {e}"
                    finally:
                        loop.close()
                
                thread = threading.Thread(target=run_tts)
                thread.start()
                thread.join()
                
                if result[0] == "success":
                    print(f"✅ Enhanced Edge-TTS created: {output_path}")
                    return
                else:
                    print(f"❌ Edge-TTS error: {result[0]}")
            
        except Exception as edge_error:
            print(f"❌ Enhanced Edge-TTS failed: {edge_error}")
        
        # Method 2: Enhanced pyttsx3 with voice characteristic matching
        print("🔄 Trying enhanced pyttsx3...")
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            
            # Analyze reference voice to match characteristics
            ref_analysis = analyze_reference_voice_characteristics(reference_voice_path)
            
            # Configure engine based on reference analysis
            voices = engine.getProperty('voices')
            selected_voice = None
            
            # Try to find the best matching voice
            for voice in voices:
                voice_name = voice.name.lower()
                if any(term in voice_name for term in ['male', 'david', 'mark', 'paul']):
                    selected_voice = voice
                    break
            
            if selected_voice:
                engine.setProperty('voice', selected_voice.id)
                print(f"🎤 Selected voice: {selected_voice.name}")
            
            # Adjust speech characteristics based on reference
            target_rate = max(120, min(200, ref_analysis.get('speech_rate', 150)))
            engine.setProperty('rate', target_rate)
            engine.setProperty('volume', 0.95)
            
            print(f"⚙️ Speech rate: {target_rate}, Reference characteristics: {ref_analysis}")
            
            # Generate to temporary WAV
            temp_wav = output_path.replace('.mp3', '_pyttsx_temp.wav')
            engine.save_to_file(name, temp_wav)
            engine.runAndWait()
            
            # Process and enhance the generated audio
            subprocess.run([
                'ffmpeg', '-y', '-i', temp_wav,
                '-af', 'highpass=f=100,lowpass=f=5000,equalizer=f=800:width_type=o:width=2:g=3,volume=1.3',
                '-acodec', 'mp3', output_path
            ], capture_output=True, check=True)
            
            safe_delete(temp_wav)
            print(f"✅ Enhanced pyttsx3 created: {output_path}")
            return
            
        except Exception as pyttsx_error:
            print(f"❌ Enhanced pyttsx3 failed: {pyttsx_error}")
        
        # Method 3: Smart reference voice segment extraction
        print("🔄 Using smart reference voice extraction...")
        
        # Analyze the reference voice to find the best segment
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', reference_voice_path
        ], capture_output=True, text=True, check=True)
        
        original_duration = float(result.stdout.strip())
        print(f"📊 Reference duration: {original_duration:.1f}s")
        
        # Find multiple potential segments and choose the best one
        best_segment_path = None
        best_score = 0
        
        # Try different segments from the reference
        segment_candidates = [
            (0.2, 1.5),   # Early segment
            (0.3, 1.8),   # Mid-early segment  
            (0.4, 2.0),   # Mid segment
        ]
        
        for i, (start_ratio, duration) in enumerate(segment_candidates):
            if original_duration < 3.0:  # Short reference
                start_time = 0.1
                seg_duration = min(1.5, original_duration - 0.2)
            else:
                start_time = original_duration * start_ratio
                seg_duration = min(duration, original_duration * 0.3)
            
            segment_path = output_path.replace('.mp3', f'_segment_{i}.wav')
            
            try:
                # Extract and enhance segment
                subprocess.run([
                    'ffmpeg', '-y', '-i', reference_voice_path,
                    '-ss', str(start_time), '-t', str(seg_duration),
                    '-af', 'volume=1.4,highpass=f=100,lowpass=f=4000,equalizer=f=1500:width_type=o:width=2:g=2',
                    segment_path
                ], capture_output=True, check=True)
                
                # Analyze segment quality (basic energy and frequency analysis)
                segment_score = analyze_segment_quality(segment_path)
                print(f"📈 Segment {i} score: {segment_score:.2f}")
                
                if segment_score > best_score:
                    best_score = segment_score
                    if best_segment_path:
                        safe_delete(best_segment_path)
                    best_segment_path = segment_path
                else:
                    safe_delete(segment_path)
                    
            except Exception as seg_error:
                print(f"❌ Segment {i} failed: {seg_error}")
        
        if best_segment_path:
            # Convert best segment to MP3
            subprocess.run([
                'ffmpeg', '-y', '-i', best_segment_path,
                '-acodec', 'mp3', output_path
            ], capture_output=True, check=True)
            
            safe_delete(best_segment_path)
            print(f"✅ Best reference segment created: {output_path} (score: {best_score:.2f})")
            return
        
        # Final fallback: Create enhanced silence
        print("🔄 Creating enhanced silence fallback...")
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=44100:duration=1.5',
            '-acodec', 'mp3', '-y', output_path
        ], capture_output=True, check=True)
        print("⚠️ Created silence as final fallback")
        
    except Exception as e:
        print(f"❌ All enhanced methods failed: {e}")
        # Ultimate fallback: basic silence
        try:
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=44100:duration=1.5',
                '-acodec', 'mp3', '-y', output_path
            ], capture_output=True, check=True)
            print("⚠️ Created basic silence")
        except:
            print("❌ Complete failure in name audio creation")

def analyze_reference_voice_characteristics(reference_path: str):
    """Analyze reference voice to extract speech characteristics"""
    try:
        # Use ffprobe to get basic audio characteristics
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-select_streams', 'a:0',
            '-show_entries', 'stream=sample_rate,channels,duration',
            '-of', 'csv=p=0', reference_path
        ], capture_output=True, text=True, check=True)
        
        parts = result.stdout.strip().split(',')
        sample_rate = int(parts[0]) if parts[0] else 44100
        channels = int(parts[1]) if parts[1] else 1
        duration = float(parts[2]) if parts[2] else 0.0
        
        # Estimate speech rate based on duration and typical speech patterns
        # This is a rough estimation
        estimated_words = duration * 2.5  # Assume ~2.5 words per second average
        speech_rate = max(120, min(180, int(120 + (estimated_words / duration) * 10)))
        
        return {
            'sample_rate': sample_rate,
            'channels': channels,
            'duration': duration,
            'speech_rate': speech_rate,
            'estimated_words': estimated_words
        }
    except Exception as e:
        print(f"❌ Reference analysis failed: {e}")
        return {'speech_rate': 150, 'sample_rate': 44100, 'channels': 1, 'duration': 5.0}

def analyze_segment_quality(segment_path: str):
    """Analyze audio segment quality for voice selection"""
    try:
        # Get RMS energy level
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-select_streams', 'a:0',
            '-show_entries', 'packet=rms_level',
            '-of', 'csv=p=0', segment_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            # Parse RMS levels and calculate average
            lines = result.stdout.strip().split('\n')
            rms_values = []
            for line in lines:
                if line and line != 'rms_level':
                    try:
                        rms_values.append(float(line))
                    except ValueError:
                        continue
            
            if rms_values:
                avg_rms = sum(rms_values) / len(rms_values)
                # Convert to a 0-1 score (higher RMS usually indicates better voice presence)
                score = min(1.0, max(0.0, (avg_rms + 30) / 40))  # Normalize RMS range
                return score
        
        # Fallback: use file size as a rough quality indicator
        file_size = os.path.getsize(segment_path)
        return min(1.0, file_size / 50000)  # Normalize by typical small audio file size
        
    except Exception:
        return 0.5  # Default neutral score

def validate_and_fix_paths(base_video_path: str) -> str:
    """Validate and fix common path issues"""
    # Convert backslashes to forward slashes
    fixed_path = base_video_path.replace('\\', '/')
    
    # Check if file exists
    if os.path.exists(fixed_path):
        return fixed_path
    
    # Common fixes
    common_fixes = [
        # Fix template vs templates
        fixed_path.replace('/template/', '/templates/'),
        fixed_path.replace('\\template\\', '/templates/'),
        # Try adding backend/ prefix if missing
        f"backend/{fixed_path}" if not fixed_path.startswith('backend/') else fixed_path,
        # Try relative path from current directory
        os.path.join(os.getcwd(), fixed_path),
        # Check if it's just a filename in templates
        f"backend/templates/{os.path.basename(fixed_path)}" if not '/' in fixed_path and not '\\' in fixed_path else fixed_path
    ]
    
    for attempt in common_fixes:
        if os.path.exists(attempt):
            print(f"📁 Fixed path: {base_video_path} → {attempt}")
            return attempt
    
    # If no fixes work, provide helpful error
    print(f"❌ Video file not found: {base_video_path}")
    print("💡 Common solutions:")
    print(f"   - Check if file exists: {os.path.abspath(fixed_path)}")
    print(f"   - Try: backend/templates/as.mp4")
    print(f"   - Available template files:")
    
    # List available template files
    templates_dir = "backend/templates"
    if os.path.exists(templates_dir):
        for file in os.listdir(templates_dir):
            if file.endswith('.mp4'):
                print(f"     - {templates_dir}/{file}")
    else:
        print(f"     - Templates directory not found: {templates_dir}")
    
    raise FileNotFoundError(f"Video file not found: {base_video_path}")

def extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:
    """Extend audio file if it's too short for voice cloning"""
    try:
        import subprocess
        import tempfile
        
        # Get audio duration
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        print(f"🕒 Audio duration: {duration:.2f}s")
        
        if duration < min_duration:
            print(f"⚡ Extending short audio from {duration:.2f}s to {min_duration:.2f}s")
            
            # Calculate how many times to repeat
            repeat_count = int((min_duration / duration) + 1)
            
            # Create the extended audio file
            base_name = os.path.splitext(audio_path)[0]
            extended_path = f"{base_name}_extended.wav"
            
            # Use FFmpeg to concatenate the audio file with itself
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for _ in range(repeat_count):
                    f.write(f"file '{os.path.abspath(audio_path)}'\n")
                concat_file = f.name
            
            try:
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', concat_file, '-t', str(min_duration),
                    '-acodec', 'copy', extended_path
                ], check=True, capture_output=True)
                
                os.unlink(concat_file)
                print(f"✅ Extended audio saved: {extended_path}")
                return extended_path
                
            except subprocess.CalledProcessError as e:
                # Fallback: use simple repeat with silence padding
                subprocess.run([
                    'ffmpeg', '-y', '-i', audio_path,
                    '-filter_complex', f'[0:a]aloop=loop={repeat_count-1}:size=44100*{min_duration}[out]',
                    '-map', '[out]', '-t', str(min_duration), extended_path
                ], check=True, capture_output=True)
                
                print(f"✅ Extended audio with loop: {extended_path}")
                return extended_path
        else:
            return audio_path
            
    except Exception as e:
        print(f"⚠️ Could not extend audio: {e}")
        return audio_path

def create_minimal_voice_clone(tts_path: str, reference_path: str, output_path: str):
    """Create a minimal voice clone when OpenVoice fails due to short audio"""
    try:
        print("🔄 Creating minimal voice clone...")
        
        # Use FFmpeg to apply basic voice modification
        subprocess.run([
            'ffmpeg', '-y',
            '-i', tts_path,
            '-i', reference_path,
            '-filter_complex',
            '[0:a]atempo=0.95,rubberband=pitch=0.95[tts];'
            '[1:a]compand=attacks=0.3:decays=1.2:points=-80/-80|-12.4/-12.4|-6/-8|0/-6.8[ref];'
            '[tts][ref]amix=inputs=2:duration=first:weights=0.7 0.3',
            '-ar', '24000', '-ac', '1',
            output_path
        ], check=True, capture_output=True)
        
        print(f"✅ Minimal voice clone created: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Minimal voice clone failed: {e}")
        return False

def validate_video_duration(video_path, min_duration=10.0):
    """Validate that video meets minimum duration requirements and extend if needed"""
    try:
        # Check video duration
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        print(f"📹 Video duration: {duration:.2f} seconds")
        
        if duration < min_duration:
            print(f"⚠️ Video duration ({duration:.2f}s) is less than minimum ({min_duration}s)")
            
            # Try to extend the video by looping
            base_name = os.path.splitext(video_path)[0]
            extended_path = f"{base_name}_extended.mp4"
            
            # Calculate loop count needed
            loop_count = int(min_duration / duration) + 1
            
            print(f"🔄 Extending video by looping {loop_count} times...")
            subprocess.run([
                'ffmpeg', '-y', '-stream_loop', str(loop_count-1), 
                '-i', video_path, '-t', str(min_duration),
                '-c', 'copy', extended_path
            ], check=True)
            
            print(f"✅ Extended video created: {extended_path}")
            return extended_path
            
        return video_path
        
    except Exception as e:
        print(f"❌ Video validation failed: {e}")
        return video_path

def setup_openvoice_environment():
    """Set up OpenVoice environment and download models if needed"""
    try:
        print("🚀 Setting up OpenVoice environment...")
        
        # Create OpenVoice directory structure
        openvoice_dir = "openvoice"
        checkpoints_dir = os.path.join(openvoice_dir, "checkpoints") 
        base_speakers_dir = os.path.join(checkpoints_dir, "base_speakers", "EN")
        converter_dir = os.path.join(checkpoints_dir, "converter")
        
        for directory in [openvoice_dir, checkpoints_dir, base_speakers_dir, converter_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Set HuggingFace cache to local directory
        os.environ["HF_HUB_CACHE"] = os.path.join(openvoice_dir, "models")
        os.environ["HF_HOME"] = os.path.join(openvoice_dir, "hf_home")
        
        print(f"✅ OpenVoice environment ready: {openvoice_dir}")
        return True
        
    except Exception as e:
        print(f"❌ OpenVoice environment setup failed: {e}")
        return False

def validate_and_fix_paths(video_path):
    """Validate and fix common path issues"""
    # Fix common path variations
    if video_path.startswith("template/"):
        video_path = video_path.replace("template/", "templates/")
    
    if not os.path.exists(video_path):
        # Try with templates/ prefix
        if not video_path.startswith("templates/"):
            alt_path = os.path.join("templates", os.path.basename(video_path))
            if os.path.exists(alt_path):
                print(f"🔄 Fixed path: {video_path} -> {alt_path}")
                video_path = alt_path
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Validate video duration and extend if needed
    return validate_video_duration(video_path)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate.py \"<Full Name>\" \"<Base Video Path>\"")
        print("Example: python generate.py \"Atul Kadam\" \"templates/as.mp4\"")
        sys.exit(1)

    input_name = sys.argv[1]
    base_video_path = sys.argv[2]
    
    try:
        # Set up OpenVoice environment first
        setup_openvoice_environment()
        
        # Validate and fix common path issues
        base_video_path = validate_and_fix_paths(base_video_path)
        print(f"🎬 Processing: {input_name}")
        print(f"📹 Video file: {base_video_path}")
        
        asyncio.run(generate_progress(input_name, base_video_path))
    except FileNotFoundError as e:
        print(f"❌ File Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
