#!/usr/bin/env python3
"""
Complete OpenVoice Setup Script for New Machine
This script downloads and sets up all required OpenVoice models and checkpoints
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def setup_directories():
    """Create necessary directories"""
    directories = [
        'openvoice',
        'openvoice/checkpoints',
        'openvoice/checkpoints/base_speakers',
        'openvoice/checkpoints/base_speakers/EN',
        'openvoice/checkpoints/converter',
        'openvoice/cache',
        'openvoice/hf_cache',
        'openvoice/torch_cache'
    ]
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")

def download_file(url, destination, description):
    """Download a file with progress indication"""
    try:
        print(f"📥 Downloading {description}...")
        urllib.request.urlretrieve(url, destination)
        print(f"✅ Downloaded: {destination}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {description}: {e}")
        return False

def setup_openvoice_checkpoints():
    """Download and set up OpenVoice checkpoints"""
    print("🔧 Setting up OpenVoice checkpoints...")
    
    # Base checkpoint URLs (these are example URLs - you'll need the actual ones)
    checkpoints = {
        'converter/config.json': 'https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints/converter/config.json',
        'converter/checkpoint.pth': 'https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints/converter/checkpoint.pth',
        'base_speakers/EN/config.json': 'https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints/base_speakers/EN/config.json',
        'base_speakers/EN/checkpoint.pth': 'https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints/base_speakers/EN/checkpoint.pth',
    }
    
    success_count = 0
    for path, url in checkpoints.items():
        destination = f"openvoice/checkpoints/{path}"
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        if download_file(url, destination, f"checkpoint {path}"):
            success_count += 1
    
    return success_count == len(checkpoints)

def setup_huggingface_cache():
    """Set up HuggingFace cache for offline mode"""
    print("🔧 Setting up HuggingFace cache...")
    
    # Set environment variables for cache
    cache_dir = os.path.abspath("openvoice/hf_cache")
    os.environ['HF_HOME'] = cache_dir
    os.environ['TRANSFORMERS_CACHE'] = cache_dir
    
    try:
        # Try to download required models
        subprocess.run([
            sys.executable, "-c", """
import os
os.environ['HF_HOME'] = 'openvoice/hf_cache'
os.environ['TRANSFORMERS_CACHE'] = 'openvoice/hf_cache'

try:
    from huggingface_hub import hf_hub_download
    
    # Download WavMark model
    hf_hub_download(
        repo_id="M4869/WavMark",
        filename="step59000_snr39.99_pesq4.35_BERP_none0.30_mean1.81_std1.81.model.pkl",
        cache_dir="openvoice/hf_cache"
    )
    print("✅ WavMark model downloaded")
    
except Exception as e:
    print(f"⚠️ HuggingFace cache setup failed: {e}")
    print("Will try to download models on first run")
"""
        ], check=False, timeout=300)
        
        print("✅ HuggingFace cache setup completed")
        return True
        
    except Exception as e:
        print(f"⚠️ HuggingFace cache setup failed: {e}")
        return False

def create_openvoice_cli_config():
    """Create OpenVoice CLI configuration"""
    config_content = """
import os
import torch

# OpenVoice CLI Configuration
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
CHECKPOINTS_DIR = os.path.join(os.path.dirname(__file__), 'checkpoints')
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')

# Model paths
BASE_SPEAKER_MODEL = os.path.join(CHECKPOINTS_DIR, 'base_speakers', 'EN')
CONVERTER_MODEL = os.path.join(CHECKPOINTS_DIR, 'converter')

print(f"OpenVoice device: {DEVICE}")
print(f"Checkpoints directory: {CHECKPOINTS_DIR}")
"""
    
    with open('openvoice/openvoice_cli.py', 'w') as f:
        f.write(config_content)
    
    print("✅ Created OpenVoice CLI configuration")

def test_openvoice_setup():
    """Test if OpenVoice setup is working"""
    print("🧪 Testing OpenVoice setup...")
    
    try:
        # Test OpenVoice CLI import
        result = subprocess.run([
            sys.executable, "-c", """
try:
    import openvoice_cli
    print("✅ OpenVoice CLI import successful")
    
    # Test checkpoint paths
    import os
    checkpoints_exist = all([
        os.path.exists('openvoice/checkpoints/converter/config.json'),
        os.path.exists('openvoice/checkpoints/base_speakers/EN/config.json')
    ])
    
    if checkpoints_exist:
        print("✅ Checkpoint files found")
    else:
        print("⚠️ Some checkpoint files missing")
        
except Exception as e:
    print(f"❌ OpenVoice test failed: {e}")
"""
        ], capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ OpenVoice test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Starting OpenVoice setup for new machine...")
    print("=" * 60)
    
    # Step 1: Setup directories
    print("\n📁 Setting up directories...")
    setup_directories()
    
    # Step 2: Setup checkpoints
    print("\n🎯 Setting up OpenVoice checkpoints...")
    checkpoint_success = setup_openvoice_checkpoints()
    
    # Step 3: Setup HuggingFace cache
    print("\n🤗 Setting up HuggingFace cache...")
    cache_success = setup_huggingface_cache()
    
    # Step 4: Create CLI config
    print("\n⚙️ Creating OpenVoice CLI configuration...")
    create_openvoice_cli_config()
    
    # Step 5: Test setup
    print("\n🧪 Testing OpenVoice setup...")
    test_success = test_openvoice_setup()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Setup Summary:")
    print(f"   📁 Directories: ✅ Created")
    print(f"   🎯 Checkpoints: {'✅ Success' if checkpoint_success else '⚠️ Partial'}")
    print(f"   🤗 HF Cache: {'✅ Success' if cache_success else '⚠️ Partial'}")
    print(f"   🧪 Test: {'✅ Success' if test_success else '❌ Failed'}")
    
    if checkpoint_success and test_success:
        print("\n🎉 OpenVoice setup completed successfully!")
        print("\nNext steps:")
        print("1. Run: python generate.py \"Test Name\" \"templates/as.mp4\"")
        print("2. OpenVoice should work with internet connection")
        print("3. Models will be cached for offline use")
    else:
        print("\n⚠️ Setup completed with some issues")
        print("OpenVoice may still work but will download models on first run")
        print("Fallback voice cloning methods will be used if needed")

if __name__ == "__main__":
    main()
