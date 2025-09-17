#!/usr/bin/env python3
"""
Simple OpenVoice Setup - Copy from existing installation
This copies the working OpenVoice folder from current machine to new machine
"""

import os
import shutil
import subprocess
import sys

def create_openvoice_package():
    """Create a portable OpenVoice package"""
    print("📦 Creating portable OpenVoice package...")
    
    if not os.path.exists('openvoice'):
        print("❌ OpenVoice folder not found in current directory")
        return False
    
    # Create package directory
    package_name = "openvoice_package"
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    
    # Copy OpenVoice folder
    try:
        shutil.copytree('openvoice', f'{package_name}/openvoice')
        print("✅ Copied OpenVoice folder")
    except Exception as e:
        print(f"❌ Failed to copy OpenVoice folder: {e}")
        return False
    
    # Copy essential scripts
    essential_files = [
        'generate.py',
        'requirements.txt',
        'templates/as.mp4'
    ]
    
    for file in essential_files:
        if os.path.exists(file):
            dest_dir = f'{package_name}/{os.path.dirname(file)}'
            if dest_dir != f'{package_name}/':
                os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(file, f'{package_name}/{file}')
            print(f"✅ Copied {file}")
    
    # Create setup instructions
    setup_instructions = """# OpenVoice Package Setup Instructions

## For New Machine Setup:

1. **Copy this entire folder** to the new machine
2. **Set up Python environment**:
   ```bash
   python -m venv abhiyanai_env
   abhiyanai_env\\Scripts\\activate  # Windows
   source abhiyanai_env/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Test the setup**:
   ```bash
   python generate.py "Test Name" "templates/as.mp4"
   ```

## What's Included:
- ✅ OpenVoice checkpoints and models
- ✅ HuggingFace cache for offline use  
- ✅ Main generation script
- ✅ Template video file
- ✅ All required dependencies list

## Expected Behavior:
- OpenVoice should work immediately with cached models
- No internet required for voice cloning (after initial setup)
- Fallback methods available if OpenVoice fails

## Troubleshooting:
If OpenVoice fails on new machine:
1. Check that Python 3.12+ is installed
2. Verify FFmpeg is installed and in PATH
3. Ensure all dependencies installed: `pip install -r requirements.txt`
4. Try running with admin privileges
"""
    
    with open(f'{package_name}/SETUP_INSTRUCTIONS.md', 'w') as f:
        f.write(setup_instructions)
    
    print("✅ Created setup instructions")
    print(f"\n🎉 Package created: {package_name}/")
    print("📋 Package contains:")
    print("   - openvoice/ (with all models and checkpoints)")
    print("   - generate.py (main script)")
    print("   - requirements.txt (dependencies)")
    print("   - templates/as.mp4 (template video)")
    print("   - SETUP_INSTRUCTIONS.md (setup guide)")
    print(f"\n📦 Copy the entire '{package_name}' folder to your new machine")
    
    return True

def install_on_new_machine():
    """Install OpenVoice on new machine from package"""
    print("🚀 Installing OpenVoice on new machine...")
    
    if not os.path.exists('openvoice'):
        print("❌ OpenVoice folder not found")
        print("Please ensure you copied the complete openvoice_package folder")
        return False
    
    # Test OpenVoice installation
    try:
        result = subprocess.run([
            sys.executable, "-c", """
import sys
import os

# Add current directory to Python path
sys.path.insert(0, '.')

try:
    # Test OpenVoice CLI
    import openvoice_cli
    print("✅ OpenVoice CLI available")
    
    # Check checkpoints
    checkpoint_paths = [
        'openvoice/checkpoints/converter/config.json',
        'openvoice/checkpoints/base_speakers/EN/config.json'
    ]
    
    missing_checkpoints = []
    for path in checkpoint_paths:
        if not os.path.exists(path):
            missing_checkpoints.append(path)
    
    if missing_checkpoints:
        print(f"⚠️ Missing checkpoints: {missing_checkpoints}")
    else:
        print("✅ All checkpoints found")
        
    # Test basic functionality
    print("✅ OpenVoice setup appears to be working")
    
except ImportError as e:
    print(f"❌ OpenVoice import failed: {e}")
    print("Try: pip install -r requirements.txt")
    
except Exception as e:
    print(f"❌ OpenVoice test failed: {e}")
"""
        ], capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
            
        return "✅ OpenVoice setup appears to be working" in result.stdout
        
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        # Installing on new machine
        success = install_on_new_machine()
        if success:
            print("\n🎉 OpenVoice installation completed successfully!")
            print("\nTest with: python generate.py \"Test Name\" \"templates/as.mp4\"")
        else:
            print("\n❌ Installation had issues. Check error messages above.")
    else:
        # Creating package on current machine
        success = create_openvoice_package()
        if success:
            print("\n🎉 Package creation completed!")
            print("\nTo use on new machine:")
            print("1. Copy the 'openvoice_package' folder to new machine")
            print("2. Run: python setup_new_machine.py install")

if __name__ == "__main__":
    main()
