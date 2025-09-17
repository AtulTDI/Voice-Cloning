#!/usr/bin/env python3
"""
COMPREHENSIVE DEBUGGING PACKAGE FOR OTHER MACHINE
Run this script on the machine experiencing the "input audio is too short" error
to identify exactly what's happening
"""

import os
import sys
import subprocess
import datetime
import platform
import tempfile

def log(message):
    """Print message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

def run_system_diagnostics():
    """Run comprehensive system diagnostics"""
    log("🚀 STARTING COMPREHENSIVE SYSTEM DIAGNOSTICS")
    log("=" * 80)
    
    # Basic system info
    log(f"💻 System Information:")
    log(f"   Platform: {platform.platform()}")
    log(f"   Python version: {sys.version}")
    log(f"   Python executable: {sys.executable}")
    log(f"   Working directory: {os.getcwd()}")
    log(f"   Current user: {os.getenv('USER', os.getenv('USERNAME', 'unknown'))}")
    
    # Environment variables
    log(f"\n🌍 Relevant Environment Variables:")
    env_vars = ['PATH', 'TEMP', 'TMP', 'PYTHONPATH', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV']
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        if var == 'PATH':
            # Show only first few PATH entries
            if len(value) > 200:
                value = value[:200] + "..."
        log(f"   {var}: {value}")

def check_dependencies():
    """Check all required dependencies"""
    log("\n🔍 DEPENDENCY CHECK")
    log("-" * 40)
    
    checks = {
        'python': [sys.executable, '--version'],
        'ffmpeg': ['ffmpeg', '-version'],
        'ffprobe': ['ffprobe', '-version'],
        'pip': [sys.executable, '-m', 'pip', '--version']
    }
    
    results = {}
    for tool, cmd in checks.items():
        log(f"Checking {tool}...")
        try:
            result = subprocess.run(cmd[:2], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0][:100]  # First 100 chars
                log(f"✅ {tool}: {version}")
                results[tool] = True
            else:
                log(f"❌ {tool}: Failed with return code {result.returncode}")
                results[tool] = False
        except FileNotFoundError:
            log(f"❌ {tool}: Command not found")
            results[tool] = False
        except Exception as e:
            log(f"❌ {tool}: Error - {e}")
            results[tool] = False
    
    return results

def check_file_structure():
    """Check if all required files are present"""
    log("\n📁 FILE STRUCTURE CHECK")
    log("-" * 40)
    
    required_files = [
        'generate.py',
        'requirements.txt',
        'backend/templates/as.mp4',
        'backend/tts'
    ]
    
    optional_files = [
        'openvoice',
        'checkpoints',
        'cache'
    ]
    
    log("Required files:")
    all_present = True
    for file in required_files:
        if os.path.exists(file):
            if os.path.isfile(file):
                size = os.path.getsize(file)
                log(f"✅ {file} ({size} bytes)")
            else:
                log(f"✅ {file} (directory)")
        else:
            log(f"❌ Missing: {file}")
            all_present = False
    
    log("\nOptional files:")
    for file in optional_files:
        if os.path.exists(file):
            log(f"✅ {file}")
        else:
            log(f"⚠️ Not found: {file}")
    
    return all_present

def test_audio_creation():
    """Test basic audio file creation"""
    log("\n🎵 AUDIO CREATION TEST")
    log("-" * 40)
    
    test_file = "diagnostic_test_audio.wav"
    try:
        log("Creating test audio file...")
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'sine=frequency=440:duration=1.5',
            '-ar', '24000', '-ac', '1', test_file
        ], check=True, capture_output=True)
        
        if os.path.exists(test_file):
            size = os.path.getsize(test_file)
            log(f"✅ Test audio created: {test_file} ({size} bytes)")
            
            # Get duration
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', test_file
            ], capture_output=True, text=True, check=True)
            
            duration = float(result.stdout.strip())
            log(f"✅ Audio duration: {duration:.2f}s")
            
            # Clean up
            os.remove(test_file)
            log("🗑️ Cleaned up test file")
            return True
        else:
            log("❌ Test audio file was not created")
            return False
            
    except Exception as e:
        log(f"❌ Audio creation test failed: {e}")
        return False

def test_extend_function():
    """Test the extend_short_audio function if available"""
    log("\n🧪 EXTEND_SHORT_AUDIO FUNCTION TEST")
    log("-" * 40)
    
    try:
        # Try to import the function
        log("Attempting to import extend_short_audio from generate.py...")
        if not os.path.exists('generate.py'):
            log("❌ generate.py not found")
            return False
        
        sys.path.insert(0, os.getcwd())
        from generate import extend_short_audio
        log("✅ Successfully imported extend_short_audio")
        
        # Create a test audio file
        test_file = "extend_test_audio.wav"
        log(f"Creating short test audio: {test_file}")
        
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'sine=frequency=440:duration=1.2',
            '-ar', '24000', '-ac', '1', test_file
        ], check=True, capture_output=True)
        
        log("Testing extend_short_audio function...")
        result = extend_short_audio(test_file, 3.0)
        
        if result and result != test_file:  # Function should return extended filename
            log(f"✅ Function returned: {result}")
            
            if os.path.exists(result):
                # Check duration of extended file
                duration_result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', result
                ], capture_output=True, text=True, check=True)
                
                extended_duration = float(duration_result.stdout.strip())
                log(f"✅ Extended duration: {extended_duration:.2f}s")
                
                # Clean up
                os.remove(test_file)
                os.remove(result)
                log("🗑️ Cleaned up test files")
                
                if extended_duration >= 3.0:
                    log("🎉 extend_short_audio function works correctly!")
                    return True
                else:
                    log("❌ Extended audio is still too short")
                    return False
            else:
                log(f"❌ Extended file not found: {result}")
                return False
        else:
            log(f"❌ Function failed or returned original file: {result}")
            return False
            
    except ImportError as e:
        log(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        log(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_openvoice_call():
    """Simulate the OpenVoice call to see what happens"""
    log("\n🎭 OPENVOICE CALL SIMULATION")
    log("-" * 40)
    
    try:
        # Create test files
        test_tts = "sim_tts.wav"
        test_ref = "sim_ref.wav" 
        test_output = "sim_output.wav"
        
        log("Creating simulation test files...")
        
        # Create short TTS file (this would trigger the error)
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'sine=frequency=440:duration=1.2',
            '-ar', '24000', '-ac', '1', test_tts
        ], check=True, capture_output=True)
        
        # Create short reference file
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'sine=frequency=880:duration=2.1',
            '-ar', '24000', '-ac', '1', test_ref
        ], check=True, capture_output=True)
        
        log("✅ Test files created")
        
        # Try to import and test the clone_voice function
        if os.path.exists('generate.py'):
            log("Testing clone_voice function...")
            
            # Add the specific logging to see what happens
            sys.path.insert(0, os.getcwd())
            try:
                from generate import clone_voice
                log("✅ Successfully imported clone_voice")
                
                # Call clone_voice with our test files
                log("🚀 Calling clone_voice with test files...")
                clone_voice(test_tts, test_output, test_ref)
                
                if os.path.exists(test_output):
                    log("✅ clone_voice succeeded!")
                else:
                    log("❌ clone_voice failed - no output file created")
                    
            except Exception as e:
                log(f"❌ clone_voice test failed: {e}")
                # This is where we'd see the "input audio is too short" error
                error_str = str(e).lower()
                if "too short" in error_str:
                    log("🔍 FOUND THE ISSUE: 'too short' error detected!")
                    log("   This suggests the extend_short_audio function is not working")
                    log("   or not being called properly on this machine.")
        
        # Clean up
        for file in [test_tts, test_ref, test_output]:
            if os.path.exists(file):
                os.remove(file)
        log("🗑️ Cleaned up simulation files")
        
        return True
        
    except Exception as e:
        log(f"❌ Simulation failed: {e}")
        return False

def check_python_modules():
    """Check if required Python modules are available"""
    log("\n🐍 PYTHON MODULES CHECK")
    log("-" * 40)
    
    required_modules = [
        'subprocess',
        'os',
        'sys',
        'tempfile',
        'shutil'
    ]
    
    optional_modules = [
        'pydub',
        'numpy',
        'scipy',
        'torch',
        'torchaudio'
    ]
    
    log("Required modules:")
    for module in required_modules:
        try:
            __import__(module)
            log(f"✅ {module}")
        except ImportError:
            log(f"❌ {module}")
    
    log("Optional modules:")
    for module in optional_modules:
        try:
            __import__(module)
            log(f"✅ {module}")
        except ImportError:
            log(f"⚠️ {module} (not installed)")

def generate_diagnosis():
    """Generate a diagnosis based on all tests"""
    log("\n🎯 RUNNING COMPREHENSIVE DIAGNOSIS")
    log("=" * 80)
    
    results = {}
    
    # Run all diagnostic tests
    tests = [
        ("System Info", lambda: True),  # Always passes, just informational
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure),
        ("Audio Creation", test_audio_creation),
        ("Python Modules", lambda: True),  # Always passes, just informational
        ("Extend Function", test_extend_function),
        ("OpenVoice Simulation", simulate_openvoice_call)
    ]
    
    for test_name, test_func in tests:
        log(f"\n{'='*20} {test_name.upper()} TEST {'='*20}")
        try:
            if test_name == "System Info":
                run_system_diagnostics()
                results[test_name] = True
            elif test_name == "Python Modules":
                check_python_modules()
                results[test_name] = True
            else:
                results[test_name] = test_func()
        except Exception as e:
            log(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Generate final diagnosis
    log(f"\n{'='*80}")
    log("🩺 FINAL DIAGNOSIS")
    log("="*80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"{status}: {test_name}")
    
    # Specific recommendations
    log(f"\n💡 SPECIFIC RECOMMENDATIONS:")
    
    if not results.get("Dependencies"):
        log("🔧 CRITICAL: Install missing dependencies (especially FFmpeg)")
        log("   - Download FFmpeg from https://ffmpeg.org/download.html")
        log("   - Add FFmpeg to your system PATH")
    
    if not results.get("File Structure"):
        log("📁 CRITICAL: Missing required files")
        log("   - Ensure you have the complete project structure")
        log("   - Run 'git pull' to update to latest version")
    
    if not results.get("Audio Creation"):
        log("🎵 CRITICAL: Cannot create audio files")
        log("   - This indicates FFmpeg is not working properly")
        log("   - Check FFmpeg installation and PATH")
    
    if not results.get("Extend Function"):
        log("🧪 CRITICAL: extend_short_audio function is not working")
        log("   - This is the likely cause of your 'input audio is too short' error")
        log("   - Check if generate.py has the latest code")
        log("   - Try running: python add_debugging_logs.py")
    
    if not results.get("OpenVoice Simulation"):
        log("🎭 WARNING: OpenVoice simulation failed")
        log("   - This could indicate broader issues with the voice cloning pipeline")
    
    # Overall conclusion
    critical_failures = sum(1 for k, v in results.items() if not v and k in ["Dependencies", "Audio Creation", "Extend Function"])
    
    if critical_failures == 0:
        log(f"\n🎉 GOOD NEWS: All critical tests passed!")
        log("   The 'input audio is too short' error might be intermittent")
        log("   or related to specific audio files. Try running the main script again.")
    elif critical_failures == 1:
        log(f"\n⚠️ MODERATE ISSUE: One critical test failed")
        log("   Fix the issue above and the 'input audio is too short' error should resolve")
    else:
        log(f"\n❌ SERIOUS ISSUES: Multiple critical tests failed")
        log("   You need to fix the dependency and setup issues before proceeding")
    
    return results

def main():
    """Main diagnostic function"""
    log("🚀 STARTING COMPREHENSIVE MACHINE DIAGNOSTICS")
    log(f"Timestamp: {datetime.datetime.now()}")
    log("="*80)
    
    try:
        results = generate_diagnosis()
        
        log(f"\n📋 NEXT STEPS:")
        log("1. Fix any CRITICAL issues identified above")
        log("2. If extend_short_audio test failed, run: python add_debugging_logs.py")
        log("3. Run your video generation script and look for the detailed logs")
        log("4. If issues persist, share this diagnostic output for further analysis")
        
        return results
        
    except Exception as e:
        log(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return {}

if __name__ == "__main__":
    main()
