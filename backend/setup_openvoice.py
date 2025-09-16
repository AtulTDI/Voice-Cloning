#!/usr/bin/env python3
"""
OpenVoice Setup Script
This script sets up OpenVoice for TTS generation and voice cloning.
Run this on a machine with internet access to download all required models.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description, check=True):
    """Run a command and print status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def setup_openvoice():
    """Set up OpenVoice with all required models"""
    
    print("🚀 Setting up OpenVoice for offline voice cloning...")
    
    # 1. Install required packages
    packages = [
        "torch>=1.13.0",
        "torchaudio>=0.13.0",
        "openvoice",
        "librosa>=0.10.0", 
        "soundfile",
        "scipy",
        "numpy",
        "transformers>=4.21.0",
        "datasets",
        "accelerate",
        "huggingface_hub"
    ]
    
    for package in packages:
        run_command(f"pip install {package}", f"Installing {package}")
    
    # 2. Create OpenVoice directory structure
    openvoice_dir = Path("openvoice")
    openvoice_dir.mkdir(exist_ok=True)
    
    checkpoints_dir = openvoice_dir / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)
    
    # 3. Download OpenVoice models
    print("📥 Downloading OpenVoice models...")
    
    # Download from HuggingFace
    model_commands = [
        "huggingface-cli download myshell-ai/OpenVoice checkpoints/base_speakers/EN --local-dir ./openvoice",
        "huggingface-cli download myshell-ai/OpenVoice checkpoints/converter --local-dir ./openvoice", 
        "huggingface-cli download myshell-ai/OpenVoice openvoice --local-dir ./openvoice"
    ]
    
    for cmd in model_commands:
        run_command(cmd, f"Downloading models: {cmd.split()[-1]}")
    
    # 4. Alternative: Clone OpenVoice repository
    if not (openvoice_dir / "api.py").exists():
        print("📥 Cloning OpenVoice repository...")
        run_command("git clone https://github.com/myshell-ai/OpenVoice.git temp_openvoice", "Cloning OpenVoice repo")
        
        # Copy necessary files
        temp_dir = Path("temp_openvoice")
        if temp_dir.exists():
            for file in temp_dir.glob("*.py"):
                shutil.copy2(file, openvoice_dir)
            
            if (temp_dir / "openvoice").exists():
                shutil.copytree(temp_dir / "openvoice", openvoice_dir / "openvoice", dirs_exist_ok=True)
            
            if (temp_dir / "checkpoints").exists():
                shutil.copytree(temp_dir / "checkpoints", openvoice_dir / "checkpoints", dirs_exist_ok=True)
            
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 5. Create cache directories for offline operation
    cache_dirs = [
        openvoice_dir / "cache",
        openvoice_dir / "hf_cache", 
        openvoice_dir / "torch_cache"
    ]
    
    for cache_dir in cache_dirs:
        cache_dir.mkdir(exist_ok=True)
    
    # 6. Download additional models that might be needed
    additional_models = [
        "facebook/wav2vec2-base-960h",
        "microsoft/speecht5_tts",
        "espnet/hindi_male_fgl"  # Hindi TTS model
    ]
    
    for model in additional_models:
        run_command(
            f"python -c \"from transformers import pipeline; pipeline('automatic-speech-recognition', model='{model}')\"",
            f"Pre-loading model: {model}",
            check=False  # Don't fail if some models are not available
        )
    
    # 7. Create OpenVoice CLI wrapper
    cli_script = openvoice_dir / "openvoice_cli.py"
    cli_script.write_text('''#!/usr/bin/env python3
"""
OpenVoice CLI wrapper for voice cloning
Usage: python openvoice_cli.py single -i input.wav -r reference.wav -o output.wav
"""
import sys
import argparse
from pathlib import Path
import torch
from api import ToneColorConverter
from openvoice import se_extractor

def main():
    parser = argparse.ArgumentParser(description='OpenVoice CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Single conversion command
    single_parser = subparsers.add_parser('single', help='Single voice conversion')
    single_parser.add_argument('-i', '--input', required=True, help='Input TTS audio file')
    single_parser.add_argument('-r', '--reference', required=True, help='Reference voice file')  
    single_parser.add_argument('-o', '--output', required=True, help='Output cloned voice file')
    
    args = parser.parse_args()
    
    if args.command == 'single':
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")
            
            # Initialize converter
            ckpt_converter = Path(__file__).parent / "checkpoints" / "converter"
            converter = ToneColorConverter(str(ckpt_converter), device=device)
            
            # Extract target speaker embedding
            target_se, _ = se_extractor.get_se(args.reference, converter, target_dir='temp', vad=True)
            
            # Convert voice
            converter.convert(
                audio_src_path=args.input,
                src_se=None,
                tgt_se=target_se,
                output_path=args.output,
                message="Voice cloning in progress..."
            )
            
            print(f"✅ Voice cloning completed: {args.output}")
            
        except Exception as e:
            print(f"❌ Voice cloning failed: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
''')
    
    # 8. Make CLI executable
    run_command(f"chmod +x {cli_script}", "Making CLI executable", check=False)
    
    # 9. Test the installation
    print("🧪 Testing OpenVoice installation...")
    test_script = f'''
import torch
print(f"PyTorch version: {{torch.__version__}}")
print(f"CUDA available: {{torch.cuda.is_available()}}")

try:
    import sys
    sys.path.insert(0, "{openvoice_dir}")
    from api import ToneColorConverter
    print("✅ OpenVoice API import successful")
except ImportError as e:
    print(f"❌ OpenVoice API import failed: {{e}}")

try:
    from transformers import pipeline
    print("✅ Transformers import successful")
except ImportError as e:
    print(f"❌ Transformers import failed: {{e}}")
'''
    
    run_command(f'python -c "{test_script}"', "Testing installation", check=False)
    
    print("🎉 OpenVoice setup completed!")
    print("\n📋 Next steps:")
    print("1. Copy the 'openvoice' folder to your offline machine")
    print("2. Update the OPENVOICE_DIR path in generate_openvoice.py")
    print("3. Run the voice cloning script on the offline machine")
    print("\n⚠️ Note: Make sure PyTorch and other dependencies are installed on the offline machine")

def create_requirements_file():
    """Create requirements.txt for the offline machine"""
    requirements = """torch>=1.13.0
torchaudio>=0.13.0
transformers>=4.21.0
librosa>=0.10.0
soundfile>=0.12.0
scipy>=1.9.0
numpy>=1.21.0
datasets>=2.0.0
accelerate>=0.20.0
huggingface_hub>=0.15.0
pydub>=0.25.0
ffmpeg-python>=0.2.0
edge-tts>=6.1.0
"""
    
    with open("requirements_openvoice.txt", "w") as f:
        f.write(requirements)
    
    print("✅ Created requirements_openvoice.txt for offline installation")

if __name__ == "__main__":
    setup_openvoice()
    create_requirements_file()
