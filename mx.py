import os
import re
import requests
import subprocess
from bs4 import BeautifulSoup
import json
import m3u8

def get_master_m3u8_url(page_url):
    """Extract the master m3u8 URL from MX Player page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.mxplayer.in/'
        }
        
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()
        
        # Method 1: Search for Apollo State JSON
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and 'window.__APOLLO_STATE__' in script.string:
                json_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', script.string)
                if json_match:
                    data = json.loads(json_match.group(1))
                    for key in data:
                        if 'content' in key.lower() and 'playbackUrls' in data[key]:
                            for url in data[key]['playbackUrls']:
                                if url.get('url', '').endswith('.m3u8'):
                                    return url['url']
        
        # Method 2: Direct regex search
        m3u8_match = re.search(r'(https?://[^\s]+\.m3u8[^\s"]+)', response.text)
        if m3u8_match:
            return m3u8_match.group(1)
            
        raise Exception("Could not find master m3u8 URL")
    
    except Exception as e:
        print(f"Error extracting m3u8 URL: {e}")
        return None

def parse_m3u8_playlist(m3u8_url):
    """Parse the m3u8 playlist to get streams"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.mxplayer.in/'
        }
        
        # Download the master playlist
        response = requests.get(m3u8_url, headers=headers)
        response.raise_for_status()
        
        # Parse the m3u8 content
        playlist = m3u8.loads(response.text)
        
        # Get the highest quality video stream
        video_streams = [s for s in playlist.playlists if s.stream_info]
        if not video_streams:
            raise Exception("No video streams found in playlist")
        
        # Sort by bandwidth (highest first)
        video_streams.sort(key=lambda x: x.stream_info.bandwidth, reverse=True)
        best_video = video_streams[0]
        
        # Get audio streams
        audio_streams = [m for m in playlist.media if m.type == 'AUDIO']
        if not audio_streams:
            raise Exception("No audio streams found in playlist")
        
        # Get subtitles if available
        subtitle_streams = [m for m in playlist.media if m.type == 'SUBTITLES']
        
        return {
            'video_url': best_video.uri,
            'audio_url': audio_streams[0].uri,
            'subtitle_url': subtitle_streams[0].uri if subtitle_streams else None
        }
    
    except Exception as e:
        print(f"Error parsing m3u8 playlist: {e}")
        return None

def download_stream(url, output_name, stream_type):
    """Download a single stream using FFmpeg"""
    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        output_path = f'downloads/{output_name}_{stream_type}.ts'
        
        print(f"Downloading {stream_type} stream...")
        
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-y',
            '-headers', f'Referer: https://www.mxplayer.in/\r\nUser-Agent: Mozilla/5.0',
            '-i', url,
            '-c', 'copy',
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {stream_type} stream: {e}")
        return None

def mux_streams(video_path, audio_path, subtitle_path, output_name):
    """Mux all streams into a single MKV file"""
    try:
        output_path = f'downloads/{output_name}.mkv'
        
        print("Muxing streams into MKV...")
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-y',
            '-i', video_path,
            '-i', audio_path,
        ]
        
        if subtitle_path:
            ffmpeg_cmd.extend(['-i', subtitle_path])
        
        ffmpeg_cmd.extend([
            '-c', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
        ])
        
        if subtitle_path:
            ffmpeg_cmd.extend(['-map', '2:s:0'])
        
        ffmpeg_cmd.append(output_path)
        
        subprocess.run(ffmpeg_cmd, check=True)
        return output_path
    
    except subprocess.CalledProcessError as e:
        print(f"Failed to mux streams: {e}")
        return None

def clean_temp_files(output_name):
    """Remove temporary downloaded files"""
    temp_files = [
        f'downloads/{output_name}_video.ts',
        f'downloads/{output_name}_audio.ts',
        f'downloads/{output_name}_subs.vtt'
    ]
    
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

def main():
    mxplayer_url = "https://www.mxplayer.in/movie/watch-durgamati-the-myth-movie-online-dabbcbb947bf786d86051ed54659eddf?watch=true"
    output_name = "Durgamati_The_Myth"
    
    # Step 1: Get master m3u8 URL
    print("Extracting master m3u8 URL...")
    master_m3u8 = get_master_m3u8_url(mxplayer_url)
    if not master_m3u8:
        print("Failed to extract master m3u8 URL")
        return
    
    print(f"Master playlist URL: {master_m3u8}")
    
    # Step 2: Parse m3u8 to get individual streams
    print("Parsing m3u8 playlist...")
    streams = parse_m3u8_playlist(master_m3u8)
    if not streams:
        print("Failed to parse m3u8 playlist")
        return
    
    print(f"Video URL: {streams['video_url']}")
    print(f"Audio URL: {streams['audio_url']}")
    if streams['subtitle_url']:
        print(f"Subtitle URL: {streams['subtitle_url']}")
    
    # Step 3: Download all streams
    video_path = download_stream(streams['video_url'], output_name, 'video')
    if not video_path:
        return
    
    audio_path = download_stream(streams['audio_url'], output_name, 'audio')
    if not audio_path:
        return
    
    subtitle_path = None
    if streams['subtitle_url']:
        subtitle_path = download_stream(streams['subtitle_url'], output_name, 'subs')
    
    # Step 4: Mux all streams
    final_path = mux_streams(video_path, audio_path, subtitle_path, output_name)
    if not final_path:
        return
    
    # Step 5: Clean up temporary files
    clean_temp_files(output_name)
    
    print("\nDownload and muxing completed successfully!")
    print(f"Final file: {final_path}")

if __name__ == "__main__":
    # Check for required dependencies
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        import m3u8
    except (subprocess.CalledProcessError, ImportError) as e:
        print("Error: Missing required dependencies")
        print("Please install:")
        print("1. FFmpeg (https://ffmpeg.org/)")
        print("2. Python m3u8 package: pip install m3u8")
        exit(1)
    
    main()
