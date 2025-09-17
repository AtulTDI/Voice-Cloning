#!/usr/bin/env python3
"""
Debug script to check why audio extension is not working on new machine
"""

import os
import sys

def debug_audio_extension():
    """Debug the audio extension issue"""
    print("🔍 Debugging audio extension on new machine...")
    print("=" * 60)
    
    # Step 1: Check if generate.py has the right code
    print("\n1. Checking generate.py code...")
    try:
        with open('generate.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key indicators
        checks = {
            'extend_short_audio function': 'def extend_short_audio(' in content,
            'Pre-processing message': 'Pre-processing audio files' in content,
            'ALWAYS extend comment': 'ALWAYS extend audio files' in content,
            'extended_tts variable': 'extended_tts = extend_short_audio(' in content,
            'extended_ref variable': 'extended_ref = extend_short_audio(' in content,
        }
        
        all_good = True
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check}")
            if not result:
                all_good = False
        
        if not all_good:
            print("\n❌ Code is missing audio extension components!")
            return False
            
        print("\n✅ Code appears to have audio extension components")
        
    except Exception as e:
        print(f"❌ Error reading generate.py: {e}")
        return False
    
    # Step 2: Check FFmpeg availability
    print("\n2. Checking FFmpeg...")
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ FFmpeg is available")
        else:
            print("   ❌ FFmpeg command failed")
            return False
    except Exception as e:
        print(f"   ❌ FFmpeg not found: {e}")
        return False
    
    # Step 3: Test the extend_short_audio function directly
    print("\n3. Testing extend_short_audio function...")
    try:
        # Create a test script to check the function
        test_script = '''
import sys
import os
sys.path.insert(0, '.')

# Import the function from generate.py
exec(open('generate.py').read())

# Test with a fake short audio path
test_result = extend_short_audio.__code__.co_varnames
print(f"✅ extend_short_audio function exists with parameters: {test_result}")
'''
        
        result = subprocess.run([sys.executable, '-c', test_script], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"   {result.stdout.strip()}")
        else:
            print(f"   ❌ Function test failed: {result.stderr}")
            
    except Exception as e:
        print(f"   ❌ Function test error: {e}")
    
    # Step 4: Check if the OpenVoice call is using extended files
    print("\n4. Checking OpenVoice subprocess call...")
    
    # Look for the subprocess call pattern
    if '"-i", extended_tts,' in content and '"-r", extended_ref,' in content:
        print("   ✅ OpenVoice call uses extended audio files")
    elif '"-i", tts_wav_path,' in content and '"-r", reference_wav_path,' in content:
        print("   ❌ OpenVoice call uses original files (not extended)")
        print("   🔧 This is the problem! The subprocess call needs to be updated.")
        return False
    else:
        print("   ⚠️ Could not find OpenVoice subprocess call pattern")
    
    return True

def show_fix_instructions():
    """Show instructions to fix the issue"""
    print("\n" + "=" * 60)
    print("🔧 FIX INSTRUCTIONS:")
    print("\nThe issue is likely that your OpenVoice subprocess call")
    print("is still using the original audio files instead of extended ones.")
    print("\nTo fix this, you need to update the subprocess.run call in generate.py:")
    print("\nChange this:")
    print('   "-i", tts_wav_path,')
    print('   "-r", reference_wav_path,')
    print("\nTo this:")
    print('   "-i", extended_tts,')
    print('   "-r", extended_ref,')
    print("\nOr run the quick fix script:")
    print("   python quick_fix_new_machine.py")

def main():
    print("🚀 Audio Extension Debug Tool")
    
    if not os.path.exists('generate.py'):
        print("❌ generate.py not found. Run this in the backend/ directory.")
        return
    
    is_working = debug_audio_extension()
    
    if not is_working:
        show_fix_instructions()
    else:
        print("\n🎉 Audio extension appears to be set up correctly!")
        print("\n🤔 If you're still getting the error, the issue might be:")
        print("   1. FFprobe/FFmpeg path issues")
        print("   2. File permissions")
        print("   3. Audio file format issues")
        print("\n🧪 Try running this test:")
        print("   python generate.py \"Short Test\" \"templates/as.mp4\"")
        print("\nYou should see:")
        print("   ⚡ Pre-processing audio files...")
        print("   🕒 Audio duration: X.XXs")
        print("   ⚡ Extending short audio from X.XXs to 3.00s")

if __name__ == "__main__":
    main()
