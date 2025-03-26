from flask import Flask, request, redirect, url_for, send_file, send_from_directory
import os
import subprocess
import glob

app = Flask(__name__)

INPUT_DIR = os.getenv("INPUT_DIR", "data/input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/output")
REPORT_DIR = os.getenv("REPORT_DIR", "data/report")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

@app.route('/')
def index():
    return redirect(url_for('upload_form'))

@app.route("/upload-form", methods=["GET"])
def upload_form():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Upload XDP Files</title></head>
    <body>
      <h2>Upload .xdp Files</h2>
      <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" multiple required>
        <br><br>
        <input type="submit" value="Upload and Convert">
      </form>
    </body>
    </html>
    '''

@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return "No file part", 400

    files = request.files.getlist("file")
    uploaded_files = []

    for f in files:
        filename = f.filename
        if filename:
            input_path = os.path.join(INPUT_DIR, filename)
            f.save(input_path)
            uploaded_files.append(filename)

    # Run batch conversion on the entire input folder
    try:
        subprocess.run([
            "python", "src/xml_converter.py",
            "--input-dir", INPUT_DIR,
            "--output-dir", OUTPUT_DIR,
        ], check=True)
    except subprocess.CalledProcessError as e:
        return f"Error during conversion: {e.stderr}", 500

    # Generate download links
    html = "<h2>Converted Output</h2><ul>"
    for name in uploaded_files:
        base = os.path.splitext(name)[0]
        
        # Find most recent output JSON
        json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_output_*.json")), reverse=True)
        report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_report_*.json")), reverse=True)
        
        json_file = os.path.basename(json_matches[0]) if json_matches else "Not found"
        report_file = os.path.basename(report_matches[0]) if report_matches else "Not found"

        if json_file != "Not found" and report_file != "Not found":
            html += f'<li><a href="/download/{json_file}">{json_file}</a> | <a href="/report/{report_file}">{report_file}</a></li>'
        else:
            html += f"<li>{base}: Conversion failed or files missing.</li>"

    html += '<br><a href="/upload-form"><button>⬅ Back to Upload</button></a>'

    return html

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

@app.route("/report/<filename>")
def report(filename):
    return send_from_directory(REPORT_DIR, filename, as_attachment=True)
