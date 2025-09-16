import whisper
import torch
import re
import os
import time
from pydub import AudioSegment
from indic_transliteration.sanscript import transliterate, ITRANS, DEVANAGARI
from difflib import get_close_matches

def normalize_word(w: str) -> str:
    """Normalize a word by removing non-letters and lowering case."""
    return re.sub(r'[^a-z]', '', w.lower())


def convert_to_devanagari(text: str) -> str:
    """Convert Roman script to Devanagari using ITRANS transliteration."""
    return transliterate(text, ITRANS, DEVANAGARI)
def _find_phrase_times(words_data, phrase_words):
    match_index = 0
    start_time = None
    end_time = None

    for word_info in words_data:
        current_word = normalize_word(word_info["word"])
        if current_word == phrase_words[match_index]:
            if match_index == 0:
                start_time = word_info["start"]
            end_time = word_info["end"]
            match_index += 1
            if match_index == len(phrase_words):
                break
        else:
            match_index = 0
            start_time = None
            end_time = None

    return start_time, end_time

def normalize_word(w):
    return re.sub(r'[^a-zA-Zअ-हक़-य़ء-ي]', '', w.lower().strip())

def trim_audio_by_word(audio_path: str, phrase: str, output_path: str = None):
    """
    Trims audio between the end of the first occurrence and start of the second
    of the *first phonetically similar repeated word* (e.g., 'namaskar', 'nameskar').
    """

    if output_path is None:
        base_dir = "cloned_voices"
        os.makedirs(base_dir, exist_ok=True)
        timestamp = int(time.time() * 1000)
        safe_phrase = re.sub(r'[^a-zA-Z0-9]', '_', phrase)
        output_path = os.path.join(base_dir, f"{safe_phrase}_trimmed_{timestamp}.wav")

    print(f"🎧 Loading audio for trimming: {audio_path}")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="mr", word_timestamps=True)

    all_words = []
    for seg in result["segments"]:
        all_words.extend(seg["words"])
    
    print("\n📝 Transcribed Words:")
    for w in all_words:
        print(f"{w['word']} ({w['start']:.2f}-{w['end']:.2f}s)")

    print("\n🔎 Searching for repeated similar words...")
    normalized_words = [normalize_word(w["word"]) for w in all_words]

def trim_audio_by_word(audio_path: str, target_name: str, output_path: str):
    """
    Trim audio around the target name. This function will:
    1. Try to find repeated similar words (original algorithm)
    2. Try to find phonetically similar words to the target name
    3. Fall back to extracting a segment from the middle of the audio
    """
    print(f"🎧 Loading audio for trimming: {audio_path}")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="mr", word_timestamps=True)
    all_words = []
    
    for segment in result['segments']:
        if 'words' in segment:
            all_words.extend(segment['words'])
    
    print("📝 Transcribed Words:")
    for word_info in all_words:
        print(f" {word_info['word']} ({word_info['start']:.2f}-{word_info['end']:.2f}s)")
    
    if not all_words:
        raise ValueError("❌ No words found in transcription.")
    
    # Normalize words for comparison (remove punctuation, lowercase)
    normalized_words = [re.sub(r'[^\w\s]', '', word["word"].lower().strip()) for word in all_words]
    
    # Strategy 1: Try to find repeated similar words (original algorithm)
    print("🔎 Searching for repeated similar words...")
    for i, word1 in enumerate(normalized_words):
        if not word1:
            continue
        matches = get_close_matches(word1, normalized_words[i+1:], n=1, cutoff=0.8)
        if matches:
            word2 = matches[0]
            second_index = normalized_words.index(word2, i + 1)
            print(f"✅ Found similar words: '{word1}' → '{word2}'")
            first_end = all_words[i]["end"]
            second_start = all_words[second_index]["start"]

            # Trim and export
            audio = AudioSegment.from_file(audio_path)
            trimmed = audio[int(first_end * 1000):int(second_start * 1000)]
            trimmed.export(output_path, format="wav")

            print(f"✂️ Trimmed audio between {first_end:.2f}s and {second_start:.2f}s → {output_path}")
            return output_path
    
    # Strategy 2: Try to find words similar to the target name
    print(f"🔎 Searching for words similar to '{target_name}'...")
    target_words = target_name.lower().split()
    for target_word in target_words:
        matches = get_close_matches(target_word, normalized_words, n=3, cutoff=0.6)
        if matches:
            # Find the first match in the audio
            for match in matches:
                try:
                    match_index = normalized_words.index(match)
                    word_start = all_words[match_index]["start"]
                    word_end = all_words[match_index]["end"]
                    
                    # Extend the selection to include some context (0.5s before and after)
                    buffer = 0.5
                    trim_start = max(0, word_start - buffer)
                    trim_end = word_end + buffer
                    
                    print(f"✅ Found similar word to '{target_word}': '{match}' at {word_start:.2f}-{word_end:.2f}s")
                    
                    # Trim and export
                    audio = AudioSegment.from_file(audio_path)
                    trimmed = audio[int(trim_start * 1000):int(trim_end * 1000)]
                    trimmed.export(output_path, format="wav")
                    
                    print(f"✂️ Trimmed audio between {trim_start:.2f}s and {trim_end:.2f}s → {output_path}")
                    return output_path
                except ValueError:
                    continue
    
    # Strategy 3: Fallback - extract from the middle portion (assuming name is likely in the middle)
    print("🔄 Using fallback strategy: extracting middle segment...")
    audio = AudioSegment.from_file(audio_path)
    total_duration = len(audio) / 1000.0  # Duration in seconds
    
    # Extract a 2-3 second segment from the middle
    segment_duration = min(3.0, total_duration * 0.4)  # 40% of audio or 3s max
    start_time = (total_duration - segment_duration) / 2
    end_time = start_time + segment_duration
    
    trimmed = audio[int(start_time * 1000):int(end_time * 1000)]
    trimmed.export(output_path, format="wav")
    
    print(f"✂️ Fallback trim: extracted {segment_duration:.1f}s from middle ({start_time:.2f}s-{end_time:.2f}s) → {output_path}")
    return output_path


async def transcribe_audio(audio_path: str, language: str = "mr") -> str:
    """
    Transcribes given audio using Whisper and returns the Devanagari script output.
    """
    try:
        print(f"📝 Transcribing audio: {audio_path} (language='{language}')")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🖥️  Using device: {device.upper()}")

        model = whisper.load_model("small", device=device)
        result = model.transcribe(audio_path, language=language, fp16=torch.cuda.is_available())

        raw_text = result.get("text", "").strip()
        print(f"📜 Transcribed (Roman):\n{raw_text}")

        dev_text = convert_to_devanagari(raw_text)
        print(f"📝 Transcribed (Devanagari):\n{dev_text}")

        return dev_text

    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return ""
