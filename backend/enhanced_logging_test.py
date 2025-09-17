#!/usr/bin/env python3
"""
Enhanced logging version to track exactly what happens during voice cloning
This script adds detailed logging to identify where the audio extension is failing
"""

import os
import sys
import subprocess
import tempfile
import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

def enhanced_extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:
    """Enhanced extend_short_audio with detailed logging"""
    log_with_timestamp(f"🚀 STARTING extend_short_audio")
    log_with_timestamp(f"   Input: {audio_path}")
    log_with_timestamp(f"   Min duration: {min_duration}s")
    log_with_timestamp(f"   Current working directory: {os.getcwd()}")
    
    try:
        # Check if file exists
        log_with_timestamp(f"📁 Checking if file exists...")
        if not os.path.exists(audio_path):
            log_with_timestamp(f"❌ ERROR: File does not exist: {audio_path}")
            return audio_path
        
        log_with_timestamp(f"✅ File exists: {audio_path}")
        
        # Get file size for additional info
        file_size = os.path.getsize(audio_path)
        log_with_timestamp(f"📊 File size: {file_size} bytes")
        
        # Get audio duration
        log_with_timestamp(f"⏱️ Getting audio duration with ffprobe...")
        
        ffprobe_cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ]
        log_with_timestamp(f"   Command: {' '.join(ffprobe_cmd)}")
        
        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            duration = float(result.stdout.strip())
            log_with_timestamp(f"✅ Audio duration: {duration:.2f}s")
        else:
            log_with_timestamp(f"❌ ERROR: ffprobe returned empty duration")
            log_with_timestamp(f"   STDOUT: '{result.stdout}'")
            log_with_timestamp(f"   STDERR: '{result.stderr}'")
            return audio_path
        
        # Check if extension is needed
        if duration >= min_duration:
            log_with_timestamp(f"ℹ️ Audio is already long enough ({duration:.2f}s >= {min_duration}s)")
            return audio_path
        
        log_with_timestamp(f"⚡ Extension needed: {duration:.2f}s → {min_duration:.2f}s")
        
        # Calculate repeat count
        repeat_count = int((min_duration / duration) + 1)
        log_with_timestamp(f"🔄 Will repeat {repeat_count} times")
        
        # Create extended audio file path
        base_name = os.path.splitext(audio_path)[0]
        extended_path = f"{base_name}_extended.wav"
        log_with_timestamp(f"📤 Extended file path: {extended_path}")
        
        # Create concatenation file
        log_with_timestamp(f"📝 Creating concatenation file...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            abs_path = os.path.abspath(audio_path).replace('\\', '/')  # Normalize path
            log_with_timestamp(f"   Absolute path: {abs_path}")
            
            for i in range(repeat_count):
                line = f"file '{abs_path}'\n"
                f.write(line)
                if i < 3:  # Only log first few lines to avoid spam
                    log_with_timestamp(f"   Line {i+1}: {line.strip()}")
                elif i == 3 and repeat_count > 5:
                    log_with_timestamp(f"   ... (writing {repeat_count - 3} more lines)")
            
            concat_file = f.name
        
        log_with_timestamp(f"✅ Concat file created: {concat_file}")
        
        # Verify concat file contents
        try:
            with open(concat_file, 'r') as f:
                concat_contents = f.read()
            log_with_timestamp(f"📋 Concat file size: {len(concat_contents)} characters")
            log_with_timestamp(f"📋 Concat file lines: {len(concat_contents.splitlines())}")
        except:
            log_with_timestamp(f"⚠️ Could not read back concat file")
        
        # Run FFmpeg concatenation
        log_with_timestamp(f"⚙️ Running FFmpeg concatenation...")
        
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file, '-t', str(min_duration),
            '-acodec', 'copy', extended_path
        ]
        log_with_timestamp(f"   Command: {' '.join(ffmpeg_cmd)}")
        
        ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        log_with_timestamp(f"   Return code: {ffmpeg_result.returncode}")
        if ffmpeg_result.stdout:
            log_with_timestamp(f"   STDOUT: {ffmpeg_result.stdout[:500]}")
        if ffmpeg_result.stderr:
            log_with_timestamp(f"   STDERR: {ffmpeg_result.stderr[:500]}")
        
        if ffmpeg_result.returncode == 0:
            log_with_timestamp(f"✅ FFmpeg concatenation successful")
        else:
            log_with_timestamp(f"❌ FFmpeg concatenation failed, trying fallback...")
            
            # Try fallback method
            fallback_cmd = [
                'ffmpeg', '-y', '-i', audio_path,
                '-filter_complex', f'[0:a]aloop=loop={repeat_count-1}:size=44100*{min_duration}[out]',
                '-map', '[out]', '-t', str(min_duration), extended_path
            ]
            log_with_timestamp(f"   Fallback command: {' '.join(fallback_cmd)}")
            
            fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True)
            log_with_timestamp(f"   Fallback return code: {fallback_result.returncode}")
            
            if fallback_result.returncode != 0:
                log_with_timestamp(f"❌ Fallback also failed")
                log_with_timestamp(f"   Fallback STDERR: {fallback_result.stderr[:500]}")
                
                # Clean up
                try:
                    os.unlink(concat_file)
                except:
                    pass
                
                return audio_path
            else:
                log_with_timestamp(f"✅ Fallback method successful")
        
        # Clean up concat file
        try:
            os.unlink(concat_file)
            log_with_timestamp(f"🗑️ Cleaned up concat file")
        except Exception as e:
            log_with_timestamp(f"⚠️ Failed to clean up concat file: {e}")
        
        # Verify extended file was created
        if os.path.exists(extended_path):
            # Check duration of extended file
            log_with_timestamp(f"🔍 Verifying extended file...")
            
            verify_result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', extended_path
            ], capture_output=True, text=True, check=True)
            
            extended_duration = float(verify_result.stdout.strip())
            extended_size = os.path.getsize(extended_path)
            
            log_with_timestamp(f"✅ Extended file created successfully:")
            log_with_timestamp(f"   Duration: {extended_duration:.2f}s")
            log_with_timestamp(f"   Size: {extended_size} bytes")
            log_with_timestamp(f"   Path: {extended_path}")
            
            return extended_path
        else:
            log_with_timestamp(f"❌ Extended file was not created: {extended_path}")
            return audio_path
            
    except subprocess.CalledProcessError as e:
        log_with_timestamp(f"❌ Subprocess error in extend_short_audio: {e}")
        log_with_timestamp(f"   Command: {e.cmd}")
        log_with_timestamp(f"   Return code: {e.returncode}")
        log_with_timestamp(f"   STDOUT: {e.stdout}")
        log_with_timestamp(f"   STDERR: {e.stderr}")
        return audio_path
    except Exception as e:
        log_with_timestamp(f"❌ Unexpected error in extend_short_audio: {e}")
        import traceback
        traceback.print_exc()
        return audio_path
    
    finally:
        log_with_timestamp(f"🏁 FINISHED extend_short_audio")

