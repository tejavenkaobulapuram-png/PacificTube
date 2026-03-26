"""
Generate chapters from existing subtitle files
Analyzes .vtt subtitle files to detect topic changes
"""

import os
import re
import json
from app import VideoService, ViewTracker
import requests

# Topic transition keywords (Japanese) - Expanded for meetings
TRANSITION_PHRASES = [
    # Explicit transitions
    r'次に',
    r'続いて',
    r'それでは',
    r'次の議題',
    r'次回',
    
    # Topic introductions  
    r'について.*説明',
    r'について.*紹介',
    r'について.*お話',
    r'について.*報告',
    r'について.*共有',
    
    # Demonstrations
    r'デモ.*見',
    r'デモ.*行',
    r'画面.*共有',
    r'見て.*いただ',
    
    # Q&A
    r'質問.*受付',
    r'質疑応答',
    r'Q.*A',
    r'質問.*ありま',
    r'何か.*質問',
    
    # Speaker changes
    r'私.*方',
    r'僕.*方',
    r'発表.*させ',
    r'紹介.*させ',
    
    # Closings
    r'まとめ',
    r'最後に',
    r'終わり',
    r'クロージング',
    r'以上です',
    
    # Agenda items
    r'一つ目',
    r'二つ目',
    r'三つ目',
    r'最初',
    r'一番目',
]

def parse_vtt_file(vtt_content):
    """Parse VTT subtitle file and return list of segments with timestamps and text"""
    segments = []
    
    lines = vtt_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for timestamp line (format: 00:00:05.000 --> 00:00:10.000)
        if '-->' in line:
            try:
                # Parse timestamps
                start_str, end_str = line.split('-->')
                start_seconds = parse_vtt_timestamp(start_str.strip())
                end_seconds = parse_vtt_timestamp(end_str.strip())
                
                # Get text from next lines until empty line
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                text = ' '.join(text_lines)
                
                # IMPORTANT: Remove spaces between Japanese characters (Azure Speech adds them)
                text = text.replace(' ', '')
                
                if text:
                    segments.append({
                        'start': start_seconds,
                        'end': end_seconds,
                        'text': text
                    })
            except:
                pass
        
        i += 1
    
    return segments

def parse_vtt_timestamp(timestamp_str):
    """Convert VTT timestamp (HH:MM:SS.mmm) to seconds"""
    # Remove any extra chars
    timestamp_str = timestamp_str.strip()
    
    # Parse HH:MM:SS.mmm or MM:SS.mmm
    parts = timestamp_str.split(':')
    
    if len(parts) == 3:  # HH:MM:SS.mmm
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    elif len(parts) == 2:  # MM:SS.mmm
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    else:
        return 0
    
    return hours * 3600 + minutes * 60 + seconds

