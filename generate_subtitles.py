"""
Automatic Subtitle Generator for PacificTube
Uses Azure Speech-to-Text to automatically generate subtitles from video audio
"""

import os
import subprocess
import tempfile
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, AudioConfig, OutputFormat
from azure.cognitiveservices.speech import ResultReason, CancellationReason
from azure.storage.blob import BlobServiceClient, ContainerClient
from urllib.parse import quote
from dotenv import load_dotenv
import requests

load_dotenv()


class AutoSubtitleGenerator:
    """Generate subtitles automatically from video audio using Azure Speech Services"""
    
    def __init__(self, speech_key, speech_region, storage_account, blob_sas_token):
        self.speech_key = speech_key
        self.speech_region = speech_region
        self.storage_account = storage_account
        self.blob_sas_token = blob_sas_token
        
        # Create container client directly with SAS URL
        container_url = f"https://{storage_account}.blob.core.windows.net/videos?{blob_sas_token}"
        self.container_client = ContainerClient.from_container_url(container_url)
    
    def _find_ffmpeg(self):
        """
        Smart FFmpeg detection - works for all team members!
        Checks multiple locations in order:
        1. FFMPEG_PATH environment variable (custom location)
        2. Project folder: ./ffmpeg/ffmpeg-8.1-essentials_build/bin/ffmpeg.exe
        3. System PATH: 'ffmpeg' (if installed globally)
        """
        # 1. Check environment variable
        env_path = os.environ.get('FFMPEG_PATH')
        if env_path:
            # Support relative paths from project root
            if not os.path.isabs(env_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                env_path = os.path.join(script_dir, env_path)
            if os.path.exists(env_path):
                return env_path
        
        # 2. Check project folder (portable version)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        portable_paths = [
            os.path.join(script_dir, 'ffmpeg', 'ffmpeg-8.1-essentials_build', 'bin', 'ffmpeg.exe'),  # Windows
            os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg'),  # Linux/Mac
            os.path.join(script_dir, 'ffmpeg', 'ffmpeg'),  # Simple structure
        ]
        
        for path in portable_paths:
            if os.path.exists(path):
                return path
        
        # 3. Try system PATH (globally installed)
        return 'ffmpeg'
    
    def extract_audio_from_video(self, video_id, output_wav_path):
        """Download video from Azure Blob Storage and extract audio using ffmpeg"""
        print(f"📥 Downloading video from Azure Blob Storage...")
        
        # Download video directly from Azure Blob Storage using container client
        blob_client = self.container_client.get_blob_client(video_id)
        
        # Download to temporary file
        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        
        # Download with progress
        stream = blob_client.download_blob()
        total_size = stream.properties.size
        downloaded = 0
        
        for chunk in stream.chunks():
            temp_video.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"\rDownloading: {percent:.1f}% ({downloaded:,} / {total_size:,} bytes)", end='')
        
        temp_video.close()
        print(f"\n✅ Downloaded to {temp_video.name} ({os.path.getsize(temp_video.name):,} bytes)")
        
        print(f"🎵 Extracting audio with ffmpeg...")
        
        # Get FFmpeg path with smart detection
        ffmpeg_cmd = self._find_ffmpeg()
        
        # Use ffmpeg to extract audio as WAV (required for Speech API)
        # WAV format: 16kHz, mono, 16-bit PCM
        cmd = [
            ffmpeg_cmd,
            '-i', temp_video.name,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output file
            output_wav_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            print(f"\n❌ FFmpeg failed with return code: {result.returncode}")
            print(f"FFmpeg error output:\n{result.stderr}")
            raise Exception(f"FFmpeg audio extraction failed: {result.stderr}")
        
        # Clean up temp video
        os.unlink(temp_video.name)
        
        print(f"✅ Audio extracted to {output_wav_path}")
    
    def transcribe_audio_to_vtt(self, audio_file_path, language='ja-JP', output_vtt_path=None):
        """
        Transcribe audio using Azure Speech Services and generate VTT file
        
        Args:
            audio_file_path: Path to WAV audio file
            language: Language code (ja-JP, en-US, zh-CN, etc.)
            output_vtt_path: Path to save VTT file
        """
        print(f"🎙️  Starting speech recognition ({language})...")
        
        # Configure Azure Speech
        speech_config = SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        speech_config.speech_recognition_language = language
        
        # Enable detailed results with word-level timestamps
        speech_config.request_word_level_timestamps()
        speech_config.output_format = OutputFormat.Detailed
        
        # IMPORTANT: Extend silence timeout to handle videos with long silence
        # Default is 5 seconds, but some meetings have silence at start and during breaks
        from azure.cognitiveservices.speech import PropertyId
        # Initial silence: wait up to 15 minutes before first speech
        speech_config.set_property(PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "900000")  # 15 minutes
        # End silence: wait up to 5 minutes for silence gaps (e.g., breaks, pauses)
        speech_config.set_property(PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "300000")  # 5 minutes
        
        print(f"⚙️  Configured for long silence periods (up to 15 min initial, 5 min gaps)")
        
        audio_config = AudioConfig(filename=audio_file_path)
        recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        
        # Store recognized text with timestamps
        subtitles = []
        done = False
        recognition_count = 0
        
        def session_started_cb(evt):
            """Callback when recognition session starts"""
            print(f"📡 Recognition session started: {evt.session_id}")
        
        def recognizing_cb(evt):
            """Callback for intermediate recognition results"""
            # Only print first few to avoid spam
            nonlocal recognition_count
            if recognition_count < 5:
                print(f"🔄 Recognizing: {evt.result.text[:50]}...")
                recognition_count += 1
        
        def recognized_cb(evt):
            """Callback when speech is recognized"""
            if evt.result.reason == ResultReason.RecognizedSpeech:
                print(f"✓ Recognized: {evt.result.text[:80]}...")
                
                # Get word-level timestamps from detailed results
                import json
                if hasattr(evt.result, 'json'):
                    result_json = json.loads(evt.result.json)
                    if 'NBest' in result_json and len(result_json['NBest']) > 0:
                        words = result_json['NBest'][0].get('Words', [])
                        if words:
                            # Group words into subtitle chunks (every 5-10 words or 5 seconds)
                            chunk = []
                            chunk_start = None
                            
                            for word in words:
                                if chunk_start is None:
                                    chunk_start = word['Offset'] / 10000000  # Convert to seconds
                                
                                chunk.append(word['Word'])
                                
                                # Create subtitle every 10 words or 5 seconds
                                duration = (word['Offset'] / 10000000) - chunk_start
                                if len(chunk) >= 10 or duration >= 5.0:
                                    chunk_end = (word['Offset'] + word['Duration']) / 10000000
                                    subtitles.append({
                                        'start': chunk_start,
                                        'end': chunk_end,
                                        'text': ' '.join(chunk)
                                    })
                                    chunk = []
                                    chunk_start = None
                            
                            # Add remaining words
                            if chunk:
                                last_word = words[-1]
                                chunk_end = (last_word['Offset'] + last_word['Duration']) / 10000000
                                subtitles.append({
                                    'start': chunk_start,
                                    'end': chunk_end,
                                    'text': ' '.join(chunk)
                                })
                else:
                    # Fallback: Use recognition time (less accurate)
                    offset = evt.result.offset / 10000000  # Convert to seconds
                    duration = evt.result.duration / 10000000
                    subtitles.append({
                        'start': offset,
                        'end': offset + duration,
                        'text': evt.result.text
                    })
        
        def canceled_cb(evt):
            """Callback when recognition is canceled"""
            print(f"⚠️  Recognition canceled. Reason: {evt.result.reason}")
            if evt.result.reason == CancellationReason.Error:
                print(f"❌ Error: {evt.result.error_details}")
            else:
                print(f"ℹ️  Cancellation details: {evt}")
        
        def stopped_cb(evt):
            """Callback when recognition stops"""
            nonlocal done
            done = True
        
        # Connect callbacks
        recognizer.session_started.connect(session_started_cb)
        recognizer.recognizing.connect(recognizing_cb)
        recognizer.recognized.connect(recognized_cb)
        recognizer.canceled.connect(canceled_cb)
        recognizer.session_stopped.connect(stopped_cb)
        
        # Start continuous recognition
        recognizer.start_continuous_recognition()
        
        # Wait for completion
        print("⏳ Transcribing... (this may take a few minutes)")
        while not done:
            import time
            time.sleep(0.5)
        
        recognizer.stop_continuous_recognition()
        
        print(f"✅ Transcription complete! Generated {len(subtitles)} subtitle segments")
        
        # Generate VTT file
        if output_vtt_path:
            self.generate_vtt_file(subtitles, output_vtt_path)
        
        return subtitles
    
    def generate_vtt_file(self, subtitles, output_path):
        """Generate WebVTT file from subtitle data"""
        print(f"📝 Generating VTT file: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for sub in subtitles:
                # Format timestamps (HH:MM:SS.mmm)
                start_time = self.format_timestamp(sub['start'])
                end_time = self.format_timestamp(sub['end'])
                
                # Write subtitle
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{sub['text']}\n\n")
        
        print(f"✅ VTT file created successfully!")
    
    def format_timestamp(self, seconds):
        """Format seconds to VTT timestamp (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def process_video(self, video_id, languages=['ja-JP']):
        """
        Complete workflow: Extract audio, transcribe, generate subtitles, upload
        
        Args:
            video_id: Video blob name (e.g., "03_定例会議/Recordings/video.mp4")
            languages: List of languages to generate subtitles for
        
        Returns:
            List of generated subtitle files
        """
        print(f"\n{'='*60}")
        print(f"🎬 Processing: {video_id}")
        print(f"{'='*60}\n")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        audio_file = os.path.join(temp_dir, 'audio.wav')
        
        try:
            # Step 1: Extract audio
            self.extract_audio_from_video(video_id, audio_file)
            
            generated_files = []
            
            # Step 2: Transcribe for each language
            for lang in languages:
                print(f"\n--- Generating {lang} subtitles ---\n")
                
                # Get language code for filename (ja-JP -> ja)
                lang_code = lang.split('-')[0]
                
                # Generate VTT filename
                video_base = video_id.rsplit('.', 1)[0] if '.' in video_id else video_id
                vtt_filename = f"{video_base}.{lang_code}.vtt"
                vtt_local_path = os.path.join(temp_dir, f'subtitle_{lang_code}.vtt')
                
                # Transcribe and generate VTT
                self.transcribe_audio_to_vtt(audio_file, language=lang, output_vtt_path=vtt_local_path)
                
                # Step 3: Upload VTT to Azure Blob Storage
                print(f"📤 Uploading subtitle to Azure Blob Storage...")
                
                with open(vtt_local_path, 'rb') as vtt_data:
                    blob_client = self.container_client.get_blob_client(vtt_filename)
                    blob_client.upload_blob(vtt_data, overwrite=True)
                
                print(f"✅ Uploaded: {vtt_filename}")
                generated_files.append(vtt_filename)
            
            print(f"\n{'='*60}")
            print(f"🎉 SUCCESS! Generated {len(generated_files)} subtitle file(s):")
            for f in generated_files:
                print(f"   ✓ {f}")
            print(f"{'='*60}\n")
            
            return generated_files
        
        finally:
            # Cleanup temporary files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Main function to generate subtitles for videos"""
    
    # Load configuration
    speech_key = os.environ.get('AZURE_SPEECH_KEY')
    speech_region = os.environ.get('AZURE_SPEECH_REGION', 'japaneast')
    storage_account = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
    blob_sas = os.environ.get('AZURE_STORAGE_SAS_TOKEN')
    
    if not all([speech_key, storage_account, blob_sas]):
        print("❌ Missing configuration. Please set environment variables:")
        print("   - AZURE_SPEECH_KEY")
        print("   - AZURE_SPEECH_REGION")
        print("   - AZURE_STORAGE_ACCOUNT_NAME")
        print("   - AZURE_STORAGE_SAS_TOKEN")
        return
    
    generator = AutoSubtitleGenerator(
        speech_key=speech_key,
        speech_region=speech_region,
        storage_account=storage_account,
        blob_sas_token=blob_sas
    )
    
    # Example: Process a video
    print("This script will generate automatic subtitles for your videos.")
    print("\nExample usage:")
    print("  1. Video ID: '03_定例会議/Recordings/video.mp4'")
    print("  2. Languages: ['ja-JP', 'en-US']")
    print("\nThe script will:")
    print("  - Extract audio from video")
    print("  - Transcribe using Azure Speech Services")
    print("  - Generate .vtt subtitle files")
    print("  - Upload to Azure Blob Storage")
    print("\nPress Ctrl+C to cancel")
    
    # Get video details from user
    video_id = input("\nEnter video ID (blob path): ").strip()
    
    if not video_id:
        print("❌ Video ID is required")
        return
    
    # Construct video URL
    container_url = f"https://{storage_account}.blob.core.windows.net/videos"
    video_url = f"{container_url}/{quote(video_id)}?{blob_sas}"
    
    # Ask for languages
    print("\nAvailable languages:")
    print("  ja-JP = Japanese")
    print("  en-US = English")
    print("  zh-CN = Chinese")
    print("  ko-KR = Korean")
    
    lang_input = input("\nEnter languages (comma-separated, e.g., 'ja-JP,en-US'): ").strip()
    languages = [l.strip() for l in lang_input.split(',') if l.strip()]
    
    if not languages:
        languages = ['ja-JP']  # Default to Japanese
    
    # Process video
    generator.process_video(video_id, video_url, languages)


if __name__ == '__main__':
    main()
