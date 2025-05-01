from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

# Path to the directory containing your media files
MEDIA_FOLDER = '/root'  # Make sure the files you want to serve are readable here

@app.route('/download/<path:filename>')
def download_file(filename):
    file_path = os.path.join(MEDIA_FOLDER, filename)
    if os.path.isfile(file_path):
        return send_from_directory(MEDIA_FOLDER, filename, as_attachment=True)
    else:
        abort(404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
