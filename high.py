import subprocess
import os
import sys
from pathlib import Path

def convert_to_heaac_5_1(input_file, output_file=None):
    """
    Convert audio file to HE-AAC 5.1 128kbps CBR 48000Hz
    
    Args:
        input_file (str): Path to input audio file
        output_file (str, optional): Path to output file. If None, will use input file with _heaac.m4a suffix
        
    Returns:
        str: Path to converted file
    """
    # Set output file if not provided
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.with_name(f"{input_path.stem}_heaac.m4a")
    
    # FFmpeg command for HE-AAC 5.1 conversion
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:a', 'libfdk_aac',
        '-profile:a', 'aac_he_v2',
        '-b:a', '128k',
        '-ar', '48000',
        '-ac', '6',
        '-channel_layout', '5.1',
        '-filter_complex', 'channelmap=channel_layout=5.1',
        '-vn',
        '-y',
        str(output_file)
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Successfully converted to {output_file}")
        return str(output_file)
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
        return None
    except FileNotFoundError:
        print("FFmpeg not found. Please install FFmpeg with libfdk_aac support.")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 high.py input_file [output_file]")
        print("Example: python3 high.py audio.m4a")
        print("Example: python3 high.py input.wav output.m4a")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' not found!")
        sys.exit(1)
    
    convert_to_heaac_5_1(input_file, output_file)
