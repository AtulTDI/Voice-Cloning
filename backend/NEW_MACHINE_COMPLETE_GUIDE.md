# 🚀 New Machine Setup - Complete Guide

## Issue Resolution: "input video too short" + Missing OpenVoice

You're getting these errors because:
1. **Missing OpenVoice folder**: OpenVoice models and checkpoints aren't set up
2. **Video validation error**: Input video validation is failing

## 🎯 Two Setup Options

### **Option 1: Full Internet Setup (Recommended)**
Download everything fresh on the new machine with internet.

### **Option 2: Portable Setup**
Copy the working OpenVoice installation from current machine.

---

## 🌐 **Option 1: Full Internet Setup**

### Step 1: Clone Repository
```bash
git clone https://github.com/AtulTDI/Voice-Cloning.git
cd Voice-Cloning
```

### Step 2: Set Up Environment
```bash
# Create virtual environment
python -m venv abhiyanai_env

# Activate environment
# Windows:
abhiyanai_env\Scripts\activate
# Linux/Mac:
source abhiyanai_env/bin/activate
```

### Step 3: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Run OpenVoice Setup
```bash
python setup_new_machine.py
```

### Step 5: Test
```bash
python generate.py "Test User" "templates/as.mp4"
```

**Expected first run**: Will download ~2GB of OpenVoice models (5-10 minutes)

---

## 📦 **Option 2: Portable Setup**

### Step A: Create Package (Current Machine)
```bash
# On your current working machine
cd backend
python create_portable_openvoice.py
```

This creates an `openvoice_package/` folder containing:
- ✅ OpenVoice models and checkpoints  
- ✅ Main scripts
- ✅ Template video
- ✅ Setup instructions

### Step B: Transfer Package
1. **Copy** the entire `openvoice_package/` folder to new machine
2. **Extract** to desired location (e.g., `C:\Voice-Cloning\`)

### Step C: Setup on New Machine
```bash
# On new machine
cd openvoice_package
python -m venv abhiyanai_env
abhiyanai_env\Scripts\activate  # Windows
pip install -r requirements.txt
python create_portable_openvoice.py install
```

### Step D: Test
```bash
python generate.py "Test User" "templates/as.mp4"
```

---

## 🔧 **Fix for "input video too short" Error**

This error occurs when video validation fails. The fix is already in the latest code but here's manual fix:

### Manual Fix:
1. **Check video file exists**:
   ```bash
   ls templates/as.mp4  # Should show file
   ffprobe templates/as.mp4  # Should show video info
   ```

2. **Verify video duration**:
   ```bash
   ffprobe -v quiet -show_entries format=duration -of csv=p=0 templates/as.mp4
   ```
   Should show ~32 seconds

3. **If video is missing or corrupted**, download a new template video or use any MP4 file > 10 seconds

---

## 🧪 **Verification Steps**

### Check 1: Environment
```bash
python --version  # Should be 3.12+
pip list | findstr openvoice  # Should show openvoice-cli
ffmpeg -version  # Should show FFmpeg info
```

### Check 2: OpenVoice Setup
```bash
python -c "import openvoice_cli; print('OpenVoice OK')"
ls openvoice/  # Should show: cache, checkpoints, hf_cache
ls openvoice/checkpoints/  # Should show: base_speakers, converter
```

### Check 3: Template Video
```bash
ls templates/as.mp4  # Should exist
python -c "
import subprocess
result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', 'templates/as.mp4'], capture_output=True, text=True)
print(f'Video duration: {float(result.stdout.strip()):.2f}s')
"
```

### Check 4: Full Test
```bash
python generate.py "John Doe" "templates/as.mp4"
```

**Expected successful output:**
```
🎬 Processing: John Doe
📹 Video file: templates/as.mp4
✅ Reference voice extracted
🗣 Generating TTS for name only: John Doe
🧬 Attempting OpenVoice cloning...
✅ OpenVoice cloning successful  # <-- This should appear with internet
✅ Generated video: generated_videos/John_Doe_timestamp.mp4
```

---

## 🚨 **Troubleshooting**

### If OpenVoice Still Fails:
1. **Check internet connection**: OpenVoice needs to download models first time
2. **Check firewall**: Allow Python and Git through firewall  
3. **Use fallback**: System will automatically use advanced spectral cloning
4. **Manual model download**: Visit HuggingFace hub to download models manually

### If "input video too short" persists:
1. **Check template file**: Ensure `templates/as.mp4` exists and is playable
2. **Try different video**: Use any MP4 file longer than 10 seconds
3. **Check FFmpeg**: Ensure FFmpeg can process the video file

### Common Solutions:
```bash
# Fix permissions (Windows)
icacls templates /grant Everyone:F /T

# Re-download template (if corrupted)
# [Download a sample MP4 file and place in templates/]

# Reinstall FFmpeg
# Windows: Download from https://ffmpeg.org/
# Linux: sudo apt install ffmpeg
# macOS: brew install ffmpeg
```

---

## 📋 **Quick Reference Commands**

```bash
# Setup new machine (Option 1)
git clone https://github.com/AtulTDI/Voice-Cloning.git
cd Voice-Cloning/backend
python -m venv abhiyanai_env
abhiyanai_env\Scripts\activate
pip install -r requirements.txt
python setup_new_machine.py
python generate.py "Test Name" "templates/as.mp4"

# Create portable package (current machine)  
python create_portable_openvoice.py

# Install portable package (new machine)
python create_portable_openvoice.py install
python generate.py "Test Name" "templates/as.mp4"
```

The key is that **OpenVoice needs proper setup on each new machine** - either through internet download or by copying the complete model files! 🎯
