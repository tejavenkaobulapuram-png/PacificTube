"""
GPT-4o Subtitle Translator - Context-Aware Japanese to English
================================================================
Uses Azure OpenAI GPT-4o for high-quality conversation translation
"""

import os
import re
import time
import json
import httpx
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
        
        # Azure OpenAI with timeout to prevent hanging
        self.openai_client = AzureOpenAI(
            api_key=OPENAI_KEY,
            api_version=OPENAI_API_VERSION,
            azure_endpoint=OPENAI_ENDPOINT,
            timeout=httpx.Timeout(60.0, connect=10.0)  # 60 sec total, 10 sec connect
        )
        
        print(f"✅ Connected to Azure Storage: {STORAGE_ACCOUNT}")
        print(f"✅ GPT-4o ready: {OPENAI_DEPLOYMENT}")
    
    def translate_single_line(self, japanese_text, context_before="", context_after=""):
        """Translate a single line using GPT-4o with context (fallback for problematic segments)"""
        try:
            # Provide context to avoid content filter issues
            context_prompt = "Translate this Japanese business meeting subtitle to English:\n\n"
            if context_before:
                context_prompt += f"Previous line: {context_before}\n"
            context_prompt += f"Current line: {japanese_text}\n"
            if context_after:
                context_prompt += f"Next line: {context_after}\n"
            context_prompt += "\nReturn ONLY the English translation of the current line:"
            
            response = self.openai_client.chat.completions.create(
                model=OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a professional Japanese-English subtitle translator for business meetings. You are translating meeting subtitles."},
                    {"role": "user", "content": context_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"      ⚠️ Single line translation failed: {str(e)[:100]}")
            # Last resort: return a safe fallback
            return f"[Translation error]"
    
    def translate_with_gpt4o(self, japanese_texts, batch_size=20, max_retries=2):
        """
        Translate Japanese subtitle texts to English using GPT-4o with JSON output
        Uses structured JSON format to guarantee exact line count matching
        """
        all_translations = []
        total_batches = (len(japanese_texts) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(japanese_texts), batch_size):
            batch = japanese_texts[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            
            # Build prompt with JSON format requirement - use numbered keys for clarity
            prompt = f"""Translate {len(batch)} Japanese meeting subtitle lines to English.

Return a JSON object with "translations" as an array containing exactly {len(batch)} strings (the English translations).

Japanese lines to translate:
"""
            for i, text in enumerate(batch):
                prompt += f'{i+1}. "{text}"\n'
            
            prompt += f"""
Example response format for 3 lines:
{{"translations": ["Hello", "Thank you", "Goodbye"]}}

IMPORTANT: Return exactly {len(batch)} translated strings in the "translations" array."""
            
            translated = False
            for attempt in range(max_retries):
                try:
                    response = self.openai_client.chat.completions.create(
                        model=OPENAI_DEPLOYMENT,
                        messages=[
                            {"role": "system", "content": "You are a Japanese-English subtitle translator. Return valid JSON with a 'translations' array containing English translations. Always return the exact number of translations requested."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=4000,
                        response_format={"type": "json_object"}
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                    # Parse JSON response
                    try:
                        parsed = json.loads(response_text)
                        
                        # Find the translations array - check multiple possible keys
                        translations = None
                        if isinstance(parsed, dict):
                            for key in ['translations', 'items', 'results', 'english', 'output', 'data']:
                                if key in parsed and isinstance(parsed[key], list):
                                    translations = parsed[key]
                                    break
                            # If still not found, look for any list value
                            if translations is None:
                                for value in parsed.values():
                                    if isinstance(value, list) and len(value) == len(batch):
                                        translations = value
                                        break
                        elif isinstance(parsed, list):
                            translations = parsed
                        
                        if translations is None:
                            print(f"   ⚠️ Batch {batch_num}: No translations array found - retry {attempt+1}/{max_retries}")
                            time.sleep(1)
                            continue
                        
                        # Extract strings from the list (handle both plain strings and dicts)
                        result = []
                        for item in translations:
                            if isinstance(item, str):
                                result.append(item.strip())
                            elif isinstance(item, dict):
                                # Try various keys for the translation
                                for k in ['english', 'translation', 'text', 'en', 'value']:
                                    if k in item:
                                        result.append(str(item[k]).strip())
                                        break
                                else:
                                    # Just use first string value
                                    for v in item.values():
                                        if isinstance(v, str):
                                            result.append(v.strip())
                                            break
                            else:
                                result.append(str(item).strip())
                        
                        # Validate line count
                        if len(result) == len(batch):
                            all_translations.extend(result)
                            print(f"   ✓ Batch {batch_num}/{total_batches} ({len(batch)} lines)")
                            translated = True
                            time.sleep(0.4)
                            break
                        else:
                            print(f"   ⚠️ Batch {batch_num}: got {len(result)} lines, need {len(batch)} - retry {attempt+1}/{max_retries}")
                            time.sleep(1)
                    
                    except json.JSONDecodeError as je:
                        print(f"   ⚠️ Batch {batch_num} JSON parse error - retry {attempt+1}/{max_retries}")
                        time.sleep(1)
                    
                    # Final fallback after retries
                    if attempt == max_retries - 1 and not translated:
                        print(f"   🔄 Line-by-line fallback for batch {batch_num}")
                        for i, line in enumerate(batch):
                            context_before = batch[i-1] if i > 0 else ""
                            context_after = batch[i+1] if i < len(batch)-1 else ""
                            translated_line = self.translate_single_line(line, context_before, context_after)
                            all_translations.append(translated_line)
                            time.sleep(0.2)
                        translated = True
                    
                except Exception as e:
                    print(f"   ❌ Batch {batch_num} error: {str(e)[:60]}")
                    time.sleep(2)
                    
                    if attempt == max_retries - 1:
                        print(f"   🔄 Emergency fallback for batch {batch_num}")
                        for i, line in enumerate(batch):
                            try:
                                context_before = batch[i-1] if i > 0 else ""
                                context_after = batch[i+1] if i < len(batch)-1 else ""
                                translated_line = self.translate_single_line(line, context_before, context_after)
                                all_translations.append(translated_line)
                                time.sleep(0.2)
                            except:
                                all_translations.append("[Translation unavailable]")
                        translated = True
            
            if not translated:
                print(f"   ⚠️ Batch {batch_num} failed - using placeholders")
                all_translations.extend(["[Translation error]"] * len(batch))
        
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
