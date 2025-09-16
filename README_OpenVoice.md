# OpenVoice TTS and Voice Cloning Setup

This document provides instructions for setting up and using OpenVoice for TTS generation and voice cloning in the Marathi Video Worker Service.

## 🌐 Setup with Internet Access

### Step 1: Run Setup Script
On a machine with internet access, run the setup script:

```bash
# Activate your Python environment
conda activate abhiyanai_env  # or your environment name

# Run the setup script
python setup_openvoice.py
```

This will:
- Install all required Python packages
- Download OpenVoice models from HuggingFace
- Set up the directory structure
- Create CLI tools
- Test the installation

### Step 2: Package for Offline Use
After setup completes, you'll have an `openvoice/` directory with all models and code. Package this for transfer:

```bash
# Create a compressed archive
tar -czf openvoice_models.tar.gz openvoice/
# or
zip -r openvoice_models.zip openvoice/
```

## 💻 Setup on Offline Machine

### Step 1: Transfer Files
1. Copy `openvoice_models.tar.gz` (or `.zip`) to your offline machine
2. Copy `generate_openvoice.py` to your offline machine
3. Copy `requirements_openvoice.txt` to your offline machine

### Step 2: Extract and Install
```bash
# Extract the models
tar -xzf openvoice_models.tar.gz
# or
unzip openvoice_models.zip

# Install Python dependencies (if not already installed)
pip install -r requirements_openvoice.txt
```

### Step 3: Update Configuration
Edit `generate_openvoice.py` and update the `OPENVOICE_DIR` path:

```python
# Update this path to point to your openvoice directory
OPENVOICE_DIR = r"C:\path\to\your\openvoice"
```

## 🎤 Usage

### Basic Usage
Replace your current `generate.py` with `generate_openvoice.py` or rename it:

```bash
# Backup current version
cp generate.py generate_advanced_backup.py

# Use OpenVoice version
cp generate_openvoice.py generate.py

# Run with OpenVoice
python generate.py "Atul Kadam" "templates/as.mp4"
```

### What the OpenVoice Version Does

1. **TTS Generation**: First tries to generate TTS directly with voice cloning using OpenVoice
2. **Fallback TTS**: If OpenVoice TTS fails, uses Edge-TTS
3. **Voice Cloning**: Uses OpenVoice to clone the reference voice from the base video
4. **Multiple Methods**: Tries different OpenVoice approaches:
   - OpenVoice CLI
   - OpenVoice API directly
   - Alternative OpenVoice implementation
5. **Fallback Processing**: If all OpenVoice methods fail, uses basic audio processing

## 🔧 Troubleshooting

### Common Issues

1. **"OpenVoice directory not found"**
   - Update `OPENVOICE_DIR` path in the script
   - Ensure the `openvoice/` directory exists and contains models

2. **"Module 'openvoice' not found"**
   - Install with: `pip install openvoice`
   - Or ensure the openvoice directory is in Python path

3. **CUDA/GPU Issues**
   - Install PyTorch with CUDA support if you have a GPU
   - The script will automatically fall back to CPU if CUDA is not available

4. **Model Loading Errors**
   - Ensure all model files were downloaded properly
   - Check the `checkpoints/` directory structure

### Environment Variables
The script sets these environment variables for offline operation:
- `HF_HUB_OFFLINE=1` - Forces HuggingFace Hub offline mode
- `TRANSFORMERS_OFFLINE=1` - Forces Transformers offline mode
- Various SSL bypass settings for restricted environments

## 📁 Directory Structure

After setup, your directory should look like:

```
openvoice/
├── checkpoints/
│   ├── base_speakers/
│   │   └── EN/
│   └── converter/
├── cache/
├── hf_cache/
├── api.py
├── openvoice_cli.py
└── other OpenVoice files...
```

## 🎯 Key Features

### OpenVoice TTS Generation
- Generates TTS directly with voice cloning
- Uses reference audio from base video
- Supports multiple languages (optimized for Hindi/Marathi)

### Advanced Voice Cloning  
- Uses spectral envelope matching
- Applies tone color conversion
- Preserves naturalness and voice characteristics

### Fallback System
- Multiple OpenVoice methods tried in sequence
- Graceful fallback to Edge-TTS + basic processing
- Always produces output even if advanced methods fail

## 🔄 Switching Between Versions

You have multiple versions available:

1. **Current Advanced Version**: `generate.py` (with spectral analysis)
2. **OpenVoice Version**: `generate_openvoice.py` (this new version)  
3. **Backup Version**: `generate_advanced_backup.py` (your previous working version)

Switch by copying the desired version:
```bash
# Use OpenVoice version
cp generate_openvoice.py generate.py

# Or go back to advanced version  
cp generate_advanced_backup.py generate.py
```

## 🌟 Expected Results

With proper OpenVoice setup, you should get:
- ✅ More natural sounding voice
- ✅ Better voice cloning quality
- ✅ Preserved speaker characteristics
- ✅ Reduced robotic artifacts
- ✅ Better pronunciation of Indian names

The voice quality should be significantly better than basic TTS, especially for voice cloning and matching the reference speaker's characteristics.
