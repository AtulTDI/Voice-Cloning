#!/usr/bin/env python3
"""
Test script to check OpenVoice model availability and configuration
"""

import os
import subprocess
import sys

def check_openvoice_models():
    """Check if OpenVoice models are available"""
    print("🔍 Checking OpenVoice model availability...")
    
    try:
        # Check if openvoice_cli is available
        result = subprocess.run([
            sys.executable, "-m", "openvoice_cli", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ OpenVoice CLI is available")
        else:
            print(f"❌ OpenVoice CLI failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ OpenVoice CLI not found: {e}")
        return False
    
    # Check HuggingFace cache directory
    hf_cache = os.path.expanduser("~/.cache/huggingface")
    if os.path.exists(hf_cache):
        print(f"📁 HuggingFace cache found: {hf_cache}")
        
        # Look for WavMark models
        import glob
        wavmark_files = glob.glob(f"{hf_cache}/**/WavMark*", recursive=True)
        if wavmark_files:
            print(f"✅ Found {len(wavmark_files)} WavMark model files")
        else:
            print("⚠️ No WavMark models found in cache")
            
        # Look for OpenVoice models  
        openvoice_files = glob.glob(f"{hf_cache}/**/open*voice*", recursive=True)
        if openvoice_files:
            print(f"✅ Found {len(openvoice_files)} OpenVoice model files")
        else:
            print("⚠️ No OpenVoice models found in cache")
            
    else:
        print("⚠️ HuggingFace cache directory not found")
    
    # Test basic model loading
    try:
        print("🧪 Testing model loading (online)...")
        
        # Set environment for online test
        env = os.environ.copy()
        env.update({
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',  
            'SSL_VERIFY': '0',
            'PYTHONHTTPSVERIFY': '0'
        })
        
        # Try to load models by running a quick test
        test_script = """
import sys
try:
    from openvoice_cli.api import ToneColorConverter
    import os
    
    # Try to initialize with checkpoints
    ckpt_base = 'checkpoints/base_speakers/EN'
    ckpt_converter = 'checkpoints/converter'
    
    if os.path.exists(ckpt_base) and os.path.exists(ckpt_converter):
        tone_color_converter = ToneColorConverter(
            os.path.join(ckpt_converter, 'config.json'), device='cpu'
        )
        print('✅ Model loading successful')
    else:
        print('⚠️ Checkpoint directories not found')
        
except Exception as e:
    print(f'❌ Model loading failed: {e}')
"""
        
        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, env=env, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Model loading test failed: {e}")
    
    # Test offline mode
    try:
        print("🧪 Testing offline mode...")
        
        env_offline = os.environ.copy()
        env_offline.update({
            'CURL_CA_BUNDLE': '',
            'REQUESTS_CA_BUNDLE': '',
            'SSL_VERIFY': '0', 
            'PYTHONHTTPSVERIFY': '0',
            'HF_HUB_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1'
        })
        
        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, env=env_offline, timeout=30)
        
        print("Offline test:")
        print(result.stdout)
        if result.stderr:
            print(f"Offline stderr: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Offline test failed: {e}")
    
    return True

if __name__ == "__main__":
    check_openvoice_models()
