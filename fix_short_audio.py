#!/usr/bin/env python3
"""
Fix script for "input audio is too short" OpenVoice error
This script provides multiple solutions and fallbacks
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def extend_audio_simple(input_path: str, output_path: str, target_duration: float = 5.0):
    """Simple audio extension using silence padding"""
    try:
        # Get current duration
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', input_path
        ], capture_output=True, text=True, check=True)
        
        current_duration = float(result.stdout.strip())
        print(f"Current duration: {current_duration:.2f}s, target: {target_duration:.2f}s")
        
        if current_duration >= target_duration:
            print("Audio is already long enough")
            if input_path != output_path:
                shutil.copy2(input_path, output_path)
            return True
        
        # Add silence padding to reach target duration
        silence_duration = target_duration - current_duration
        
        subprocess.run([
            'ffmpeg', '-y',
            '-i', input_path,
            '-f', 'lavfi', '-t', str(silence_duration), '-i', 'anullsrc=channel_layout=mono:sample_rate=24000',
            '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]',
            '-map', '[out]',
            output_path
        ], check=True, capture_output=True)
        
        print(f"✅ Extended audio to {target_duration}s: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Audio extension failed: {e}")
        return False

def extend_audio_repeat(input_path: str, output_path: str, target_duration: float = 5.0):
    """Extend audio by repeating the content"""
    try:
        # Get current duration
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', input_path
        ], capture_output=True, text=True, check=True)
        
        current_duration = float(result.stdout.strip())
        
        if current_duration >= target_duration:
            if input_path != output_path:
                shutil.copy2(input_path, output_path)
            return True
            
        # Calculate repeat count
        repeat_count = int(target_duration / current_duration) + 1
        
        subprocess.run([
            'ffmpeg', '-y',
            '-stream_loop', str(repeat_count - 1),
            '-i', input_path,
            '-t', str(target_duration),
            '-acodec', 'copy',
            output_path
        ], check=True, capture_output=True)
        
        print(f"✅ Repeated audio to {target_duration}s: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Audio repeat failed: {e}")
        return False

def fix_short_audio_files(directory: str = "."):
    """Find and fix short audio files in the directory"""
    print(f"🔍 Scanning for short audio files in: {directory}")
    
    # Common directories to check
    dirs_to_check = [
        "tts", "voice_reference", "cloned_voices", 
        "backend/tts", "backend/voice_reference", "backend/cloned_voices"
    ]
    
    fixed_count = 0
    
    for dir_name in dirs_to_check:
        dir_path = os.path.join(directory, dir_name)
        if not os.path.exists(dir_path):
            continue
            
        print(f"📂 Checking: {dir_path}")
        
        # Find all WAV files recursively
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.wav'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Check duration
                        result = subprocess.run([
                            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                            '-of', 'csv=p=0', file_path
                        ], capture_output=True, text=True, check=True)
                        
                        duration = float(result.stdout.strip())
                        
                        if duration < 3.0:  # Less than 3 seconds
                            print(f"⚡ Found short audio: {file_path} ({duration:.2f}s)")
                            
                            # Create extended version
                            backup_path = file_path + ".original"
                            shutil.move(file_path, backup_path)
                            
                            # Try repeat method first, then silence padding
                            if extend_audio_repeat(backup_path, file_path, 5.0):
                                print(f"✅ Fixed with repeat: {file}")
                                fixed_count += 1
                            elif extend_audio_simple(backup_path, file_path, 5.0):
                                print(f"✅ Fixed with padding: {file}")
                                fixed_count += 1
                            else:
                                # Restore original if both methods fail
                                shutil.move(backup_path, file_path)
                                print(f"❌ Could not fix: {file}")
                                
                    except Exception as e:
                        print(f"⚠️ Could not process {file_path}: {e}")
    
    print(f"🎯 Fixed {fixed_count} short audio files")

def main():
    """Main function"""
    print("🔧 OpenVoice Short Audio Fix Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "."
    
    print(f"Working directory: {os.path.abspath(directory)}")
    
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg found")
    except:
        print("❌ FFmpeg not found - please install FFmpeg")
        return
    
    # Fix short audio files
    fix_short_audio_files(directory)
    
    print("\n💡 Usage tips:")
    print("   - Run this before voice cloning to fix short audio issues")
    print("   - Audio files will be extended to 5+ seconds")
    print("   - Original files backed up with .original extension")
    print("   - For single file: python fix_short_audio.py /path/to/directory")

if __name__ == "__main__":
    main()
