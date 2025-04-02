from flask import Flask, request, redirect, url_for, send_file, send_from_directory
import os
import subprocess
import glob
import traceback
import sys

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

    # Process each file based on its type
    for filename in uploaded_files:
        try:
            # Process both XDP and XML files using xdp_converter_cli.py
            base_name = os.path.splitext(filename)[0]
            output_file = os.path.join(OUTPUT_DIR, f"{base_name}_output.json")
            input_file = os.path.join(INPUT_DIR, filename)
            mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_mapping.json")
            
            # Print debug information
            print(f"Processing file: {filename}")
            print(f"Input file path: {input_file}")
            print(f"Output file path: {output_file}")
            print(f"Mapping file path: {mapping_file}")
            
            # Ensure input file exists
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Input file not found: {input_file}")
            
            # Run the converter with detailed error handling
            cmd = [
                sys.executable, "src/xdp_converter_cli.py",
                "-i", input_file,
                "-o", output_file,
            ]
            
            # Add mapping file for XML files
            if filename.lower().endswith('.xml'):
                cmd.extend(["-m", mapping_file])
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print(f"Conversion output: {result.stdout}")
            
            # Verify output file was created
            if not os.path.exists(output_file):
                raise FileNotFoundError(f"Output file was not created: {output_file}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Error processing {filename}: {e.stderr if e.stderr else 'No error message available'}"
            print(error_msg)
            print(f"Return code: {e.returncode}")
            print(f"Command output: {e.output if hasattr(e, 'output') else 'No output available'}")
            return f"{error_msg}<br><br><a href='/upload-form'><button>⬅ Back to Upload</button></a>", 500
        except Exception as e:
            error_msg = f"Unexpected error processing {filename}: {str(e)}"
            print(error_msg)
            return f"{error_msg}<br><br><a href='/upload-form'><button>⬅ Back to Upload</button></a>", 500

    # Generate download links
    html = "<h2>Converted Output</h2><ul>"
    for name in uploaded_files:
        base = os.path.splitext(name)[0]
        file_ext = os.path.splitext(name)[1].lower()
        
        # Find most recent output JSON - check for different patterns based on file type
        if file_ext == '.xdp':
            # For XDP files, try both patterns
            json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_xdp_output_*.json")), reverse=True)
            if not json_matches:
                json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_output.json")), reverse=True)
            
            report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_xdp_report_*.json")), reverse=True)
            if not report_matches:
                report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_report.json")), reverse=True)
        elif file_ext == '.xml':
            # For XML files, try both patterns
            json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_xml_output_*.json")), reverse=True)
            if not json_matches:
                json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_output.json")), reverse=True)
            
            report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_xml_report_*.json")), reverse=True)
            if not report_matches:
                report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_report.json")), reverse=True)
        else:
            # For other file types, try both patterns
            json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_output_*.json")), reverse=True)
            if not json_matches:
                json_matches = sorted(glob.glob(os.path.join(OUTPUT_DIR, f"{base}_output.json")), reverse=True)
            
            report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_report_*.json")), reverse=True)
            if not report_matches:
                report_matches = sorted(glob.glob(os.path.join(REPORT_DIR, f"{base}_report.json")), reverse=True)
        
        json_file = os.path.basename(json_matches[0]) if json_matches else "Not found"
        report_file = os.path.basename(report_matches[0]) if report_matches else "Not found"

        print(f"JSON file: {json_file}")
        print(f"Report file: {report_file}")

        if json_file != "Not found":
            html += f'<li><a href="/download/{json_file}">{json_file}</a>'
            if report_file != "Not found":
                html += f' | <a href="/report/{report_file}">{report_file}</a>'
            html += '</li>'
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

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 5000))
    # Get host from environment variable or use default
    host = os.getenv("HOST", "0.0.0.0")
    # Run the Flask app
    app.run(host=host, port=port, debug=True)
