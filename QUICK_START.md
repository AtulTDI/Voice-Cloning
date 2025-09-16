# Quick Start Guide - Marathi Video Worker Service

## 🚀 **Quick Commands**

### Activate Environment
```powershell
abhiyanai_env\Scripts\Activate.ps1
```

### Generate Video
```powershell
python backend/generate.py "Full Name" "templates/video.mp4"
```

### Example
```powershell
python backend/generate.py "Priya Sharma" "templates/as.mp4"
```

## 📂 **Key Folders**

- **Templates**: `backend/templates/` (input videos)
- **Output**: `backend/generated_videos/` (final videos)
- **Logs**: Check console output for status

## ⚡ **Expected Process**

1. **Audio Extraction**: ~1 second
2. **TTS Generation**: ~1-2 seconds  
3. **Voice Cloning**: ~1-2 seconds
4. **Video Synthesis**: ~2-3 seconds
5. **Cleanup**: Automatic

Total: ~5-8 seconds per video

## ✅ **Success Indicators**

```
✅ Reference voice extracted
✅ Enhanced pyttsx3 created
✅ Advanced voice cloning completed
✅ Generated video for [Name]
```

## ❌ **Troubleshooting**

### Common Issues
- **Path errors**: Use forward slashes `/` or double backslashes `\\`
- **Permission errors**: Run as administrator if needed
- **Long names**: Keep names under 50 characters

### Fallback Behavior
- Edge-TTS fails → pyttsx3 (expected on restricted networks)
- OpenVoice fails → Advanced spectral cloning (expected offline)
- All TTS fails → Silent audio (rare)

## 📞 **Support**

Check `DEPLOYMENT_SUMMARY.md` for detailed technical information.

**Status: ✅ PRODUCTION READY**
