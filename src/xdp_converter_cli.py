#!/usr/bin/env python3
from InquirerPy import inquirer
import os
import time
import subprocess
import argparse
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.filename_generator import REPORT_DIR, INPUT_DIR, OUTPUT_DIR, generate_filename
from src.orbeon_converter_class import OrbeonParser
from src.xml_converter import XDPConverter
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    term = os.environ.get('TERM_PROGRAM', '')
    
    if term in ['iTerm.app', 'vscode'] or 'VSCODE' in os.environ:
        return f"\033]8;;file://{abs_path}\033\\{abs_path}\033]8;;\033\\"
    elif platform.system() == 'Darwin' and term == 'Apple_Terminal':
        return f"{abs_path}"
    else:
        return f"{abs_path}"

def validate_input_file(input_path):
    """Validate that the input file exists and has a valid extension"""
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return False
    
    _, ext = os.path.splitext(input_path)
    if ext.lower() not in ['.xml', '.xdp']:
        logger.error(f"Input file must be an XML or XDP file: {input_path}")
        return False
    
    return True

def validate_mapping_file(mapping_path):
    """Validate that the mapping file exists and is a JSON file"""
    if not os.path.exists(mapping_path):
        logger.error(f"Mapping file not found: {mapping_path}")
        return False
    
    _, ext = os.path.splitext(mapping_path)
    if ext.lower() != '.json':
        logger.error(f"Mapping file must be a JSON file: {mapping_path}")
        return False
    
    return True

def convert_xml_to_json(input_path, mapping_path, output_path=None):
    """Convert Oberon XML to JSON"""
    try:
        # Initialize parser
        logger.info(f"Initializing parser for {input_path}")
        parser = OrbeonParser(input_path, mapping_path)
        
        # Parse the XML file
        logger.info("Parsing XML file...")
        output_json = parser.parse()
        
        if output_json is None:
            logger.error("Failed to parse XML file")
            return False
        
        # Generate output path if not provided
        if output_path is None:
            output_path = generate_filename(input_path, "output")
        
        # Write output to file
        logger.info(f"Writing output to {output_path}")
        with open(output_path, 'w') as f:
            json.dump(output_json, f, indent=4)
        
        logger.info(f"Conversion completed successfully! Output saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting XML to JSON: {e}")
        return False

def convert_xdp_to_json(input_path, mapping_path, output_path=None):
    """Convert XDP to JSON"""
    try:
        # Initialize converter
        logger.info(f"Initializing converter for {input_path}")
        converter = XDPConverter(mapping_path)
        
        # Generate output path if not provided
        if output_path is None:
            output_path = generate_filename(input_path, "output")
        
        # Process the XDP file
        logger.info("Processing XDP file...")
        success = converter.process_file(input_path, output_path)
        
        if not success:
            logger.error("Failed to process XDP file")
            return False
        
        logger.info(f"Conversion completed successfully! Output saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting XDP to JSON: {e}")
        return False

def run_conversion():
    """Interactive conversion of a single file"""
    file_path = inquirer.filepath(message="Select a file to convert:").execute()
    output_dir = inquirer.text(
        message=f"Enter the output directory [Default: {OUTPUT_DIR}]:",
        default=OUTPUT_DIR
    ).execute()
    
    print("\n🛠 Converting file to JSON...\n")
    
    # Determine file type and run appropriate conversion
    _, ext = os.path.splitext(file_path)
    if ext.lower() == '.xml':
        # Use Oberon converter for XML files
        success = convert_xml_to_json(file_path, None, None)
    else:
        # Use XDP converter for XDP files
        success = convert_xdp_to_json(file_path, None, None)

    time.sleep(1)  

    # Check if conversion failed
    if not success:
        print("\n❌ Conversion failed! Please check the logs for details.\n")
        return
    
    latest_report = get_latest_report()
    latest_output = get_latest_output()

    if latest_output:
        print(f"\n✅ Conversion complete! Output saved to: {format_link(latest_output)}")

    if latest_report:
        print(f"📊 Report generated: {format_link(latest_report)}\n")

