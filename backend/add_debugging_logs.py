#!/usr/bin/env python3
"""
Patch script to add enhanced logging to the existing generate.py
This will help identify exactly what's happening with the audio extension
"""

import os
import sys
import shutil
import datetime

def backup_original():
    """Create a backup of the original generate.py"""
    if os.path.exists("generate.py"):
        backup_name = f"generate_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        shutil.copy("generate.py", backup_name)
        print(f"✅ Backup created: {backup_name}")
        return True
    else:
        print("❌ generate.py not found in current directory")
        return False

def patch_extend_short_audio():
    """Add logging to the extend_short_audio function"""
    print("🔧 Patching extend_short_audio function with enhanced logging...")
    
    if not os.path.exists("generate.py"):
        print("❌ generate.py not found")
        return False
    
    # Read the original file
    with open("generate.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the extend_short_audio function and add logging
    old_function_start = 'def extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:'
    
    if old_function_start not in content:
        print("❌ extend_short_audio function not found in generate.py")
        return False
    
    # Enhanced function with logging
    new_function = '''def extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:
    """Extend audio file if it's too short for voice cloning - WITH ENHANCED LOGGING"""
    import datetime
    
    def log_extend(message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[EXTEND_LOG {timestamp}] {message}")
    
    log_extend(f"🚀 EXTEND_SHORT_AUDIO CALLED")
    log_extend(f"   Input: {audio_path}")
    log_extend(f"   Min duration: {min_duration}s")
    log_extend(f"   Current working directory: {os.getcwd()}")
    
    try:
        import subprocess
        import tempfile
        
        # Check if file exists
        log_extend(f"📁 Checking if file exists...")
        if not os.path.exists(audio_path):
            log_extend(f"❌ ERROR: File does not exist: {audio_path}")
            return audio_path
        
        file_size = os.path.getsize(audio_path)
        log_extend(f"✅ File exists: {audio_path} ({file_size} bytes)")
        
        # Get audio duration
        log_extend(f"⏱️ Getting audio duration with ffprobe...")
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        log_extend(f"✅ Audio duration: {duration:.2f}s")
        
        if duration < min_duration:
            log_extend(f"⚡ Extension needed: {duration:.2f}s → {min_duration:.2f}s")
            
            # Calculate how many times to repeat
            repeat_count = int((min_duration / duration) + 1)
            log_extend(f"🔄 Will repeat {repeat_count} times")
            
            # Create the extended audio file
            base_name = os.path.splitext(audio_path)[0]
            extended_path = f"{base_name}_extended.wav"
            log_extend(f"📤 Extended file path: {extended_path}")
            
            # Use FFmpeg to concatenate the audio file with itself
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                abs_path = os.path.abspath(audio_path).replace('\\\\', '/')
                log_extend(f"   Using absolute path: {abs_path}")
                for _ in range(repeat_count):
                    f.write(f"file '{abs_path}'\\n")
                concat_file = f.name
            
            log_extend(f"✅ Concat file created: {concat_file}")
            
            try:
                cmd = [
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', concat_file, '-t', str(min_duration),
                    '-acodec', 'copy', extended_path
                ]
                log_extend(f"⚙️ Running: {' '.join(cmd)}")
                
                subprocess.run(cmd, check=True, capture_output=True)
                
                os.unlink(concat_file)
                log_extend(f"✅ Extended audio saved: {extended_path}")
                
                # Verify result
                verify_result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', extended_path
                ], capture_output=True, text=True, check=True)
                
                extended_duration = float(verify_result.stdout.strip())
                log_extend(f"✅ Verified extended duration: {extended_duration:.2f}s")
                
                return extended_path
                
            except subprocess.CalledProcessError as e:
                log_extend(f"❌ FFmpeg failed, trying fallback...")
                log_extend(f"   Error: {e}")
                # Fallback: use simple repeat with silence padding
                try:
                    subprocess.run([
                        'ffmpeg', '-y', '-i', audio_path,
                        '-filter_complex', f'[0:a]aloop=loop={repeat_count-1}:size=44100*{min_duration}[out]',
                        '-map', '[out]', '-t', str(min_duration), extended_path
                    ], check=True, capture_output=True)
                    
                    log_extend(f"✅ Extended audio with loop: {extended_path}")
                    return extended_path
                except Exception as fallback_e:
                    log_extend(f"❌ Fallback also failed: {fallback_e}")
                    return audio_path
        else:
            log_extend(f"ℹ️ Audio is already long enough ({duration:.2f}s >= {min_duration}s)")
            return audio_path
            
    except Exception as e:
        log_extend(f"❌ Could not extend audio: {e}")
        import traceback
        traceback.print_exc()
        return audio_path
    finally:
        log_extend(f"🏁 EXTEND_SHORT_AUDIO FINISHED")'''
    
    # Find the start and end of the original function
    start_pos = content.find(old_function_start)
    if start_pos == -1:
        print("❌ Could not find function start")
        return False
    
    # Find the end of the function (next function definition or end of file)
    # Look for next function definition at the same indentation level
    lines = content[start_pos:].split('\n')
    end_line = len(lines)
    
    for i, line in enumerate(lines[1:], 1):  # Skip the def line
        if line and not line[0].isspace() and line.startswith('def '):
            end_line = i
            break
    
    # Calculate the end position
    end_pos = start_pos + len('\n'.join(lines[:end_line]))
    
    # Replace the function
    new_content = content[:start_pos] + new_function + content[end_pos:]
    
    # Write back to file
    with open("generate.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Successfully patched extend_short_audio function")
    return True

def patch_clone_voice():
    """Add logging to the clone_voice function"""
    print("🔧 Adding enhanced logging to clone_voice function...")
    
    with open("generate.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the line where extend_short_audio is called and add logging before it
    old_line = '        print("⚡ Pre-processing audio files...")'
    new_lines = '''        print("⚡ Pre-processing audio files...")
        import datetime
        
        def log_clone(message):
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[CLONE_LOG {timestamp}] {message}")
        
        log_clone(f"🎭 STARTING clone_voice")
        log_clone(f"   TTS path: {tts_wav_path}")
        log_clone(f"   Reference path: {reference_wav_path}")
        log_clone(f"   Output path: {cloned_wav_path}")'''
    
    if old_line in content:
        content = content.replace(old_line, new_lines)
        
        # Also add logging after the extend_short_audio calls
        extend_calls = [
            'extended_tts = extend_short_audio(tts_wav_path, min_duration=3.0)',
            'extended_ref = extend_short_audio(reference_wav_path, min_duration=5.0)'
        ]
        
        for i, call in enumerate(extend_calls):
            if call in content:
                var_name = 'extended_tts' if i == 0 else 'extended_ref'
                log_line = f'        log_clone(f"📥 {var_name}: {{{var_name}}}")'
                content = content.replace(call, call + '\n' + log_line)
        
        # Write back
        with open("generate.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("✅ Successfully added logging to clone_voice function")
        return True
    else:
        print("⚠️ Could not find clone_voice logging insertion point")
        return False

def main():
    """Run the patching process"""
    print("🚀 PATCHING GENERATE.PY FOR ENHANCED LOGGING")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("generate.py"):
        print("❌ generate.py not found in current directory")
        print(f"Current directory: {os.getcwd()}")
        print("Please run this script in the same directory as generate.py")
        return False
    
    # Create backup
    if not backup_original():
        return False
    
    # Apply patches
    success = True
    
    if not patch_extend_short_audio():
        success = False
    
    if not patch_clone_voice():
        success = False
    
    if success:
        print("\n🎉 SUCCESS! generate.py has been patched with enhanced logging.")
        print("Now run your video generation and you'll see detailed logs about:")
        print("  - File existence checks")
        print("  - Audio duration measurements")
        print("  - FFmpeg commands and results")
        print("  - File creation and verification")
        print("\nThis will help identify exactly where the audio extension is failing.")
        print("\n💡 To remove the logging later, restore from the backup file.")
    else:
        print("\n❌ FAILED! Some patches could not be applied.")
        print("Check the errors above and manually add logging if needed.")
    
    return success

if __name__ == "__main__":
    main()
