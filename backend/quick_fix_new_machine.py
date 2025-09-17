#!/usr/bin/env python3
"""
Quick update script for new machine - adds audio extension fix if missing
"""

import os
import sys
import shutil
from pathlib import Path

def update_generate_py():
    """Update generate.py with audio extension fix if it's missing"""
    print("🔧 Updating generate.py with audio extension fix...")
    
    if not os.path.exists('generate.py'):
        print("❌ generate.py not found")
        return False
    
    # Read current file
    with open('generate.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if we already have the fix
    if 'def extend_short_audio(' in content:
        print("✅ extend_short_audio function already exists")
        return True
    
    # Add the extend_short_audio function if missing
    extend_function = '''
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
                    f.write(f"file '{os.path.abspath(audio_path)}'\\n")
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
'''
    
    # Find the location to insert the function (before clone_voice function)
    if 'def clone_voice(' in content:
        # Insert before clone_voice function
        parts = content.split('def clone_voice(', 1)
        new_content = parts[0] + extend_function + '\n\ndef clone_voice(' + parts[1]
    else:
        # Add at the end of imports section
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_pos = i + 1
        
        lines.insert(insert_pos + 1, extend_function)
        new_content = '\n'.join(lines)
    
    # Backup original file
    shutil.copy2('generate.py', 'generate.py.backup')
    
    # Write updated content
    with open('generate.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Added extend_short_audio function to generate.py")
    print("💾 Original backed up as generate.py.backup")
    return True

def update_openvoice_call():
    """Update the OpenVoice call to use audio extension"""
    print("🔧 Updating OpenVoice call to use audio extension...")
    
    with open('generate.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already updated
    if 'Pre-processing audio files' in content:
        print("✅ OpenVoice call already updated")
        return True
    
    # Find and replace the OpenVoice section
    old_pattern = '''print("🧬 Attempting OpenVoice cloning...")'''
    new_pattern = '''print("🧬 Attempting OpenVoice cloning...")
            
            # ALWAYS extend audio files to prevent "too short" errors
            print("⚡ Pre-processing audio files...")
            extended_tts = extend_short_audio(tts_wav_path, min_duration=3.0)
            extended_ref = extend_short_audio(reference_wav_path, min_duration=5.0)
            
            print(f"📥 Using TTS audio: {extended_tts}")
            print(f"📥 Using reference audio: {extended_ref}")'''
    
    if old_pattern in content:
        # Replace the pattern
        content = content.replace(old_pattern, new_pattern)
        
        # Also update the subprocess call to use extended files
        content = content.replace(
            '"-i", tts_wav_path,',
            '"-i", extended_tts,'
        ).replace(
            '"-r", reference_wav_path,',
            '"-r", extended_ref,'
        )
        
        # Write updated content
        with open('generate.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Updated OpenVoice call to use extended audio")
        return True
    else:
        print("⚠️ Could not find OpenVoice call pattern to update")
        return False

def main():
    print("🚀 Quick Fix for New Machine - Audio Extension")
    print("=" * 55)
    
    # Check current directory
    if not os.path.exists('generate.py'):
        print("❌ generate.py not found. Please run this script in the backend/ directory")
        return
    
    print(f"📁 Working in: {os.getcwd()}")
    
    # Update the file
    func_added = update_generate_py()
    call_updated = update_openvoice_call()
    
    print("\n" + "=" * 55)
    print("📋 Update Summary:")
    print(f"   🔧 extend_short_audio function: {'✅ Added' if func_added else '❌ Failed'}")
    print(f"   🔧 OpenVoice call updated: {'✅ Updated' if call_updated else '❌ Failed'}")
    
    if func_added and call_updated:
        print("\n🎉 Audio extension fix applied successfully!")
        print("\n🎯 Test the fix:")
        print("   python generate.py \"Test Name\" \"templates/as.mp4\"")
        print("\n📝 Expected behavior:")
        print("   - Should show: '⚡ Extending short audio from X.XXs to 3.00s'")
        print("   - No more 'AssertionError: input audio is too short'")
    else:
        print("\n⚠️ Some updates failed. Try manually updating the code:")
        print("   1. git pull origin main")
        print("   2. Or download latest generate.py from GitHub")

if __name__ == "__main__":
    main()