def batch_process():
    """Batch process multiple files while ensuring paths are correctly formatted."""
    input_dir = inquirer.text(message=f"Enter the input directory (default: {INPUT_DIR}):", default=INPUT_DIR).execute()
    output_dir = inquirer.text(message=f"Enter the output directory (default: {OUTPUT_DIR}):", default=OUTPUT_DIR).execute()

    # Convert paths to absolute & normalized versions
    input_dir = os.path.abspath(os.path.normpath(input_dir))
    output_dir = os.path.abspath(os.path.normpath(output_dir))

    print(f"\n🔍 Checking directories...\n  Input: {input_dir}\n  Output: {output_dir}")

    # Ensure input directory exists before running batch processing
    if not os.path.isdir(input_dir):
        print(f"\n❌ Error: The input directory '{input_dir}' does not exist or is not a valid directory.")
        print("Make sure the path is correct and contains XML or XDP files.\n")
        return

    if not any(file.lower().endswith((".xdp", ".xml")) for file in os.listdir(input_dir)):
        print(f"\n⚠ Warning: The input directory '{input_dir}' is empty or contains no XML or XDP files.")
        print("Ensure there are valid files before running batch processing.\n")
        return

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Capture existing files before processing
    existing_outputs = set(os.listdir(output_dir))
    existing_reports = set(os.listdir(REPORT_DIR))

    print("\n🔄 Running batch processing...\n")

    # Process XML files
    xml_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.xml')]
    for xml_file in xml_files:
        input_path = os.path.join(input_dir, xml_file)
        convert_xml_to_json(input_path, None, None)

    # Process XDP files
    converter = XDPConverter()
    files_processed = converter.process_directory(input_dir, output_dir)
    
    if files_processed == 0:
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

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Convert XML/XDP form files to JSON')
    parser.add_argument('-i', '--input', help='Path to input file (XML or XDP)', required=False)
    parser.add_argument('-m', '--mapping', help='Path to XML field mapping file (defaults to xml_mapping.json in project root)', required=False)
    parser.add_argument('-o', '--output', help='Path to output JSON file (defaults to auto-generated filename in the output directory)', required=False)
    parser.add_argument('-v', '--verbose', help='Enable verbose output', action='store_true')
    parser.add_argument('--input-dir', help='Directory containing input files for batch processing', required=False)
    parser.add_argument('--output-dir', help='Directory for output files during batch processing', required=False)
    return parser.parse_args()

def main():
    """Main entry point for the CLI tool"""
    # Parse arguments
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # If no arguments provided, run interactive mode
    if not any([args.input, args.input_dir]):
        while True:
            choice = inquirer.select(
                message="📌 Select an action:",
                choices=[
                    "🔄 Convert a Single File",
                    "📂 Batch Process Multiple Files",
                    "📊 View Reports",
                    "❌ Exit"
                ]
            ).execute()

            if choice == "🔄 Convert a Single File":
                run_conversion()
            elif choice == "📂 Batch Process Multiple Files":
                batch_process()
            elif choice == "📊 View Reports":
                view_reports()
            elif choice == "❌ Exit":
                print("\n👋 Exiting CLI. Goodbye!\n")
                break
        return
    
    # Command line mode
    if args.input:
        # Single file conversion
        input_path = os.path.abspath(args.input)
        if not validate_input_file(input_path):
            sys.exit(1)
        
        # Validate mapping file if provided
        mapping_path = args.mapping
        if mapping_path:
            mapping_path = os.path.abspath(mapping_path)
            if not validate_mapping_file(mapping_path):
                sys.exit(1)
        
        # Get output path if provided
        output_path = args.output
        if output_path:
            output_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Determine file type and run appropriate conversion
        _, ext = os.path.splitext(input_path)
        if ext.lower() == '.xml':
            success = convert_xml_to_json(input_path, mapping_path, output_path)
        else:
            success = convert_xdp_to_json(input_path, mapping_path, output_path)
        
        sys.exit(0 if success else 1)
    
    elif args.input_dir:
        # Batch processing
        input_dir = os.path.abspath(args.input_dir)
        output_dir = os.path.abspath(args.output_dir) if args.output_dir else OUTPUT_DIR
        
        if not os.path.isdir(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            sys.exit(1)
        
        # Process XML files
        xml_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.xml')]
        for xml_file in xml_files:
            input_path = os.path.join(input_dir, xml_file)
            convert_xml_to_json(input_path, None, None)
        
        # Process XDP files
        converter = XDPConverter()
        files_processed = converter.process_directory(input_dir, output_dir)
        
        sys.exit(0 if files_processed > 0 else 1)

if __name__ == "__main__":
    main()
