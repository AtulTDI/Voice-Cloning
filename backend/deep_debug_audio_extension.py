#!/usr/bin/env python3
"""
Deep debugging script for audio extension issues
Identifies why the extend_short_audio function isn't working properly
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path

def check_system_requirements():
    """Check if all required tools are available"""
    print("=" * 60)
    print("🔍 SYSTEM REQUIREMENTS CHECK")
    print("=" * 60)
    
    checks = {
        'python': [sys.executable, '--version'],
        'ffmpeg': ['ffmpeg', '-version'],
        'ffprobe': ['ffprobe', '-version'],
    }
    
    results = {}
    for tool, cmd in checks.items():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                print(f"✅ {tool}: {version}")
                results[tool] = True
            else:
                print(f"❌ {tool}: Failed with return code {result.returncode}")
                print(f"   STDERR: {result.stderr[:200]}")
                results[tool] = False
        except FileNotFoundError:
            print(f"❌ {tool}: Command not found")
            results[tool] = False
        except Exception as e:
            print(f"❌ {tool}: Error - {e}")
            results[tool] = False
    
    return results

def create_test_audio(duration=1.5, filename="test_short.wav"):
    """Create a test audio file with specific duration"""
    print(f"\n📝 Creating test audio file: {filename} ({duration}s)")
    
    try:
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', f'sine=frequency=440:duration={duration}',
            '-ar', '24000', '-ac', '1', filename
        ], check=True, capture_output=True)
        
        # Verify the created file
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', filename
        ], capture_output=True, text=True, check=True)
        
        actual_duration = float(result.stdout.strip())
        print(f"✅ Test audio created: {filename} ({actual_duration:.2f}s)")
        return filename
        
    except Exception as e:
        print(f"❌ Failed to create test audio: {e}")
        return None

def test_extend_short_audio_function(audio_path, min_duration=3.0):
    """Test the extend_short_audio function step by step"""
    print(f"\n🧪 TESTING EXTEND_SHORT_AUDIO FUNCTION")
    print(f"Input: {audio_path}, Min duration: {min_duration}s")
    print("-" * 40)
    
    try:
        # Step 1: Check if file exists
        if not os.path.exists(audio_path):
            print(f"❌ Audio file doesn't exist: {audio_path}")
            return None
        
        print(f"✅ Audio file exists: {audio_path}")
        
        # Step 2: Get audio duration
        print("📊 Getting audio duration...")
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        print(f"✅ Audio duration: {duration:.2f}s")
        
        # Step 3: Check if extension is needed
        if duration >= min_duration:
            print(f"ℹ️ Audio is already long enough ({duration:.2f}s >= {min_duration}s)")
            return audio_path
        
        print(f"⚡ Extension needed: {duration:.2f}s → {min_duration:.2f}s")
        
        # Step 4: Calculate repeat count
        repeat_count = int((min_duration / duration) + 1)
        print(f"🔄 Will repeat {repeat_count} times")
        
        # Step 5: Create extended audio file path
        base_name = os.path.splitext(audio_path)[0]
        extended_path = f"{base_name}_extended.wav"
        print(f"📤 Extended file path: {extended_path}")
        
        # Step 6: Create concat file
        print("📝 Creating concatenation file...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(repeat_count):
                abs_path = os.path.abspath(audio_path)
                f.write(f"file '{abs_path}'\n")
                print(f"   Line {i+1}: file '{abs_path}'")
            concat_file = f.name
        
        print(f"✅ Concat file created: {concat_file}")
        
        # Step 7: Run FFmpeg concatenation
        print("⚙️ Running FFmpeg concatenation...")
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file, '-t', str(min_duration),
            '-acodec', 'copy', extended_path
        ]
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ FFmpeg concatenation successful")
        else:
            print(f"❌ FFmpeg concatenation failed (return code: {result.returncode})")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            
            # Try fallback method
            print("🔄 Trying fallback loop method...")
            fallback_cmd = [
                'ffmpeg', '-y', '-i', audio_path,
                '-filter_complex', f'[0:a]aloop=loop={repeat_count-1}:size=44100*{min_duration}[out]',
                '-map', '[out]', '-t', str(min_duration), extended_path
            ]
            print(f"Fallback command: {' '.join(fallback_cmd)}")
            
            fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if fallback_result.returncode != 0:
                print(f"❌ Fallback also failed: {fallback_result.stderr}")
                return None
            else:
                print("✅ Fallback method successful")
        
        # Step 8: Clean up concat file
        try:
            os.unlink(concat_file)
            print("🗑️ Cleaned up concat file")
        except:
            pass
        
        # Step 9: Verify extended file
        if os.path.exists(extended_path):
            # Check duration of extended file
            verify_result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', extended_path
            ], capture_output=True, text=True, check=True)
            
            extended_duration = float(verify_result.stdout.strip())
            print(f"✅ Extended file created successfully: {extended_duration:.2f}s")
            return extended_path
        else:
            print("❌ Extended file was not created")
            return None
            
    except Exception as e:
        print(f"❌ Error in extend_short_audio test: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_openvoice_call_simulation():
    """Simulate the OpenVoice call with extended audio"""
    print(f"\n🎭 TESTING OPENVOICE CALL SIMULATION")
    print("-" * 40)
    
    # Create test files
    test_tts = create_test_audio(1.2, "test_tts.wav")
    test_ref = create_test_audio(2.1, "test_reference.wav")
    
    if not test_tts or not test_ref:
        print("❌ Failed to create test files")
        return False
    
    try:
        # Test the extension process
        print("🔄 Testing TTS audio extension...")
        extended_tts = test_extend_short_audio_function(test_tts, 3.0)
        
        print("🔄 Testing reference audio extension...")
        extended_ref = test_extend_short_audio_function(test_ref, 5.0)
        
        if extended_tts and extended_ref:
            print("✅ Audio extension test passed!")
            
            # Simulate OpenVoice command (without actually running it)
            print(f"\n🎭 Would run OpenVoice with:")
            print(f"   TTS: {extended_tts}")
            print(f"   REF: {extended_ref}")
            
            return True
        else:
            print("❌ Audio extension test failed")
            return False
    
    finally:
        # Clean up test files
        for file in [test_tts, test_ref]:
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass
        
        # Clean up extended files
        for pattern in ["*_extended.wav"]:
            import glob
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                except:
                    pass

def check_file_permissions():
    """Check if we have proper file permissions in the current directory"""
    print(f"\n🔐 FILE PERMISSIONS CHECK")
    print("-" * 40)
    
    test_file = "permission_test.txt"
    try:
        # Test write permission
        with open(test_file, 'w') as f:
            f.write("test")
        print("✅ Write permission: OK")
        
        # Test read permission
        with open(test_file, 'r') as f:
            content = f.read()
        print("✅ Read permission: OK")
        
        # Test delete permission
        os.remove(test_file)
        print("✅ Delete permission: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Permission error: {e}")
        return False

def check_temp_directory():
    """Check if temporary directory is accessible"""
    print(f"\n📁 TEMP DIRECTORY CHECK")
    print("-" * 40)
    
    try:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
            f.write(b"test")
        
        print(f"✅ Temp file created: {temp_file}")
        
        # Clean up
        os.unlink(temp_file)
        print("✅ Temp file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Temp directory error: {e}")
        return False

def main():
    """Run all debugging tests"""
    print("🚀 DEEP AUDIO EXTENSION DEBUGGING")
    print("=" * 60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"Platform: {sys.platform}")
    print("=" * 60)
    
    # Run all checks
    tests = [
        ("System Requirements", check_system_requirements),
        ("File Permissions", check_file_permissions),
        ("Temp Directory", check_temp_directory),
        ("OpenVoice Call Simulation", test_openvoice_call_simulation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name.upper()} {'='*20}")
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if not results.get("System Requirements"):
        print("- Install FFmpeg and ensure it's in PATH")
        print("- Verify Python environment is properly set up")
    
    if not results.get("File Permissions"):
        print("- Check directory write permissions")
        print("- Try running as administrator if needed")
    
    if not results.get("Temp Directory"):
        print("- Check TEMP environment variable")
        print("- Ensure temp directory has sufficient space")
    
    if not results.get("OpenVoice Call Simulation"):
        print("- Audio extension logic may need fixes")
        print("- Check FFmpeg installation and functionality")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! The audio extension should work properly.")
    else:
        print(f"\n⚠️ Some tests failed. Please address the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()
