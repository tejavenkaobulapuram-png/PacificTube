"""
Test the fixed GPT-4o translation on one file
"""
import os
from dotenv import load_dotenv
from translate_gpt4o import GPT4oSubtitleTranslator

load_dotenv()

def test_one_file():
    translator = GPT4oSubtitleTranslator()
    
    # Translate just the first file as a test
    test_file = "03_定例会議/Recordings/生成AI連携会議-20251121_145723-会議の録音.ja.vtt"
    
    print("\n" + "="*60)
    print("🧪 TESTING FIXED TRANSLATION (ONE FILE)")
    print("="*60)
    print(f"📝 Test file: {test_file}")
    print()
    
    success = translator.translate_subtitle_file(test_file)
    
    if success:
        print("\n✅ Test translation successful!")
        print("   Check the .en.vtt file - it should contain ONLY English text")
    else:
        print("\n❌ Test translation failed")
    
    print("="*60)

if __name__ == '__main__':
    test_one_file()