def detect_topics_from_segments(segments):
    """
    Analyze subtitle segments to detect topic changes
    Returns list of chapters with timestamps and PLACEHOLDER titles for user editing
    Note: Automatic topic extraction from conversation is difficult, so we provide
    numbered placeholders that users can quickly edit to actual topics
    """
    print(f"\n🔍 Analyzing {len(segments)} subtitle segments to detect topic changes...")
    
    chapters = []
    last_chapter_time = 0
    MIN_CHAPTER_GAP = 120  # Minimum 2 minutes between chapters
    chapter_number = 1
    
    # Always start with chapter at 0:00
    if segments:
        chapters.append({
            'timestamp': '0:00',
            'title': '会議開始・アジェンダ紹介'
        })
    
    for i, segment in enumerate(segments):
        text = segment['text']
        start_time = segment['start']
        
        # Check if enough time has passed since last chapter
        if start_time - last_chapter_time < MIN_CHAPTER_GAP:
            continue
        
        # Check for transition phrases or keywords that indicate topic change
        is_transition = False
        transition_type = None
        
        # Detect explicit transitions
        if re.search(r'(次に|続いて|それでは次|一つ目|二つ目|三つ目|最初|次の議題)', text):
            is_transition = True
            transition_type = 'topic'
        
        # Detect Q&A/discussion
        elif re.search(r'(質問|質疑応答|何かご質問|いかがでしょう)', text):
            is_transition = True
            transition_type = 'qa'
        
        # Detect demo/presentation
        elif re.search(r'(画面.*共有|デモ.*見|紹介.*させ|説明.*させ|報告.*させ)', text):
            is_transition = True
            transition_type = 'demo'
        
        # Detect closing
        elif re.search(r'(私.*以上|以上です|まとめ|クロージング|次回)', text):
            is_transition = True
            transition_type = 'closing'
        
        if is_transition:
            # Generate appropriate placeholder title
            if transition_type == 'qa':
                title = f"質疑応答・ディスカッション"
            elif transition_type == 'demo':
                title = f"議題{chapter_number}：デモ・実演"
                chapter_number += 1
            elif transition_type == 'closing':
                title = "まとめ・次回予定"
            else:
                title = f"議題{chapter_number}：[トピック名を入力]"
                chapter_number += 1
            
            chapters.append({
                'timestamp': format_timestamp(start_time),
                'title': title
            })
            last_chapter_time = start_time
            print(f"   📋 Chapter at {format_timestamp(start_time)}: {title}")
        
        # Detect long pauses (gap > 5 seconds = likely topic change)
        if i < len(segments) - 1:
            next_segment = segments[i + 1]
            gap = next_segment['start'] - segment['end']
            
            if gap > 5.0 and start_time - last_chapter_time >= MIN_CHAPTER_GAP:
                title = f"議題{chapter_number}：[トピック名を入力]"
                chapter_number += 1
                
                chapters.append({
                    'timestamp': format_timestamp(next_segment['start']),
                    'title': title
                })
                last_chapter_time = next_segment['start']
                print(f"   📋 Chapter at {format_timestamp(next_segment['start'])} (after {gap:.1f}s pause): {title}")
    
    print(f"\n   ✅ Detected {len(chapters)} chapters with placeholder titles")
    print(f"   ℹ️  Edit the '[トピック名を入力]' placeholders with actual topic names")
    return chapters

def extract_topic_from_context(context, timestamp):
    """
    Analyze wider conversation context to extract meaningful topic
    Uses keyword extraction, pattern matching, and frequency analysis
    """
    # Remove all filler words
    context_clean = re.sub(r'(えーと|あの|そのー|まあ|ええ|はい|ですね|ますね|ました|します|じゃあ|では|それでは)', '', context)
    
    # Look for explicit topic announcements first
    topic_patterns = [
        r'([ぁ-んァ-ヶー一-龠]{3,20})(?:について|に関して|の話|の件)(?:です|ます|お話|説明|紹介|報告)',
        r'(?:次に|続いて|それでは)([ぁ-んァ-ヶー一-龠]{3,20})(?:について|です|ます|を)',
        r'([ぁ-んァ-ヶー一-龠]{3,20})(?:の説明|の紹介|の報告|のデモ|の共有)',
        r'(?:本日は|今日は)([ぁ-んァ-ヶー一-龠]{3,20})(?:について|です|を)',
    ]
    
    for pattern in topic_patterns:
        matches = re.findall(pattern, context_clean)
        for match in matches:
            if len(match) >= 3 and not re.match(r'^(最初|一つ目|二つ目|定刻)', match):
                # Clean up and return
                topic = match.strip()
                topic = re.sub(r'[、。].*$', '', topic)
                if len(topic) >= 3:
                    return topic[:35]
    
    # Extract compound nouns and technical terms (3-15 characters, appears multiple times)
    # Common in Japanese: カタカナ words (AI, DX, etc.) and Kanji compounds
    technical_terms = re.findall(r'[ァ-ヶー]{2,10}|[一-龠]{2,10}', context_clean)
    
    # Count frequency
    from collections import Counter
    term_freq = Counter(technical_terms)
    
    # Filter out common words
    stopwords = ['します', 'ですね', 'ました', 'ですが', 'ようなやつ', 'ているん', 'ますが', 
                 'いただき', 'ください', 'ありがとう', 'よろしく', 'お願い', 'ござい',
                 '会議', '定刻', '時間', '今日', '本日', '以上', '次回', '皆さん']
    
    for term, count in term_freq.most_common(10):
        if count >= 2 and len(term) >= 3 and term not in stopwords:
            # This term appears multiple times - likely the topic
            # Try to find it with context words
            context_pattern = f'({term}[ぁ-んァ-ヶー一-龠]{{0,15}}(?:について|の話|機能|システム|ツール|報告|紹介)?)'
            match = re.search(context_pattern, context_clean)
            if match:
                topic = match.group(1).strip()
                topic = re.sub(r'[、。].*$', '', topic)
                if 3 <= len(topic) <= 35:
                    return topic
            else:
                # Just return the term itself
                if 3 <= len(term) <= 35:
                    return term
    
    # Fallback: Look for action-oriented phrases
    action_patterns = [
        r'([ぁ-んァ-ヶー一-龠]{4,20})(?:を|の)(?:説明|紹介|共有|報告|デモ)',
        r'([ぁ-んァ-ヶー一-龠]{4,20})(?:について質問|についての質疑)',
        r'([ぁ-んァ-ヶー一-龠]{4,20})(?:の進捗|の状況|の確認)',
    ]
    
    for pattern in action_patterns:
        match = re.search(pattern, context_clean)
        if match:
            topic = match.group(1).strip()
            if 3 <= len(topic) <= 35:
                return topic
    
    # Last resort: Extract longest meaningful noun phrase
    noun_phrases = re.findall(r'[ぁ-んァ-ヶー一-龠]{5,25}', context_clean)
    for phrase in noun_phrases:
        # Skip if it's clearly a sentence fragment
        if not re.search(r'(ですが|ますが|ているん|いただき|お願い|ござい)', phrase):
            if 5 <= len(phrase) <= 35:
                return phrase
    
    return None


