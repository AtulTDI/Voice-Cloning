#!/usr/bin/env python3
"""
Quick fix for the syntax error caused by add_debugging_logs.py
This will restore the backup and apply a corrected patch
"""

import os
import sys
import shutil
import glob
import datetime

def find_backup_file():
    """Find the most recent backup file"""
    backup_files = glob.glob("generate_backup_*.py")
    if not backup_files:
        print("❌ No backup files found")
        return None
    
    # Sort by timestamp (most recent first)
    backup_files.sort(reverse=True)
    latest_backup = backup_files[0]
    print(f"✅ Found latest backup: {latest_backup}")
    return latest_backup

def restore_from_backup():
    """Restore generate.py from backup"""
    backup_file = find_backup_file()
    if not backup_file:
        return False
    
    try:
        shutil.copy(backup_file, "generate.py")
        print(f"✅ Restored generate.py from {backup_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to restore backup: {e}")
        return False

def apply_corrected_logging():
    """Apply corrected logging patches to generate.py"""
    print("🔧 Applying corrected logging patches...")
    
    try:
        with open("generate.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Add datetime import at the top if not already present
        if "import datetime" not in content[:500]:  # Check first 500 chars
            # Find a good place to add the import (after other imports)
            import_lines = []
            other_lines = []
            in_imports = True
            
            for line in content.split('\n'):
                if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == '' or line.startswith('#')):
                    import_lines.append(line)
                    if line.startswith('import ') or line.startswith('from '):
                        # Add datetime import after the last import
                        if 'datetime' not in line and line.strip():
                            import_lines.append('import datetime')
                            in_imports = False
                else:
                    in_imports = False
                    other_lines.append(line)
            
            # If we didn't add it during imports, add it at the beginning
            if in_imports:
                import_lines.append('import datetime')
            
            content = '\n'.join(import_lines + other_lines)
        
        # Now add logging to the extend_short_audio function
        # Find the function definition
        func_start = 'def extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:'
        
        if func_start in content:
            # Add logging function definition right after the docstring
            old_pattern = '''def extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:
    """Extend audio file if it's too short for voice cloning"""
    try:'''
            
            new_pattern = '''def extend_short_audio(audio_path: str, min_duration: float = 3.0) -> str:
    """Extend audio file if it's too short for voice cloning"""
    
    def log_extend(message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[EXTEND_LOG {timestamp}] {message}")
    
    log_extend(f"🚀 EXTEND_SHORT_AUDIO CALLED")
    log_extend(f"   Input: {audio_path}")
    log_extend(f"   Min duration: {min_duration}s")
    
    try:'''
            
            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern)
                print("✅ Added logging to extend_short_audio function")
            else:
                print("⚠️ Could not find exact pattern for extend_short_audio logging")
        
        # Add logging to clone_voice function
        clone_logging_point = 'print("⚡ Pre-processing audio files...")'
        
        if clone_logging_point in content:
            new_clone_logging = '''def log_clone(message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[CLONE_LOG {timestamp}] {message}")
    
    log_clone(f"🎭 STARTING clone_voice")
    log_clone(f"   TTS path: {tts_wav_path}")
    log_clone(f"   Reference path: {reference_wav_path}")
    log_clone(f"   Output path: {cloned_wav_path}")
    
    print("⚡ Pre-processing audio files...")'''
            
            content = content.replace(clone_logging_point, new_clone_logging)
            print("✅ Added logging to clone_voice function")
        
        # Write the corrected content
        with open("generate.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("✅ Successfully applied corrected logging patches")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply corrected patches: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_syntax():
    """Validate that the patched file has no syntax errors"""
    print("🔍 Validating syntax...")
    
    try:
        import ast
        with open("generate.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        ast.parse(content)
        print("✅ Syntax validation passed")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error detected: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def main():
    """Main function to fix the syntax error"""
    print("🚀 FIXING SYNTAX ERROR IN GENERATE.PY")
    print("="*60)
    
    if not os.path.exists("generate.py"):
        print("❌ generate.py not found")
        return False
    
    # First, try to validate current syntax
    if validate_syntax():
        print("✅ Current generate.py has no syntax errors")
        return True
    
    # Restore from backup
    if not restore_from_backup():
        print("❌ Could not restore from backup")
        return False
    
    # Apply corrected patches
    if not apply_corrected_logging():
        print("❌ Could not apply corrected patches")
        return False
    
    # Validate final result
    if validate_syntax():
        print("\n🎉 SUCCESS! generate.py has been fixed and enhanced with logging")
        print("You can now run your video generation script and see detailed logs")
        return True
    else:
        print("\n❌ FAILED! Syntax errors remain")
        print("Restoring original backup...")
        restore_from_backup()
        return False

if __name__ == "__main__":
    main()
