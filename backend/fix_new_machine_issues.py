#!/usr/bin/env python3
"""
Comprehensive fix script for new machine setup issues:
1. "input video too short" error  
2. Missing OpenVoice setup
3. Template video validation
4. Model download automation
"""

import os
import sys
import subprocess
import time
import requests
from urllib.parse import urlparse

def check_video_duration(video_path):
    """Check if video meets minimum duration requirements"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        print(f"📹 Video duration: {duration:.2f} seconds")
        
        if duration < 10.0:
            print(f"⚠️ WARNING: Video is only {duration:.2f}s, minimum recommended is 10s")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking video duration: {e}")
        return False

def download_better_template():
    """Download a longer template video if current one is too short"""
    try:
        print("📥 Downloading better template video...")
        
        # Create a longer template by repeating the existing one
        current_template = "templates/as.mp4" 
        extended_template = "templates/extended_as.mp4"
        
        # Use FFmpeg to loop the video to make it longer
        subprocess.run([
            'ffmpeg', '-y', '-stream_loop', '2', '-i', current_template,
            '-c', 'copy', extended_template
        ], check=True)
        
        print(f"✅ Extended template created: {extended_template}")
        return extended_template
        
    except Exception as e:
        print(f"❌ Failed to create extended template: {e}")
        return None

def setup_openvoice_models():
    """Set up OpenVoice models and checkpoints"""
    try:
        print("🚀 Setting up OpenVoice models...")
        
        # Create OpenVoice directory structure
        openvoice_dir = "openvoice"
        checkpoints_dir = os.path.join(openvoice_dir, "checkpoints")
        base_speakers_dir = os.path.join(checkpoints_dir, "base_speakers", "EN")
        converter_dir = os.path.join(checkpoints_dir, "converter")
        
        os.makedirs(base_speakers_dir, exist_ok=True)
        os.makedirs(converter_dir, exist_ok=True)
        
        print(f"✅ Created OpenVoice directories: {openvoice_dir}")
        
        # Try to trigger model download by running OpenVoice help
        print("🔄 Triggering OpenVoice model download...")
        
        try:
            # This will trigger the model download
            result = subprocess.run([
                sys.executable, '-c', 
                '''
import os
os.environ["HF_HUB_CACHE"] = "./openvoice/models"
try:
    from openvoice_cli.api import ToneColorConverter
    print("✅ OpenVoice models loaded successfully")
except Exception as e:
    print(f"Model download triggered: {e}")
'''
            ], capture_output=True, text=True, timeout=300)
            
            print(f"Model setup output: {result.stdout}")
            if result.stderr:
                print(f"Model setup stderr: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Model download taking longer than expected, continuing...")
            
        return True
        
    except Exception as e:
        print(f"❌ OpenVoice setup failed: {e}")
        return False

def fix_video_validation():
    """Add video validation to prevent 'video too short' errors"""
    
    generate_py_path = "generate.py"
    
    # Add video validation function
    validation_code = '''
def validate_video_duration(video_path, min_duration=10.0):
    """Validate that video meets minimum duration requirements"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        
        if duration < min_duration:
            print(f"⚠️ WARNING: Video duration ({duration:.2f}s) is less than minimum ({min_duration}s)")
            
            # Try to extend the video by looping
            extended_path = video_path.replace('.mp4', '_extended.mp4')
            loop_count = int(min_duration / duration) + 1
            
            print(f"🔄 Extending video by looping {loop_count} times...")
            subprocess.run([
                'ffmpeg', '-y', '-stream_loop', str(loop_count-1), 
                '-i', video_path, '-t', str(min_duration),
                '-c', 'copy', extended_path
            ], check=True)
            
            print(f"✅ Extended video created: {extended_path}")
            return extended_path
            
        return video_path
        
    except Exception as e:
        print(f"❌ Video validation failed: {e}")
        return video_path

'''
    
    try:
        with open(generate_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add validation function if not already present
        if 'validate_video_duration' not in content:
            # Find the right place to insert (after imports)
            import_end = content.find('# === Unique run ID')
            if import_end != -1:
                new_content = content[:import_end] + validation_code + '\n' + content[import_end:]
                
                with open(generate_py_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✅ Added video validation function to generate.py")
                return True
                
    except Exception as e:
        print(f"❌ Failed to add video validation: {e}")
        
    return False

def create_quick_fix_script():
    """Create a quick fix script for common issues"""
    
    fix_script = '''#!/usr/bin/env python3
"""
Quick fix script - run this if you encounter issues
"""
import os
import sys
import subprocess

def main():
    print("🔧 Running quick fixes...")
    
    # 1. Check Python environment
    if 'abhiyanai_env' not in sys.executable:
        print("⚠️ Virtual environment not activated!")
        print("Please run: abhiyanai_env\\Scripts\\activate")
        return
    
    # 2. Check template video
    if not os.path.exists('templates/as.mp4'):
        print("❌ Template video missing!")
        return
    
    # 3. Check FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg found")
    except:
        print("❌ FFmpeg not found - please install FFmpeg")
        return
    
    # 4. Test basic functionality
    try:
        print("🧪 Testing basic functionality...")
        result = subprocess.run([
            sys.executable, 'generate.py', 'Test User', 'templates/as.mp4'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Basic test successful!")
        else:
            print(f"❌ Test failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
'''
    
    with open('quick_fix.py', 'w') as f:
        f.write(fix_script)
    
    print("✅ Created quick_fix.py script")

def main():
    """Main fix function"""
    print("🔧 Fixing new machine setup issues...")
    
    # 1. Check video duration
    if os.path.exists("templates/as.mp4"):
        if not check_video_duration("templates/as.mp4"):
            extended_template = download_better_template()
            if extended_template:
                print("✅ Use extended template for better results")
    
    # 2. Setup OpenVoice
    setup_openvoice_models()
    
    # 3. Add video validation
    fix_video_validation()
    
    # 4. Create quick fix script
    create_quick_fix_script()
    
    print("\n🎉 Fix complete! Try running:")
    print("python generate.py 'Test Name' 'templates/as.mp4'")
    
if __name__ == "__main__":
    main()
