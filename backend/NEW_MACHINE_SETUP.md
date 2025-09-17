# Setup Steps for New Machine with Internet 🌐

## Prerequisites
- Windows 10/11 (or Linux/macOS)
- Python 3.12+ 
- Git installed
- Internet connection (for OpenVoice model downloads)
- Administrative privileges (for FFmpeg installation)

## Step-by-Step Setup

### 1. Clone Repository
```bash
git clone https://github.com/AtulTDI/Voice-Cloning.git
cd Voice-Cloning
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv abhiyanai_env

# Windows activation
abhiyanai_env\Scripts\activate

# Linux/Mac activation  
source abhiyanai_env/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Install FFmpeg
**Windows (Recommended):**
- Download from: https://www.gyan.dev/ffmpeg/builds/
- Extract to `C:\ffmpeg`
- Add `C:\ffmpeg\bin` to PATH environment variable
- OR use chocolatey: `choco install ffmpeg`

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 5. Verify Installation
```bash
python --version    # Should show 3.12+
ffmpeg -version     # Should show 8.0+
```

### 6. Test Basic Functionality
```bash
# Navigate to backend directory
cd backend

# Test with sample name
python generate.py "Test User" "templates/as.mp4"
```

### 7. OpenVoice Setup (Internet Required)
On first run, the script will automatically:
- Download OpenVoice models from HuggingFace
- Cache models locally for future offline use
- Set up voice cloning checkpoints

**First run may take 5-10 minutes for model downloads.**

### 8. Expected Output Structure
```
Voice-Cloning/
├── backend/
│   ├── generated_videos/     # Output videos will appear here
│   ├── templates/           # Template video files
│   ├── cloned_voices/       # Temporary (auto-cleaned)
│   ├── tts/                # Temporary (auto-cleaned)
│   ├── voice_reference/     # Temporary (auto-cleaned)
│   └── generate.py          # Main script
├── abhiyanai_env/           # Python environment
└── README.md               # Documentation
```

## Quick Test Commands

```bash
# Activate environment (if not already active)
abhiyanai_env\Scripts\activate  # Windows
source abhiyanai_env/bin/activate  # Linux/Mac

# Navigate to backend
cd backend

# Test different names
python generate.py "John Smith" "templates/as.mp4"
python generate.py "Maria Garcia" "templates/as.mp4"
python generate.py "Rajesh Kumar" "templates/as.mp4"
python generate.py "Priya Sharma" "templates/as.mp4"
```

## Expected Behavior with Internet

### OpenVoice Success Scenario:
```
🧬 Attempting OpenVoice cloning...
⚡ Pre-processing audio files...
🕒 Audio duration: 1.74s
⚡ Extending short audio from 1.74s to 3.00s
✅ Extended audio saved: tts\...\Name_extended.wav
✅ OpenVoice cloning successful: cloned_voices\...\Name.wav
✅ Generated video: generated_videos\Name_timestamp.mp4
```

### Fallback Scenario (if OpenVoice fails):
```
❌ OpenVoice failed: [Error details]
🔄 Using simple voice cloning fallback...
🧬 Attempting advanced spectral voice cloning...
✅ Advanced voice cloning successful
✅ Generated video: generated_videos\Name_timestamp.mp4  
```

## Troubleshooting

### If OpenVoice Downloads Fail:
1. Check internet connection
2. Verify firewall/proxy settings
3. Try running with admin privileges
4. Check antivirus isn't blocking downloads

### If FFmpeg Not Found:
- Windows: Ensure FFmpeg is in PATH
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`

### If Memory Issues:
- Close other applications
- Ensure 8GB+ RAM available
- Use smaller batch sizes

## Production Features Enabled

✅ **Automatic Audio Extension**: Handles short TTS files
✅ **Smart OpenVoice Handling**: Online/offline model management  
✅ **Multi-Layer Fallbacks**: Multiple voice cloning methods
✅ **SSL/Certificate Handling**: Works in corporate networks
✅ **Comprehensive Error Handling**: Graceful failure recovery
✅ **Resource Management**: Automatic cleanup
✅ **Progress Logging**: Detailed status updates

## Success Indicators

1. ✅ **Environment Setup**: `(abhiyanai_env)` visible in prompt
2. ✅ **Dependencies**: No import errors when running script  
3. ✅ **FFmpeg**: Version information displays correctly
4. ✅ **Template Video**: `templates/as.mp4` exists and playable
5. ✅ **First Run**: Downloads OpenVoice models successfully
6. ✅ **Output**: Video generated in `generated_videos/` folder
7. ✅ **Cleanup**: Temporary folders auto-removed after processing

The system is now production-ready with full OpenVoice support! 🎉
