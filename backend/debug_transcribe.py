import whisper

audio_path = "cloned_voices/Atul_Kadam.wav"  # change if needed
model = whisper.load_model("base")  # or "small" for faster

result = model.transcribe(audio_path, word_timestamps=True)

print("\n--- Whisper Detected Words ---")
for seg in result["segments"]:
    for w in seg["words"]:
        print(f"{w['word']} ({w['start']:.2f}-{w['end']:.2f}s)")
print("-------------------------------------------\n")
