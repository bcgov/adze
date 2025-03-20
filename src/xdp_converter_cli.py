from InquirerPy import inquirer
import os
import time
import subprocess
import glob
from pathlib import Path
from filename_generator import REPORT_DIR, INPUT_DIR, OUTPUT_DIR
import platform

def get_latest_report():
    """Fetch the most recent report file from REPORT_DIR."""
    report_files = sorted(Path(REPORT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True)
    return str(report_files[0]) if report_files else None

def get_latest_output():
    """Fetch the most recent JSON output file from OUTPUT_DIR."""
    output_files = sorted(Path(OUTPUT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True)
    return str(output_files[0]) if output_files else None

def get_all_reports():
    """Fetch all report files sorted by most recent."""
    return [str(file) for file in sorted(Path(REPORT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True)]

def get_all_outputs():
    """Fetch all JSON output files sorted by most recent."""
    return [str(file) for file in sorted(Path(OUTPUT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True)]

def format_link(file_path):
    """Generate clickable file links that work across more terminals."""
    
    abs_path = Path(file_path).resolve()
    
    # Check terminal environment
    term = os.environ.get('TERM_PROGRAM', '')
    
    if term in ['iTerm.app', 'vscode'] or 'VSCODE' in os.environ:
        # Use OSC 8 for terminals that support it
        return f"\033]8;;file://{abs_path}\033\\{abs_path}\033]8;;\033\\"
    elif platform.system() == 'Darwin' and term == 'Apple_Terminal':
        # Mac Terminal fallback - just show the path
        return f"{abs_path}"
    else:
        # Default fallback
        return f"{abs_path}"

def run_conversion():
    xdp_file = inquirer.filepath(message="Select an XDP file to convert:").execute()
    output_dir = inquirer.text(
        message=f"Enter the output directory [Default: {OUTPUT_DIR}]:",
        default=OUTPUT_DIR
    ).execute()
    
    print("\n🛠 Converting XDP to JSON...\n")
    python_cmd = "python3" if os.name != "nt" else "python"
    script_path = os.path.join("src","xml_converter.py")
    result = subprocess.run([
        python_cmd, script_path, 
        "-f", os.path.normpath(xdp_file), 
        "-o", os.path.normpath(output_dir)
    ])

    time.sleep(1)  

    # Check if conversion failed
    if result.returncode != 0:
        print("\n❌ Conversion failed! Please check the logs for details.\n")
        return
    
    latest_report = get_latest_report()
    latest_output = get_latest_output()

    if latest_output:
        print(f"\n✅ Conversion complete! Output saved to: {format_link(latest_output)}")

    if latest_report:
        print(f"📊 Report generated: {format_link(latest_report)}\n")

def batch_process():
    """Batch process multiple XDP files while ensuring paths are correctly formatted."""
    input_dir = inquirer.text(message=f"Enter the input directory (default: {INPUT_DIR}):", default=INPUT_DIR).execute()
    output_dir = inquirer.text(message=f"Enter the output directory (default: {OUTPUT_DIR}):", default=OUTPUT_DIR).execute()

    # Convert paths to absolute & normalized versions
    input_dir = os.path.abspath(os.path.normpath(input_dir))
    output_dir = os.path.abspath(os.path.normpath(output_dir))

    print(f"\n🔍 Checking directories...\n  Input: {input_dir}\n  Output: {output_dir}")

    # Ensure input directory exists before running batch processing
    if not os.path.isdir(input_dir):
        print(f"\n❌ Error: The input directory '{input_dir}' does not exist or is not a valid directory.")
        print("Make sure the path is correct and contains XDP files.\n")
        return  # ✅ Exit early if input directory is invalid

    if not any(file.lower().endswith(".xdp") for file in os.listdir(input_dir)):
        print(f"\n⚠ Warning: The input directory '{input_dir}' is empty or contains no XDP files.")
        print("Ensure there are valid XDP files before running batch processing.\n")
        return  # ✅ Exit early if no XDP files are found

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Capture existing files before processing
    existing_outputs = set(os.listdir(output_dir))
    existing_reports = set(os.listdir(REPORT_DIR))

    print("\n🔄 Running batch processing...\n")

    python_cmd = "python3" if os.name != "nt" else "python"
    script_path = os.path.join("src", "xml_converter.py")
    result = subprocess.run([
        python_cmd, script_path,
        "--input-dir", input_dir,
        "--output-dir", output_dir
    ], capture_output=True, text=True)


    # If batch processing failed, exit early
    if result.returncode != 0:
        print("\n❌ Batch processing failed! Please check the logs for details.\n")
        return

    # Capture new files after processing
    new_outputs = set(os.listdir(output_dir)) - existing_outputs
    new_reports = set(os.listdir(REPORT_DIR)) - existing_reports

    print("\n✅ Batch processing complete!")

    if new_outputs:
        print("\n📂 Generated Output Files:")
        for file in new_outputs:
            print(f"   - {format_link(os.path.join(output_dir, file))}")

    if new_reports:
        print("\n📊 Generated Reports:")
        for file in new_reports:
            print(f"   - {format_link(os.path.join(REPORT_DIR, file))}")


def view_reports():
    """Allow the user to select and view a specific report file."""
    report_files = get_all_reports()
    
    if not report_files:
        print("\n⚠ No recent reports found! Run a conversion first.\n")
        return

    report_choices = [os.path.basename(f) for f in report_files]
    selected_report = inquirer.select(message="📊 Select a report to view:", choices=report_choices).execute()

    report_path = os.path.join(REPORT_DIR, selected_report)
    print(f"\n📊 Viewing report: {format_link(report_path)}")

    with open(report_path, "r") as f:
        print(f.read())

def main():
    while True:
        choice = inquirer.select(
            message="📌 Select an action:",
            choices=[
                "🔄 Convert a Single XDP File",
                "📂 Batch Process Multiple Files",
                "📊 View Reports",
                "❌ Exit"
            ]
        ).execute()

        if choice == "🔄 Convert a Single XDP File":
            run_conversion()
        elif choice == "📂 Batch Process Multiple Files":
            batch_process()
        elif choice == "📊 View Reports":
            view_reports()
        elif choice == "❌ Exit":
            print("\n👋 Exiting CLI. Goodbye!\n")
            break

if __name__ == "__main__":
    main()
