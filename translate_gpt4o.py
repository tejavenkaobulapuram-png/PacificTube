"""
GPT-4o Subtitle Translator - Context-Aware Japanese to English
================================================================
Uses Azure OpenAI GPT-4o for high-quality conversation translation
"""

import os
import time
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Azure Storage
STORAGE_ACCOUNT = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
SAS_TOKEN = os.getenv('AZURE_STORAGE_SAS_TOKEN')
CONTAINER_NAME = 'videos'

# Azure OpenAI
OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT')
OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')


class GPT4oSubtitleTranslator:
    def __init__(self):
        """Initialize storage and OpenAI clients"""
        # Blob Storage
        account_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
        self.blob_service = BlobServiceClient(account_url=f"{account_url}?{SAS_TOKEN}")
        self.container_client = self.blob_service.get_container_client(CONTAINER_NAME)
        
        # Azure OpenAI
        self.openai_client = AzureOpenAI(
            api_key=OPENAI_KEY,
            api_version=OPENAI_API_VERSION,
            azure_endpoint=OPENAI_ENDPOINT
        )
        
        print(f"✅ Connected to Azure Storage: {STORAGE_ACCOUNT}")
        print(f"✅ GPT-4o ready: {OPENAI_DEPLOYMENT}")
    
    def translate_with_gpt4o(self, japanese_texts, batch_size=30):
        """
        Translate Japanese subtitle texts to English using GPT-4o
        Processes in batches with full conversation context
        """
        all_translations = []
        total_batches = (len(japanese_texts) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(japanese_texts), batch_size):
            batch = japanese_texts[batch_idx:batch_idx + batch_size]
            
            # Build prompt with conversation context
            prompt = """You are a professional Japanese-to-English subtitle translator for business meeting recordings.

Translate the following Japanese subtitle lines into natural English. These are from a recorded business meeting.

IMPORTANT RULES:
1. Translate conversational phrases accurately (e.g., "ありがとうございます" = "Thank you")
2. Maintain the natural flow of conversation
3. Keep translations concise (suitable for subtitles)
4. Preserve speaker intent and politeness
5. Return ONLY the translated lines, one per line, in the same order
6. Do NOT add numbers, labels, or extra formatting

Japanese subtitle lines:
---
"""
            prompt += "\n".join(batch)
            prompt += "\n---\n\nEnglish translations:"
            
            try:
                response = self.openai_client.chat.completions.create(
                    model=OPENAI_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": "You are a professional Japanese-English subtitle translator specializing in business meetings."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Lower temperature for consistent  translation
                    max_tokens=4000
                )
                
                translation_text = response.choices[0].message.content.strip()
                translations = [line.strip() for line in translation_text.split('\n') if line.strip()]
                
                # Match translations to original lines
                for i in range(len(batch)):
                    if i < len(translations):
                        all_translations.append(translations[i])
                    else:
                        # Fallback: keep original if mismatch
                        all_translations.append(batch[i])
                
                print(f"   ✓ Translated batch {batch_idx//batch_size + 1}/{total_batches} ({len(batch)} lines)")
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"   ❌ Error in batch {batch_idx//batch_size + 1}: {e}")
                # Fallback: keep original text
                all_translations.extend(batch)
        
        return all_translations
    
    def parse_vtt(self, vtt_content):
        """Parse VTT file into segments"""
        segments = []
        lines = vtt_content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if '-->' in line:
                timestamp = line
                i += 1
                
                text_lines = []
                while i < len(lines):
                    text_line = lines[i].strip()
                    if not text_line or '-->' in text_line:
                        break
                    if not text_line.isdigit():
                        text_lines.append(text_line)
                    i += 1
                
                if text_lines:
                    segments.append({
                        'timestamp': timestamp,
                        'text': ' '.join(text_lines)
                    })
            else:
                i += 1
        
        return segments
    
    def create_vtt_content(self, segments):
        """Create VTT file from segments"""
        vtt_lines = ['WEBVTT', '']
        
        for i, segment in enumerate(segments, 1):
            vtt_lines.append(str(i))
            vtt_lines.append(segment['timestamp'])
            vtt_lines.append(segment['text'])
            vtt_lines.append('')
        
        return '\n'.join(vtt_lines)
    
    def translate_subtitle_file(self, ja_blob_name):
        """Translate a single Japanese subtitle file using GPT-4o"""
        try:
            print(f"\n📝 Processing: {ja_blob_name}")
            
            # Download Japanese subtitle
            blob_client = self.container_client.get_blob_client(ja_blob_name)
            ja_content = blob_client.download_blob().readall().decode('utf-8')
            
            # Parse VTT
            segments = self.parse_vtt(ja_content)
            print(f"   📊 Found {len(segments)} subtitle segments")
            
            if not segments:
                print(f"   ⚠️  No segments found, skipping")
                return False
            
            # Extract texts for translation
            texts = [seg['text'] for seg in segments]
            
            # Translate using GPT-4o
            print(f"   🤖 Translating with GPT-4o (conversation-aware)...")
            translations = self.translate_with_gpt4o(texts)
            
            # Update segments with translations
            for i, translation in enumerate(translations):
                if i < len(segments):
                    segments[i]['text'] = translation
            
            # Create English VTT
            en_content = self.create_vtt_content(segments)
            
            # Upload
            en_blob_name = ja_blob_name.replace('.ja.vtt', '.en.vtt')
            print(f"   📤 Uploading: {en_blob_name}")
            en_blob_client = self.container_client.get_blob_client(en_blob_name)
            en_blob_client.upload_blob(
                en_content.encode('utf-8'),
                overwrite=True,
                content_settings=ContentSettings(content_type='text/vtt')
            )
            
            print(f"   ✅ Translation complete!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def translate_all_subtitles(self):
        """Translate all Japanese subtitle files"""
        print("\n" + "="*60)
        print("🤖 GPT-4o SUBTITLE TRANSLATION - Japanese → English")
        print("="*60)
        
        # Get all Japanese subtitle files
        all_blobs = list(self.container_client.list_blobs())
        ja_subtitle_blobs = [
            blob.name for blob in all_blobs 
            if blob.name.endswith('.ja.vtt')
        ]
        
        print(f"\n📁 Found {len(ja_subtitle_blobs)} Japanese subtitle files")
        print(f"🎯 Will translate all files with GPT-4o")
        print("-" * 60)
        
        success_count = 0
        for ja_blob_name in ja_subtitle_blobs:
            if self.translate_subtitle_file(ja_blob_name):
                success_count += 1
        
        print("\n" + "="*60)
        print(f"✅ Translation Complete!")
        print(f"   Successful: {success_count}/{len(ja_subtitle_blobs)}")
        print("="*60)


def main():
    """Main entry point"""
    try:
        translator = GPT4oSubtitleTranslator()
        translator.translate_all_subtitles()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
