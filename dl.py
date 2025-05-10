#!/usr/bin/env python3
import os
import sys
import requests
from m3u8 import M3U8
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

def download_segment(segment_url, output_path, headers=None):
    try:
        response = requests.get(segment_url, headers=headers, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {segment_url}: {e}")
        return False

def download_hls_video(m3u8_url, output_filename=None, headers=None):
    if not output_filename:
        output_filename = "output.mp4"
    
    try:
        # Parse the master playlist
        response = requests.get(m3u8_url, headers=headers)
        response.raise_for_status()
        
        # Load the m3u8 content
        base_url = m3u8_url[:m3u8_url.rfind('/')+1]
        m3u8_obj = M3U8(response.text, base_uri=base_url)
        
        # Get the best quality stream (highest bandwidth)
        if m3u8_obj.playlists:
            best_quality = max(m3u8_obj.playlists, key=lambda p: p.stream_info.bandwidth)
            playlist_url = urljoin(base_url, best_quality.uri)
            response = requests.get(playlist_url, headers=headers)
            response.raise_for_status()
            m3u8_obj = M3U8(response.text, base_uri=playlist_url[:playlist_url.rfind('/')+1])
        
        # Download all segments
        segments = m3u8_obj.segments
        print(f"Found {len(segments)} segments to download...")
        
        # Create temp directory for segments
        temp_dir = "temp_segments"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download segments in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i, segment in enumerate(segments):
                segment_url = urljoin(m3u8_obj.base_uri, segment.uri)
                segment_path = os.path.join(temp_dir, f"segment_{i:04d}.ts")
                futures.append(executor.submit(download_segment, segment_url, segment_path, headers))
            
            # Wait for all downloads to complete
            for i, future in enumerate(futures):
                if future.result():
                    print(f"Downloaded segment {i+1}/{len(segments)}", end='\r')
                else:
                    print(f"\nFailed to download segment {i+1}")
        
        # Combine segments into one file
        with open(output_filename, 'wb') as outfile:
            for i in range(len(segments)):
                segment_path = os.path.join(temp_dir, f"segment_{i:04d}.ts")
                try:
                    with open(segment_path, 'rb') as infile:
                        outfile.write(infile.read())
                except FileNotFoundError:
                    print(f"\nMissing segment {i}, skipping")
        
        print(f"\nVideo successfully saved as {output_filename}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
        
    finally:
        # Clean up temp files
        if os.path.exists(temp_dir):
            for i in range(len(segments)):
                segment_path = os.path.join(temp_dir, f"segment_{i:04d}.ts")
                try:
                    os.remove(segment_path)
                except FileNotFoundError:
                    pass
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dl.py <m3u8_url> [output_filename]")
        print("Example: python dl.py https://example.com/playlist.m3u8 video.mp4")
        sys.exit(1)
    
    m3u8_url = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Optional: Add headers if needed (e.g., for authenticated streams)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    download_hls_video(m3u8_url, output_filename, headers)
