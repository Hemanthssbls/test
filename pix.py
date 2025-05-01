import requests
import sys
import os

def upload_to_pixeldrain(file_path):
    if not os.path.isfile(file_path):
        print("Error: File does not exist:", file_path)
        return

    url = 'https://pixeldrain.com/api/file'
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    if response.status_code == 200:
        result = response.json()
        file_id = result.get("id")
        print("Upload successful!")
        print("View link: https://pixeldrain.com/u/" + file_id)
        print("Direct download: https://pixeldrain.com/api/file/" + file_id)
    else:
        print("Upload failed:", response.status_code, response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 pix.py <file_path>")
    else:
        upload_to_pixeldrain(sys.argv[1])
