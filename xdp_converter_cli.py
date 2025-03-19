from InquirerPy import inquirer
import os
import time
import subprocess
import glob
from pathlib import Path
from filename_generator import REPORT_DIR, INPUT_DIR, OUTPUT_DIR

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
    """Generate clickable file links."""
    abs_path = Path(file_path).resolve()
    return f"\033]8;;file://{abs_path}\033\\{abs_path}\033]8;;\033\\"

def run_conversion():
    xdp_file = inquirer.filepath(message="Select an XDP file to convert:").execute()
    output_dir = inquirer.text(message=f"Enter the output directory (default: {OUTPUT_DIR}):", default=OUTPUT_DIR).execute()

    
    print("\n🛠 Converting XDP to JSON...\n")
    python_cmd = "python3" if os.name != "nt" else "python"
    subprocess.run([python_cmd, "xml_converter.py", "-f", f'"{xdp_file}"', "-o", f'"{output_dir}"'])
    time.sleep(1)  

    latest_report = get_latest_report()
    latest_output = get_latest_output()

    if latest_output:
        print(f"\n✅ Conversion complete! Output saved to: {format_link(latest_output)}")

    if latest_report:
        print(f"📊 Report generated: {format_link(latest_report)}\n")

def batch_process():
    input_dir = inquirer.text(message=f"Enter the input directory (default: {INPUT_DIR}):", default=INPUT_DIR).execute()
    output_dir = inquirer.text(message=f"Enter the output directory (default: {OUTPUT_DIR}):", default=OUTPUT_DIR).execute()

    # Check if the input directory is empty or contains no XDP files
    if not os.path.exists(input_dir) or not any(file.endswith(".xdp") for file in os.listdir(input_dir)):
        print(f"\n⚠ Warning: The input directory '{input_dir}' is empty or contains no XDP files.")
        print("Ensure there are valid XDP files before running batch processing.\n")
        return

    print("\n🔄 Running batch processing...\n")
    python_cmd = "python3" if os.name != "nt" else "python"
    subprocess.run([python_cmd, "xml_converter.py", "--input-dir", f'"{input_dir}"', "--output-dir", f'"{output_dir}"'])

    report_files = get_all_reports()
    output_files = get_all_outputs()

    print("\n✅ Batch processing complete!")

    if output_files:
        print("\n📂 Generated Output Files:")
        for file in output_files:
            print(f"   - {format_link(file)}")

    if report_files:
        print("\n📊 Generated Reports:")
        for file in report_files:
            print(f"   - {format_link(file)}")

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
