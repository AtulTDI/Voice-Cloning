#!/usr/bin/env python3
"""
EMERGENCY FIX for syntax error in generate.py
Run this on the other machine to fix the patching error
"""

import os
import glob

def emergency_fix():
    """Quick emergency fix for the syntax error"""
    print("🚨 EMERGENCY SYNTAX FIX")
    print("="*40)
    
    # Find the backup file
    backup_files = glob.glob("generate_backup_*.py")
    if backup_files:
        latest_backup = sorted(backup_files)[-1]
        print(f"📁 Found backup: {latest_backup}")
        
        try:
            # Simply restore the backup
            with open(latest_backup, "r", encoding="utf-8") as f:
                backup_content = f.read()
            
            with open("generate.py", "w", encoding="utf-8") as f:
                f.write(backup_content)
            
            print("✅ Restored generate.py from backup")
            print("🔄 The syntax error has been fixed")
            print("⚠️  Note: Enhanced logging has been removed")
            print("💡 You can try your video generation now")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to restore: {e}")
            return False
    else:
        print("❌ No backup files found")
        return False

if __name__ == "__main__":
    if emergency_fix():
        print("\n🎯 SUCCESS! You can now run:")
        print('python generate.py "Your Name" "templates\\as.mp4"')
    else:
        print("\n❌ FAILED! Manual intervention needed")
        print("Please check if backup files exist")
