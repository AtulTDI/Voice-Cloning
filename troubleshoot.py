#!/usr/bin/env python3
"""
Voice Cloning Troubleshooting Script
Run this to diagnose common issues with the voice cloning setup
"""

import os
import sys
import subprocess
import importlib
import platform

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"🐍 Python Version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("⚠️  WARNING: Python 3.8+ recommended")
    else:
        print("✅ Python version OK")

def check_required_modules():
    """Check if required Python modules are installed"""
    required_modules = [
        'numpy', 'pandas', 'pydub', 'moviepy', 'edge_tts', 
        'pyttsx3', 'openpyxl', 'aiofiles', 'fastapi', 'uvicorn',
        'librosa', 'soundfile', 'scipy', 'torch', 'torchaudio',
        'transformers', 'datasets', 'accelerate', 'huggingface_hub'
    ]
    
    print("\n📦 Checking Python Modules:")
    missing_modules = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - MISSING")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n⚠️  Missing modules: {', '.join(missing_modules)}")
        print("💡 Install with: pip install -r backend/requirements.txt")
    else:
        print("✅ All required modules found")

def check_ffmpeg():
    """Check if FFmpeg is available"""
    print("\n🎵 Checking FFmpeg:")
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ {version_line}")
        else:
            print("❌ FFmpeg found but returned error")
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        print("💡 Install FFmpeg and add to PATH")
    except subprocess.TimeoutExpired:
        print("⚠️  FFmpeg check timed out")
    except Exception as e:
        print(f"❌ FFmpeg check failed: {e}")

def check_file_structure():
    """Check if required files and directories exist"""
    print("\n📁 Checking File Structure:")
    
    required_files = [
        'backend/generate.py',
        'backend/generate_video.py', 
        'backend/word_trimming.py',
        'backend/requirements.txt',
        'README.md'
    ]
    
    required_dirs = [
        'backend',
        'backend/templates'
    ]
    
    # Check files
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
    
    # Check directories
    for dir_path in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ - MISSING")
    
    # Check template videos
    templates_dir = 'backend/templates'
    if os.path.exists(templates_dir):
        video_files = [f for f in os.listdir(templates_dir) if f.endswith('.mp4')]
        if video_files:
            print(f"✅ Template videos: {', '.join(video_files)}")
        else:
            print("⚠️  No .mp4 template videos found")

def check_working_directory():
    """Check if running from correct directory"""
    print(f"\n📍 Current Directory: {os.getcwd()}")
    
    # Check if we're in the right place
    indicators = ['backend', 'README.md', '.git']
    found_indicators = [item for item in indicators if os.path.exists(item)]
    
    if len(found_indicators) >= 2:
        print("✅ Appears to be in correct project directory")
    else:
        print("⚠️  May not be in correct project directory")
        print("💡 Make sure you're in the Voice-Cloning project root")

def check_system_info():
    """Display system information"""
    print(f"\n💻 System Info:")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Architecture: {platform.machine()}")
    print(f"   Processor: {platform.processor()}")

def run_basic_test():
    """Run a basic test of the voice cloning system"""
    print("\n🧪 Running Basic Test:")
    
    # Check if we can import the main module
    try:
        sys.path.insert(0, 'backend')
        import generate
        print("✅ Can import generate.py")
        
        # Check if template video exists
        template_path = "backend/templates/as.mp4"
        if os.path.exists(template_path):
            print("✅ Template video found")
            print("💡 Try running: python backend/generate.py \"Test Name\" \"backend/templates/as.mp4\"")
        else:
            print("❌ Template video not found")
            
    except Exception as e:
        print(f"❌ Cannot import generate.py: {e}")

def main():
    """Main troubleshooting function"""
    print("🔧 Voice Cloning Troubleshooting Tool")
    print("=" * 50)
    
    check_python_version()
    check_system_info()
    check_working_directory()
    check_file_structure()
    check_ffmpeg()
    check_required_modules()
    run_basic_test()
    
    print("\n" + "=" * 50)
    print("🎯 Troubleshooting Complete!")
    print("\n💡 Common Solutions:")
    print("   1. Install dependencies: pip install -r backend/requirements.txt")
    print("   2. Install FFmpeg and add to PATH")
    print("   3. Use correct path: backend/templates/as.mp4 (not backend/template/as.mp4)")
    print("   4. Make sure you're in the project root directory")
    print("   5. Check Python version is 3.8+")

if __name__ == "__main__":
    main()