def enhanced_clone_voice_with_logging(tts_wav_path: str, cloned_wav_path: str, reference_wav_path: str):
    """Enhanced clone_voice function with detailed logging"""
    log_with_timestamp(f"🎭 STARTING enhanced_clone_voice_with_logging")
    log_with_timestamp(f"   TTS path: {tts_wav_path}")
    log_with_timestamp(f"   Reference path: {reference_wav_path}")
    log_with_timestamp(f"   Output path: {cloned_wav_path}")
    
    try:
        # Check file existence
        for label, path in [("TTS", tts_wav_path), ("Reference", reference_wav_path)]:
            if os.path.exists(path):
                size = os.path.getsize(path)
                log_with_timestamp(f"✅ {label} file exists: {path} ({size} bytes)")
            else:
                log_with_timestamp(f"❌ {label} file missing: {path}")
                return False
        
        # Create output directory
        os.makedirs(os.path.dirname(cloned_wav_path), exist_ok=True)
        log_with_timestamp(f"📁 Output directory created: {os.path.dirname(cloned_wav_path)}")
        
        # Try OpenVoice with audio extension
        log_with_timestamp(f"🧬 Attempting OpenVoice cloning with audio extension...")
        
        # ALWAYS extend audio files to prevent "too short" errors
        log_with_timestamp(f"⚡ Pre-processing audio files...")
        extended_tts = enhanced_extend_short_audio(tts_wav_path, min_duration=3.0)
        extended_ref = enhanced_extend_short_audio(reference_wav_path, min_duration=5.0)
        
        log_with_timestamp(f"📥 Using TTS audio: {extended_tts}")
        log_with_timestamp(f"📥 Using reference audio: {extended_ref}")
        
        # Set environment variables for OpenVoice
        log_with_timestamp(f"🌐 Setting environment variables...")
        env = os.environ.copy()
        env.update({
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',
            'SSL_VERIFY': '0',
            'PYTHONHTTPSVERIFY': '0'
        })
        
        # OpenVoice command
        openvoice_cmd = [
            sys.executable, "-m", "openvoice_cli", "single",
            "-i", extended_tts,
            "-r", extended_ref,
            "-o", cloned_wav_path
        ]
        
        log_with_timestamp(f"🚀 Running OpenVoice command:")
        log_with_timestamp(f"   {' '.join(openvoice_cmd)}")
        
        # Run OpenVoice with timeout and detailed logging
        openvoice_result = subprocess.run(openvoice_cmd, env=env, capture_output=True, text=True, timeout=120)
        
        log_with_timestamp(f"⚙️ OpenVoice finished with return code: {openvoice_result.returncode}")
        
        if openvoice_result.stdout:
            log_with_timestamp(f"📤 OpenVoice STDOUT:")
            for line in openvoice_result.stdout.split('\n')[:20]:  # Show first 20 lines
                if line.strip():
                    log_with_timestamp(f"   {line}")
        
        if openvoice_result.stderr:
            log_with_timestamp(f"📤 OpenVoice STDERR:")
            for line in openvoice_result.stderr.split('\n')[:20]:  # Show first 20 lines
                if line.strip():
                    log_with_timestamp(f"   {line}")
        
        if openvoice_result.returncode == 0:
            log_with_timestamp(f"✅ OpenVoice cloning successful!")
            
            # Verify output file
            if os.path.exists(cloned_wav_path):
                size = os.path.getsize(cloned_wav_path)
                log_with_timestamp(f"✅ Output file created: {cloned_wav_path} ({size} bytes)")
            else:
                log_with_timestamp(f"❌ Output file missing despite success: {cloned_wav_path}")
        else:
            log_with_timestamp(f"❌ OpenVoice failed with return code {openvoice_result.returncode}")
            error_msg = openvoice_result.stderr.lower()
            if "too short" in error_msg:
                log_with_timestamp(f"🔍 'Too short' error detected despite audio extension!")
                log_with_timestamp(f"   This suggests the extension didn't work or wasn't used.")
        
        # Clean up extended files if they were created
        for extended_file, original_file in [(extended_tts, tts_wav_path), (extended_ref, reference_wav_path)]:
            if extended_file != original_file and os.path.exists(extended_file):
                try:
                    os.remove(extended_file)
                    log_with_timestamp(f"🗑️ Cleaned up extended file: {extended_file}")
                except:
                    log_with_timestamp(f"⚠️ Failed to clean up: {extended_file}")
        
        return openvoice_result.returncode == 0
        
    except subprocess.TimeoutExpired:
        log_with_timestamp(f"⏰ OpenVoice timed out after 120 seconds")
        return False
    except Exception as e:
        log_with_timestamp(f"❌ Error in enhanced_clone_voice_with_logging: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        log_with_timestamp(f"🏁 FINISHED enhanced_clone_voice_with_logging")

def main():
    """Test the enhanced logging functions"""
    log_with_timestamp(f"🚀 STARTING ENHANCED LOGGING TEST")
    log_with_timestamp(f"Working directory: {os.getcwd()}")
    
    # Create test files
    test_tts = "test_short_tts.wav"
    test_ref = "test_short_ref.wav"
    test_output = "test_cloned_output.wav"
    
    try:
        # Create short test files
        log_with_timestamp(f"📝 Creating test files...")
        
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1.2',
            '-ar', '24000', '-ac', '1', test_tts
        ], check=True, capture_output=True)
        
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=880:duration=2.1',
            '-ar', '24000', '-ac', '1', test_ref
        ], check=True, capture_output=True)
        
        log_with_timestamp(f"✅ Test files created")
        
        # Test the enhanced clone voice function
        success = enhanced_clone_voice_with_logging(test_tts, test_output, test_ref)
        
        if success:
            log_with_timestamp(f"🎉 Test completed successfully!")
        else:
            log_with_timestamp(f"❌ Test failed - this shows what's happening in the real script")
    
    except Exception as e:
        log_with_timestamp(f"❌ Test setup failed: {e}")
    
    finally:
        # Clean up
        for file in [test_tts, test_ref, test_output]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

if __name__ == "__main__":
    main()
