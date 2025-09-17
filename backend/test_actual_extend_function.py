#!/usr/bin/env python3
"""
Test the actual extend_short_audio function from generate.py
This script imports and tests the exact function used in the main script
"""

import os
import sys
import subprocess
import tempfile

# Add the current directory to Python path so we can import from generate.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_audio(duration=1.5, filename="test_audio.wav"):
    """Create a test audio file with specific duration"""
    print(f"📝 Creating test audio: {filename} ({duration}s)")
    
    try:
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', f'sine=frequency=440:duration={duration}',
            '-ar', '24000', '-ac', '1', filename
        ], check=True, capture_output=True)
        
        return filename
    except Exception as e:
        print(f"❌ Failed to create test audio: {e}")
        return None

def test_actual_extend_function():
    """Test the actual extend_short_audio function from generate.py"""
    print("🧪 TESTING ACTUAL EXTEND_SHORT_AUDIO FUNCTION")
    print("=" * 50)
    
    try:
        # Import the function from generate.py
        print("📥 Importing extend_short_audio from generate.py...")
        from generate import extend_short_audio
        print("✅ Successfully imported extend_short_audio function")
        
        # Create test files with different durations
        test_cases = [
            (1.2, 3.0, "Short TTS audio"),
            (2.1, 5.0, "Short reference audio"), 
            (4.0, 3.0, "Already long enough audio")
        ]
        
        all_passed = True
        
        for i, (audio_duration, min_duration, description) in enumerate(test_cases):
            print(f"\n--- Test Case {i+1}: {description} ---")
            
            # Create test audio
            test_file = f"test_case_{i+1}.wav"
            if not create_test_audio(audio_duration, test_file):
                print(f"❌ Failed to create test file for case {i+1}")
                all_passed = False
                continue
            
            try:
                print(f"🔄 Testing extend_short_audio({test_file}, {min_duration})")
                
                # Call the actual function
                result = extend_short_audio(test_file, min_duration)
                
                if result:
                    print(f"✅ Function returned: {result}")
                    
                    # Verify the result file exists and has correct duration
                    if os.path.exists(result):
                        # Check duration
                        duration_result = subprocess.run([
                            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                            '-of', 'csv=p=0', result
                        ], capture_output=True, text=True, check=True)
                        
                        actual_duration = float(duration_result.stdout.strip())
                        print(f"📊 Actual output duration: {actual_duration:.2f}s")
                        
                        if actual_duration >= min_duration:
                            print(f"✅ Test case {i+1} PASSED")
                        else:
                            print(f"❌ Test case {i+1} FAILED: Duration too short")
                            all_passed = False
                    else:
                        print(f"❌ Test case {i+1} FAILED: Output file doesn't exist")
                        all_passed = False
                else:
                    print(f"❌ Test case {i+1} FAILED: Function returned None/False")
                    all_passed = False
                
            except Exception as e:
                print(f"❌ Test case {i+1} FAILED with exception: {e}")
                import traceback
                traceback.print_exc()
                all_passed = False
            
            finally:
                # Clean up test files
                for pattern in [test_file, f"test_case_{i+1}_extended.wav"]:
                    if os.path.exists(pattern):
                        try:
                            os.remove(pattern)
                            print(f"🗑️ Cleaned up: {pattern}")
                        except:
                            pass
        
        print(f"\n{'='*50}")
        if all_passed:
            print("🎉 ALL TESTS PASSED! The extend_short_audio function works correctly.")
        else:
            print("❌ SOME TESTS FAILED! Check the errors above.")
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ Failed to import extend_short_audio: {e}")
        print("💡 Make sure generate.py is in the current directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_current_directory_setup():
    """Test if the current directory has the necessary files"""
    print("📁 CHECKING CURRENT DIRECTORY SETUP")
    print("=" * 50)
    
    required_files = [
        "generate.py",
        "requirements.txt"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ Found: {file}")
        else:
            print(f"❌ Missing: {file}")
    
    # List some files in the directory
    print(f"\n📋 Files in current directory:")
    try:
        files = [f for f in os.listdir('.') if f.endswith('.py')][:10]  # Show up to 10 .py files
        for file in files:
            print(f"   - {file}")
    except:
        pass

def main():
    """Run the test"""
    print(f"🚀 TESTING ACTUAL EXTEND_SHORT_AUDIO FUNCTION")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)
    
    # Check setup first
    test_current_directory_setup()
    
    # Test the actual function
    success = test_actual_extend_function()
    
    if success:
        print(f"\n🎯 CONCLUSION: The extend_short_audio function is working correctly!")
        print("   If you're still getting 'input audio is too short' errors,")
        print("   the issue might be:")
        print("   1. The function is not being called at all")
        print("   2. OpenVoice is using different audio files")
        print("   3. There's an error in the OpenVoice call itself")
    else:
        print(f"\n⚠️ CONCLUSION: The extend_short_audio function has issues!")
        print("   This explains why you're getting the 'input audio is too short' error.")

if __name__ == "__main__":
    main()