def extract_topic_title(text):
    """
    Legacy function - kept for compatibility
    Calls extract_topic_from_context with smaller context
    """
    return extract_topic_from_context(text, 0)

def format_timestamp(seconds):
    """Convert seconds to M:SS or H:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def save_chapters(chapters, video_path):
    """Save chapters to JSON file"""
    # Extract base name without extension
    filename = os.path.basename(video_path).replace('.mp4', '')
    output_file = f"chapters/{filename}.chapters.json"
    
    os.makedirs('chapters', exist_ok=True)
    
    data = {'chapters': chapters}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_file

def main(video_path):
    print("=" * 70)
    print("Chapter Generator - From Existing Subtitles")
    print("=" * 70)
    print(f"\nVideo: {video_path}\n")
    
    # Get subtitle file
    vt = ViewTracker()
    vs = VideoService(vt)
    
    print("📥 Fetching subtitle file...")
    subtitles = vs.get_subtitles(video_path)
    
    if not subtitles:
        print("❌ No subtitle file found for this video.")
        print("   Please generate subtitles first using Azure Speech Service.")
        return
    
    # Download subtitle content
    subtitle_url = subtitles[0]['url']
    print(f"   ✅ Found subtitle: {subtitles[0]['lang']}")
    print(f"\n📄 Downloading subtitle content...")
    
    response = requests.get(subtitle_url)
    vtt_content = response.text
    
    # Parse VTT file
    segments = parse_vtt_file(vtt_content)
    print(f"   ✅ Parsed {len(segments)} subtitle segments")
    
    if not segments:
        print("❌ No text found in subtitle file.")
        return
    
    # Detect topics
    chapters = detect_topics_from_segments(segments)
    
    if not chapters or len(chapters) < 2:
        print("⚠️ Not enough chapters detected. Using manual editing recommended.")
        chapters = [
            {'timestamp': '0:00', 'title': '会議開始'},
            {'timestamp': '30:00', 'title': '議題討議'},
            {'timestamp': '60:00', 'title': 'まとめ'}
        ]
    
    # Save chapters
    output_file = save_chapters(chapters, video_path)
    
    print(f"\n✅ Generated {len(chapters)} chapters")
    print(f"💾 Saved to: {output_file}")
    
    print("\n" + "=" * 70)
    print("Generated Chapters:")
    print("=" * 70)
    for chapter in chapters:
        print(f"  {chapter['timestamp']} - {chapter['title']}")
    
    print(f"\nNext steps:")
    print(f"  1. Review and edit: {output_file}")
    print(f"  2. Upload to blob: python upload_chapters.py")
    print(f"  3. Deploy: .\\quick-deploy.ps1")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python generate_chapters_from_subtitles.py <video_path>")
        print("\nExample:")
        print('  python generate_chapters_from_subtitles.py "03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4"')
        sys.exit(1)
    
    video_path = sys.argv[1]
    main(video_path)
