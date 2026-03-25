"""
Batch Subtitle Generator for PacificTube
Uses Azure Batch Transcription API for long videos (no 20-30 min limit!)
"""

import os
import time
import json
import requests
from datetime import datetime
from generate_subtitles import AutoSubtitleGenerator
from dotenv import load_dotenv

load_dotenv()


class BatchSubtitleGenerator(AutoSubtitleGenerator):
    """Extended generator using Azure Batch Transcription API for long videos"""
    
    def __init__(self, speech_key, speech_region, storage_account, blob_sas_token):
        super().__init__(speech_key, speech_region, storage_account, blob_sas_token)
        self.batch_api_base = f"https://{speech_region}.api.cognitive.microsoft.com/speechtotext/v3.1"
    
    def check_existing_subtitle(self, video_id):
        """
        Check if subtitle already exists and is complete
        Returns: (exists, is_complete, file_size, last_timestamp)
        """
        subtitle_blob_name = video_id.replace('.mp4', '.ja.vtt')
        
        try:
            blob_client = self.container_client.get_blob_client(subtitle_blob_name)
            properties = blob_client.get_blob_properties()
            file_size = properties.size
            
            # Determine if subtitle is complete based on file size AND content check
            # 10 bytes = "WEBVTT\n" only (failed)
            # < 1000 bytes = likely incomplete for a 40+ min video
            # 1-100KB = might be partial (need to check last timestamp)
            # > 100KB = likely complete
            
            if file_size <= 10:
                return True, False, file_size  # Exists but failed
            elif file_size < 1000:
                return True, False, file_size  # Exists but likely partial
            elif file_size < 100000:  # Between 1KB and 100KB - need deeper check
                # Download and check last timestamp
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.vtt', mode='w', encoding='utf-8')
                
                try:
                    # Download subtitle content
                    download_stream = blob_client.download_blob()
                    content = download_stream.readall().decode('utf-8')
                    temp_file.write(content)
                    temp_file.close()
                    
                    # Parse last timestamp
                    last_timestamp = self._get_last_timestamp_from_vtt(content)
                    
                    # If last timestamp < 30 minutes, likely partial for our videos (40-90 min)
                    if last_timestamp < 1800:  # 30 minutes in seconds
                        return True, False, file_size  # Partial - stopped early
                    else:
                        return True, True, file_size  # Likely complete
                        
                finally:
                    import os
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
            else:
                return True, True, file_size  # > 100KB = definitely complete
                
        except Exception:
            return False, False, 0  # Doesn't exist
    
    def _get_last_timestamp_from_vtt(self, vtt_content):
        """
        Parse VTT content and get last timestamp in seconds
        Returns: last timestamp in seconds (float)
        """
        lines = vtt_content.strip().split('\n')
        last_timestamp = 0.0
        
        for line in lines:
            # Look for timestamp lines (format: 00:20:27.000 --> 00:20:30.000)
            if '-->' in line:
                parts = line.split('-->')
                if len(parts) == 2:
                    # Parse end timestamp
                    end_time = parts[1].strip().split()[0]  # Remove any extra info
                    try:
                        # Parse HH:MM:SS.mmm
                        time_parts = end_time.split(':')
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        seconds = float(time_parts[2])
                        
                        timestamp_seconds = hours * 3600 + minutes * 60 + seconds
                        last_timestamp = max(last_timestamp, timestamp_seconds)
                    except:
                        pass
        
        return last_timestamp
    
    def upload_audio_to_blob(self, audio_file_path, blob_name):
        """
        Upload audio file to Azure Blob Storage for Batch API access
        Returns: SAS URL for the blob
        """
        print(f"[INFO] Uploading audio to Azure Blob Storage...")
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        with open(audio_file_path, 'rb') as audio_file:
            blob_client.upload_blob(audio_file, overwrite=True)
        
        # Generate SAS URL (Batch API needs accessible URL)
        blob_url = f"https://{self.storage_account}.blob.core.windows.net/videos/{blob_name}?{self.blob_sas_token}"
        
        print(f"[DONE] Audio uploaded: {blob_name}")
        return blob_url
    
    def create_batch_transcription(self, audio_url, language='ja-JP'):
        """
        Submit audio file to Azure Batch Transcription API
        Returns: transcription ID
        """
        print(f"[INFO] Submitting to Batch Transcription API...")
        
        headers = {
            'Ocp-Apim-Subscription-Key': self.speech_key,
            'Content-Type': 'application/json'
        }
        
        # Batch transcription request
        payload = {
            'contentUrls': [audio_url],
            'locale': language,
            'displayName': f'PacificTube Subtitle - {datetime.now().isoformat()}',
            'properties': {
                'wordLevelTimestampsEnabled': True,
                'punctuationMode': 'DictatedAndAutomatic',
                'profanityFilterMode': 'None'
            }
        }
        
        response = requests.post(
            f"{self.batch_api_base}/transcriptions",
            headers=headers,
            json=payload
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Batch API submission failed: {response.status_code} - {response.text}")
        
        result = response.json()
        transcription_id = result['self'].split('/')[-1]
        
        print(f"[DONE] Transcription submitted: {transcription_id}")
        return transcription_id
    
    def poll_transcription_status(self, transcription_id, max_wait_minutes=30):
        """
        Poll transcription status until complete or failed
        Returns: transcription result object
        """
        headers = {
            'Ocp-Apim-Subscription-Key': self.speech_key
        }
        
        print(f"[WAIT] Waiting for transcription to complete (max {max_wait_minutes} minutes...)")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while True:
            # Check if timeout
            if time.time() - start_time > max_wait_seconds:
                raise Exception(f"Transcription timed out after {max_wait_minutes} minutes")
            
            # Get transcription status
            response = requests.get(
                f"{self.batch_api_base}/transcriptions/{transcription_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get transcription status: {response.status_code}")
            
            result = response.json()
            status = result['status']
            
            elapsed = int(time.time() - start_time)
            print(f"   Status: {status} (elapsed: {elapsed}s)", end='\r')
            
            if status == 'Succeeded':
                print(f"\n[DONE] Transcription completed in {elapsed} seconds")
                return result
            elif status == 'Failed':
                error = result.get('properties', {}).get('error', 'Unknown error')
                raise Exception(f"Transcription failed: {error}")
            
            # Wait 5 seconds before next poll
            time.sleep(5)
    
    def download_transcription_results(self, transcription_id):
        """
        Download transcription results with word-level timestamps
        Returns: list of subtitle segments with timestamps
        """
        print(f"[INFO] Downloading transcription results...")
        
        headers = {
            'Ocp-Apim-Subscription-Key': self.speech_key
        }
        
        # Get files list
        response = requests.get(
            f"{self.batch_api_base}/transcriptions/{transcription_id}/files",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get transcription files: {response.status_code}")
        
        files = response.json()['values']
        
        # Find the transcription result file
        result_file = None
        for file in files:
            if file['kind'] == 'Transcription':
                result_file = file
                break
        
        if not result_file:
            raise Exception("No transcription result file found")
        
        # Download transcription content
        content_url = result_file['links']['contentUrl']
        response = requests.get(content_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download transcription content: {response.status_code}")
        
        transcription_data = response.json()
        
        # Parse into subtitle segments
        subtitles = []
        
        if 'combinedRecognizedPhrases' in transcription_data:
            # Get all phrases
            for phrase in transcription_data['combinedRecognizedPhrases']:
                if 'display' in phrase:
                    # Get word-level timestamps if available
                    if 'recognizedPhrases' in transcription_data:
                        for recognized in transcription_data['recognizedPhrases']:
                            if 'nBest' in recognized and len(recognized['nBest']) > 0:
                                best = recognized['nBest'][0]
                                if 'words' in best:
                                    # Group words into chunks (10 words or 5 seconds)
                                    chunk = []
                                    chunk_start = None
                                    
                                    for word in best['words']:
                                        # Convert duration string to seconds (PT format)
                                        offset_sec = self._parse_duration(word['offset'])
                                        duration_sec = self._parse_duration(word['duration'])
                                        
                                        if chunk_start is None:
                                            chunk_start = offset_sec
                                        
                                        chunk.append(word['word'])
                                        
                                        # Create subtitle every 10 words or 5 seconds
                                        if len(chunk) >= 10 or (offset_sec - chunk_start) >= 5.0:
                                            chunk_end = offset_sec + duration_sec
                                            subtitles.append({
                                                'start': chunk_start,
                                                'end': chunk_end,
                                                'text': ' '.join(chunk)
                                            })
                                            chunk = []
                                            chunk_start = None
                                    
                                    # Add remaining words
                                    if chunk:
                                        last_word = best['words'][-1]
                                        chunk_end = self._parse_duration(last_word['offset']) + \
                                                   self._parse_duration(last_word['duration'])
                                        subtitles.append({
                                            'start': chunk_start,
                                            'end': chunk_end,
                                            'text': ' '.join(chunk)
                                        })
        
        print(f"[DONE] Parsed {len(subtitles)} subtitle segments")
        return subtitles
    
    def _parse_duration(self, pt_duration):
        """
        Parse ISO 8601 duration format (PT1H2M3.456S) to seconds
        """
        if not pt_duration or not pt_duration.startswith('PT'):
            return 0.0
        
        duration = pt_duration[2:]  # Remove 'PT'
        
        hours = 0
        minutes = 0
        seconds = 0.0
        
        if 'H' in duration:
            hours, duration = duration.split('H')
            hours = float(hours)
        
        if 'M' in duration:
            minutes, duration = duration.split('M')
            minutes = float(minutes)
        
        if 'S' in duration:
            seconds = float(duration.replace('S', ''))
        
        return hours * 3600 + minutes * 60 + seconds
    
    def delete_transcription(self, transcription_id):
        """Clean up: delete transcription from Azure"""
        headers = {
            'Ocp-Apim-Subscription-Key': self.speech_key
        }
        
        requests.delete(
            f"{self.batch_api_base}/transcriptions/{transcription_id}",
            headers=headers
        )
        print(f"[INFO] Cleaned up transcription: {transcription_id}")
    
    def process_video_batch(self, video_id, languages=['ja-JP']):
        """
        Process video using Batch Transcription API (no duration limit!)
        
        This method replaces the continuous recognition approach with batch processing:
        1. Extract audio from video
        2. Upload audio to Azure Blob Storage
        3. Submit to Batch Transcription API
        4. Poll until complete
        5. Download results and convert to VTT
        6. Upload VTT to blob storage
        """
        print("="*60)
        print(f"Processing: {video_id}")
        print("="*60)
        print()
        
        # Check if subtitle already exists and is complete
        exists, is_complete, file_size = self.check_existing_subtitle(video_id)
        
        if exists and is_complete:
            print(f"[SKIP] Subtitle already exists and is complete ({file_size:,} bytes)")
            print(f"       File: {video_id.replace('.mp4', '.ja.vtt')}")
            return
        elif exists and not is_complete:
            print(f"[REGENERATE] Existing subtitle is incomplete ({file_size} bytes)")
        else:
            print(f"[NEW] No subtitle found, creating new one")
        
        print()
        
        # Create temp directory for audio files
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        try:
            for language in languages:
                print(f"--- Generating {language} subtitles ---")
                print()
                
                # Step 1: Extract audio
                audio_file = os.path.join(temp_dir, 'audio.wav')
                self.extract_audio_from_video(video_id, audio_file)
                print()
                
                # Step 2: Upload audio to blob storage
                audio_blob_name = f"temp_audio/{video_id.replace('.mp4', f'_{language}.wav')}"
                audio_url = self.upload_audio_to_blob(audio_file, audio_blob_name)
                print()
                
                # Step 3: Submit to Batch Transcription API
                transcription_id = self.create_batch_transcription(audio_url, language)
                print()
                
                # Step 4: Poll for completion
                result = self.poll_transcription_status(transcription_id, max_wait_minutes=30)
                print()
                
                # Step 5: Download results
                subtitles = self.download_transcription_results(transcription_id)
                print()
                
                # Step 6: Generate VTT file
                vtt_file = os.path.join(temp_dir, f'subtitle_{language}.vtt')
                self.generate_vtt_file(subtitles, vtt_file)
                print()
                
                # Step 7: Upload VTT to blob storage
                subtitle_blob_name = video_id.replace('.mp4', f'.{language.split("-")[0]}.vtt')
                self.upload_subtitle_to_blob(vtt_file, subtitle_blob_name)
                print()
                
                # Step 8: Cleanup
                self.delete_transcription(transcription_id)
                
                # Delete temp audio from blob (optional - don't fail if this fails)
                try:
                    temp_blob_client = self.container_client.get_blob_client(audio_blob_name)
                    temp_blob_client.delete_blob()
                    print(f"[INFO] Cleaned up temp audio: {audio_blob_name}")
                except Exception as cleanup_error:
                    print(f"[WARN] Could not delete temp audio (not critical): {audio_blob_name}")
                    # Not critical - continue without failing
                
                print()
                
                print(f"[SUCCESS] Generated {language} subtitle!")
                print()
        
        finally:
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        print("="*60)
        print(f"[COMPLETED] {video_id}")
        print("="*60)
        print()
    
    def upload_subtitle_to_blob(self, vtt_file_path, blob_name):
        """Upload generated VTT file to Azure Blob Storage"""
        print(f"[INFO] Uploading subtitle to Azure Blob Storage...")
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        with open(vtt_file_path, 'rb') as vtt_file:
            blob_client.upload_blob(vtt_file, overwrite=True)
        
        print(f"[DONE] Uploaded: {blob_name}")


# Example usage
if __name__ == '__main__':
    # Initialize generator
    generator = BatchSubtitleGenerator(
        speech_key=os.environ.get('AZURE_SPEECH_KEY'),
        speech_region=os.environ.get('AZURE_SPEECH_REGION', 'japaneast'),
        storage_account=os.environ.get('AZURE_STORAGE_ACCOUNT_NAME'),
        blob_sas_token=os.environ.get('AZURE_STORAGE_SAS_TOKEN')
    )
    
    # Discover all MP4 videos in blob storage
    print("="*70)
    print("BATCH SUBTITLE GENERATOR - Azure Speech Services")
    print("="*70)
    print()
    print("Discovering videos in blob storage...")
    
    all_blobs = list(generator.container_client.list_blobs())
    video_ids = [b.name for b in all_blobs if b.name.endswith('.mp4')]
    
    print(f"Found {len(video_ids)} videos total")
    print()
    
    # Track results
    processed = []
    skipped = []
    failed = []
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Processing: {video_id}")
        print("="*60)
        
        # Check if subtitle already exists and is complete
        exists, is_complete, file_size = generator.check_existing_subtitle(video_id)
        
        if exists and is_complete:
            print(f"[SKIP] Subtitle already exists and is complete ({file_size:,} bytes)")
            print(f"       File: {video_id.replace('.mp4', '.ja.vtt')}")
            skipped.append(video_id)
            print()
            continue
        elif exists and not is_complete:
            print(f"[REGEN] Subtitle exists but is incomplete ({file_size:,} bytes)")
            print(f"        Will regenerate...")
        else:
            print(f"[NEW] No subtitle found, generating...")
        
        try:
            generator.process_video_batch(video_id, languages=['ja-JP'])
            processed.append(video_id)
        except Exception as e:
            print(f"[ERROR] Failed to process {video_id}: {str(e)}")
            failed.append(video_id)
        
        print()
    
    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total videos:     {len(video_ids)}")
    print(f"Processed:        {len(processed)}")
    print(f"Skipped (exist):  {len(skipped)}")
    print(f"Failed:           {len(failed)}")
    
    if processed:
        print()
        print("Processed videos:")
        for v in processed:
            print(f"  ✅ {v}")
    
    if failed:
        print()
        print("Failed videos:")
        for v in failed:
            print(f"  ❌ {v}")
