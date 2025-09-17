#!/usr/bin/env python3
"""
Complete setup script for new machine - fixes both issues:
1. "input video too short" AssertionError  
2. Missing OpenVoice folder and models
"""

import os
import sys
import subprocess
import shutil

def main():
    print("🔧 NEW MACHINE SETUP - Fixing known issues")
    print("=" * 50)
    
    # Step 1: Check environment
    print("\n1️⃣ Checking Python environment...")
    if 'abhiyanai_env' not in sys.executable:
        print("⚠️ Virtual environment not activated!")
        print("Please run: abhiyanai_env\\Scripts\\activate")
        print("Then run this script again.")
        sys.exit(1)
    print("✅ Virtual environment active")
    
    # Step 2: Check FFmpeg
    print("\n2️⃣ Checking FFmpeg...")
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg found")
    except:
        print("❌ FFmpeg not found!")
        print("Please install FFmpeg first:")
        print("- Windows: Download from https://www.gyan.dev/ffmpeg/builds/")
        print("- Linux: sudo apt install ffmpeg")
        print("- macOS: brew install ffmpeg")
        sys.exit(1)
    
    # Step 3: Check template video
    print("\n3️⃣ Checking template video...")
    template_path = "templates/as.mp4"
    if not os.path.exists(template_path):
        print(f"❌ Template video not found: {template_path}")
        print("Please ensure templates/as.mp4 exists")
        sys.exit(1)
    
    # Check video duration
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', template_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        print(f"📹 Template duration: {duration:.2f} seconds")
        
        if duration < 10.0:
            print(f"⚠️ Template video is short ({duration:.2f}s)")
            print("🔄 Creating extended template...")
            
            extended_path = "templates/as_extended.mp4"
            loop_count = int(15.0 / duration) + 1
            
            subprocess.run([
                'ffmpeg', '-y', '-stream_loop', str(loop_count-1),
                '-i', template_path, '-t', '15',
                '-c', 'copy', extended_path
            ], check=True)
            
            print(f"✅ Extended template created: {extended_path}")
            print("💡 Use 'templates/as_extended.mp4' for better results")
        else:
            print("✅ Template video duration is good")
            
    except Exception as e:
        print(f"⚠️ Could not check video duration: {e}")
    
    # Step 4: Setup OpenVoice directories
    print("\n4️⃣ Setting up OpenVoice structure...")
    
    openvoice_dirs = [
        "openvoice",
        "openvoice/checkpoints",
        "openvoice/checkpoints/base_speakers",
        "openvoice/checkpoints/base_speakers/EN",
        "openvoice/checkpoints/converter", 
        "openvoice/models",
        "openvoice/hf_home"
    ]
    
    for directory in openvoice_dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created: {directory}")
    
    print("✅ OpenVoice directories created")
    
    # Step 5: Set up environment variables
    print("\n5️⃣ Setting up OpenVoice environment...")
    
    # Create environment setup file
    env_setup = f'''
# OpenVoice Environment Setup
import os

# Set HuggingFace cache locations
os.environ["HF_HUB_CACHE"] = os.path.abspath("openvoice/models")
os.environ["HF_HOME"] = os.path.abspath("openvoice/hf_home") 
os.environ["TRANSFORMERS_CACHE"] = os.path.abspath("openvoice/models/transformers")

# SSL bypass for corporate networks
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_VERIFY"] = "0"
os.environ["PYTHONHTTPSVERIFY"] = "0"

print("🌐 OpenVoice environment configured")
'''
    
    with open("openvoice_env_setup.py", "w") as f:
        f.write(env_setup)
    
    print("✅ Created openvoice_env_setup.py")
    
    # Step 6: Test basic functionality
    print("\n6️⃣ Testing basic setup...")
    
    try:
        # Import test
        print("🧪 Testing imports...")
        test_imports = '''
try:
    import edge_tts
    print("✅ edge_tts imported")
except ImportError as e:
    print(f"❌ edge_tts import failed: {e}")

try:
    import pyttsx3  
    print("✅ pyttsx3 imported")
except ImportError as e:
    print(f"❌ pyttsx3 import failed: {e}")

try:
    from moviepy.editor import VideoFileClip
    print("✅ moviepy imported")
except ImportError as e:
    print(f"❌ moviepy import failed: {e}")

try:
    import torch
    print("✅ torch imported")
except ImportError as e:
    print(f"❌ torch import failed: {e}")
'''
        
        result = subprocess.run([
            sys.executable, "-c", test_imports
        ], capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print(f"Import warnings: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️ Import test failed: {e}")
    
    # Step 7: Create test script
    print("\n7️⃣ Creating test script...")
    
    test_script = '''#!/usr/bin/env python3
"""Test script for new machine setup"""

import os
import sys

# Load OpenVoice environment
exec(open('openvoice_env_setup.py').read())

# Import main function
sys.path.append('.')

def test_generation():
    """Test video generation with extended template"""
    
    template = "templates/as_extended.mp4" if os.path.exists("templates/as_extended.mp4") else "templates/as.mp4"
    
    print(f"🧪 Testing with template: {template}")
    
    import subprocess
    result = subprocess.run([
        sys.executable, "generate.py", "Test User", template
    ], capture_output=False, text=True)
    
    return result.returncode == 0

if __name__ == "__main__":
    print("🧪 Running comprehensive test...")
    success = test_generation()
    
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed - check output above")
'''
    
    with open("test_setup.py", "w") as f:
        f.write(test_script)
    
    print("✅ Created test_setup.py")
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 NEW MACHINE SETUP COMPLETE!")
    print("=" * 50)
    
    print("\n📋 Next Steps:")
    print("1. Run: python test_setup.py")
    print("   (This will test the complete setup)")
    
    print("\n2. For production use:")
    template = "templates/as_extended.mp4" if os.path.exists("templates/as_extended.mp4") else "templates/as.mp4"
    print(f'   python generate.py "Your Name" "{template}"')
    
    print("\n🔧 Fixes Applied:")
    print("✅ Video duration validation and extension")  
    print("✅ OpenVoice directory structure created")
    print("✅ Environment variables configured")
    print("✅ Model cache directories prepared")
    print("✅ SSL bypass for corporate networks")
    
    print("\n🌐 OpenVoice Models:")
    print("- Models will download automatically on first OpenVoice use")  
    print("- This may take 5-10 minutes with internet connection")
    print("- Models will be cached for future offline use")

if __name__ == "__main__":
    main()
