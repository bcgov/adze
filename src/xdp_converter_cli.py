#!/usr/bin/env python3
from InquirerPy import inquirer
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt
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
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_latest_report():
    """Fetch the most recent report file from REPORT_DIR."""
    report_files = sorted(
        Path(REPORT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True
    )
    return str(report_files[0]) if report_files else None


def get_latest_output():
    """Fetch the most recent JSON output file from OUTPUT_DIR."""
    output_files = sorted(
        Path(OUTPUT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True
    )
    return str(output_files[0]) if output_files else None


def get_all_reports():
    """Fetch all report files sorted by most recent."""
    return [
        str(file)
        for file in sorted(
            Path(REPORT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True
        )
    ]


def get_all_outputs():
    """Fetch all JSON output files sorted by most recent."""
    return [
        str(file)
        for file in sorted(
            Path(OUTPUT_DIR).glob("*.json"), key=os.path.getmtime, reverse=True
        )
    ]


def format_link(file_path):
    """Generate clickable file links that work across more terminals."""
    abs_path = Path(file_path).resolve()
    term = os.environ.get("TERM_PROGRAM", "")

    if term in ["iTerm.app", "vscode"] or "VSCODE" in os.environ:
        return f"\033]8;;file://{abs_path}\033\\{abs_path}\033]8;;\033\\"
    elif platform.system() == "Darwin" and term == "Apple_Terminal":
        return f"{abs_path}"
    else:
        return f"{abs_path}"


def validate_input_file(input_path):
    """Validate that the input file exists and has a valid extension"""
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return False

    _, ext = os.path.splitext(input_path)
    if ext.lower() not in [".xml", ".xdp"]:
        logger.error(f"Input file must be an XML or XDP file: {input_path}")
        return False

    return True


def validate_mapping_file(mapping_path):
    """Validate that the mapping file exists and is a JSON file"""
    if not os.path.exists(mapping_path):
        logger.error(f"Mapping file not found: {mapping_path}")
        return False

    _, ext = os.path.splitext(mapping_path)
    if ext.lower() != ".json":
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
        with open(output_path, "w") as f:
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
        default=OUTPUT_DIR,
    ).execute()

    print("\n🛠 Converting file to JSON...\n")

    # Determine file type and run appropriate conversion
    _, ext = os.path.splitext(file_path)
    if ext.lower() == ".xml":
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
        print(
            f"\n✅ Conversion complete! Output saved to: {format_link(latest_output)}"
        )

    if latest_report:
        print(f"📊 Report generated: {format_link(latest_report)}\n")


def batch_process():
    """Batch process multiple files while ensuring paths are correctly formatted."""
    input_dir = inquirer.text(
        message=f"Enter the input directory (default: {INPUT_DIR}):", default=INPUT_DIR
    ).execute()
    output_dir = inquirer.text(
        message=f"Enter the output directory (default: {OUTPUT_DIR}):",
        default=OUTPUT_DIR,
    ).execute()

    # Convert paths to absolute & normalized versions
    input_dir = os.path.abspath(os.path.normpath(input_dir))
    output_dir = os.path.abspath(os.path.normpath(output_dir))

    print(f"\n🔍 Checking directories...\n  Input: {input_dir}\n  Output: {output_dir}")

    # Ensure input directory exists before running batch processing
    if not os.path.isdir(input_dir):
        print(
            f"\n❌ Error: The input directory '{input_dir}' does not exist or is not a valid directory."
        )
        print("Make sure the path is correct and contains XML or XDP files.\n")
        return

    if not any(
        file.lower().endswith((".xdp", ".xml")) for file in os.listdir(input_dir)
    ):
        print(
            f"\n⚠ Warning: The input directory '{input_dir}' is empty or contains no XML or XDP files."
        )
        print("Ensure there are valid files before running batch processing.\n")
        return

    # Ensure output and report directories exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)  # 🔹 FIX: Ensure report directory exists

    # Capture existing files before processing
    existing_outputs = set(os.listdir(output_dir))
    existing_reports = set(os.listdir(REPORT_DIR))

    print("\n🔄 Running batch processing...\n")

    # Process XML files
    xml_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".xml")]
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
    selected_report = ListPrompt(
        message="📊 Select a report to view:", choices=report_choices
    ).execute()

    report_path = os.path.join(REPORT_DIR, selected_report)
    print(f"\n📊 Viewing report: {format_link(report_path)}")

    with open(report_path, "r") as f:
        print(f.read())


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Convert XML/XDP form files to JSON")
    parser.add_argument(
        "-i", "--input", help="Path to input file (XML or XDP)", required=False
    )
    parser.add_argument(
        "-m",
        "--mapping",
        help="Path to XML field mapping file (defaults to xml_mapping.json in project root)",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output JSON file (defaults to auto-generated filename in the output directory)",
        required=False,
    )
    parser.add_argument(
        "-v", "--verbose", help="Enable verbose output", action="store_true"
    )
    parser.add_argument(
        "--input-dir",
        help="Directory containing input files for batch processing",
        required=False,
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for output files during batch processing",
        required=False,
    )
    return parser.parse_args()


def run_single_klamm_extraction():
    """Run the advanced form extractor with conversion integration"""
    input_file = FilePathPrompt(
        message="Select an XDP or PDF file for Klamm extraction:"
    ).execute()
    output_dir = InputPrompt(
        message=f"Enter the output directory [Default: {OUTPUT_DIR}]",
        default=OUTPUT_DIR,
    ).execute()

    print("\n🛠 Running integrated extraction (Advanced + Conversion)...\n")

    try:
        import subprocess
        from pathlib import Path

        # Step 1: Run advanced form extractor
        print("Step 1: Running advanced form extraction...")
        result1 = subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "advanced_form_extractor.py"),
                "--input-file",
                input_file,
                "--output-dir",
                output_dir,
            ],
            capture_output=True,
            text=True,
        )

        if result1.returncode != 0:
            print(f"\n❌ Advanced extraction failed!\n{result1.stderr}\n")
            return

        # Step 2: Run conversion for JavaScript and dataSources
        print("Step 2: Running conversion extraction...")

        # Determine file type and run appropriate conversion
        _, ext = os.path.splitext(input_file)
        if ext.lower() == ".xml":
            success = convert_xml_to_json(input_file, None, None)
        else:
            success = convert_xdp_to_json(input_file, None, None)

        if not success:
            print(
                "\n⚠️ Conversion step failed, proceeding with advanced extraction only..."
            )

        # Step 3: Move conversion output to working-files and integrate
        if success:
            print("Step 3: Integrating extraction results...")

            # Find the latest conversion output
            latest_output = get_latest_output()
            if latest_output:
                # Move to working-files directory
                working_files_dir = Path(output_dir) / "working-files"
                working_files_dir.mkdir(exist_ok=True)

                conversion_filename = f"{Path(input_file).stem}_conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                conversion_dest = working_files_dir / conversion_filename

                import shutil

                shutil.move(latest_output, conversion_dest)
                print(f"Moved conversion output to: {conversion_dest}")

                # Find the fields file and integrate
                fields_files = list(
                    working_files_dir.glob(f"{Path(input_file).stem}_fields_*.json")
                )
                if fields_files:
                    from helper import create_integrated_template

                    success = create_integrated_template(str(fields_files[0]))
                    if success:
                        print("✅ Integration completed successfully!")
                    else:
                        print("⚠️ Integration failed, but extraction completed")

        print("\n✅ Integrated extraction complete!\n")

    except Exception as e:
        print(f"\n❌ Error running integrated extraction: {e}\n")


def run_batch_klamm_extraction():
    """Run the batch form extractor with conversion integration"""
    input_dir = InputPrompt(
        message=f"Enter the input directory (default: {INPUT_DIR})", default=INPUT_DIR
    ).execute()
    output_dir = InputPrompt(
        message=f"Enter the output directory (default: {OUTPUT_DIR})",
        default=OUTPUT_DIR,
    ).execute()

    print(f"\n🛠 Running integrated batch extraction...\n")

    try:
        import subprocess
        from pathlib import Path
        import shutil

        # Step 1: Run batch form extractor
        print("Step 1: Running batch advanced form extraction...")
        result1 = subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "batch_form_extractor.py"),
                "--input-dir",
                input_dir,
                "--output-dir",
                output_dir,
            ],
            capture_output=True,
            text=True,
        )

        if result1.returncode != 0:
            print(f"\n❌ Batch advanced extraction failed!\n{result1.stderr}\n")
            return

        # Step 2: Run conversion directly (not through batch_process)
        print("Step 2: Running batch conversion...")

        working_files_dir = Path(output_dir) / "working-files"
        working_files_dir.mkdir(exist_ok=True)

        # Create a temporary directory for conversion outputs
        temp_conversion_dir = Path(output_dir) / "temp-conversion"
        temp_conversion_dir.mkdir(exist_ok=True)

        # Process XDP files directly
        input_path = Path(input_dir)
        xdp_files = list(input_path.glob("*.xdp"))

        if xdp_files:
            converter = XDPConverter()
            successful_conversions = 0

            for xdp_file in xdp_files:
                try:
                    # Generate conversion output file
                    conversion_filename = f"{xdp_file.stem}_conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    conversion_output = temp_conversion_dir / conversion_filename

                    # Process the file
                    success = converter.process_file(
                        str(xdp_file), str(conversion_output)
                    )

                    if success and conversion_output.exists():
                        # Move to working-files directory
                        final_dest = working_files_dir / conversion_filename
                        shutil.move(str(conversion_output), str(final_dest))
                        print(f"✅ Converted and moved: {conversion_filename}")
                        successful_conversions += 1
                    else:
                        print(f"❌ Failed to convert: {xdp_file.name}")

                except Exception as e:
                    print(f"❌ Error converting {xdp_file.name}: {e}")

            print(
                f"Conversion completed: {successful_conversions}/{len(xdp_files)} files"
            )

        # Clean up temp directory
        try:
            shutil.rmtree(temp_conversion_dir)
        except Exception as e:
            logger.warning(f"Could not remove temp directory: {e}")

        # Step 3: Integrate all results
        print("Step 3: Integrating all extraction results...")

        if working_files_dir.exists():
            fields_files = list(working_files_dir.glob("*_fields_*.json"))

            from helper import create_integrated_template

            successful_integrations = 0

            for fields_file in fields_files:
                try:
                    success = create_integrated_template(str(fields_file))
                    if success:
                        successful_integrations += 1
                        print(f"✅ Integrated: {fields_file.name}")
                    else:
                        print(f"❌ Failed to integrate: {fields_file.name}")
                except Exception as e:
                    logger.error(f"Error integrating {fields_file}: {e}")
                    print(f"❌ Error integrating {fields_file.name}: {e}")

            print(f"\n✅ Integration Summary:")
            print(f"   Fields files found: {len(fields_files)}")
            print(f"   Successfully integrated: {successful_integrations}")

            # List the final template files
            templates_dir = Path(output_dir) / "templates"
            if templates_dir.exists():
                template_files = list(
                    templates_dir.glob("*-integrated-template-*.json")
                )
                if template_files:
                    print(f"   Template files created:")
                    for template_file in template_files:
                        print(f"     - {template_file.name}")

        print("\n✅ Integrated batch extraction complete!\n")

    except Exception as e:
        print(f"\n❌ Error running integrated batch extraction: {e}\n")
        import traceback

        print(traceback.format_exc())


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
            choice = ListPrompt(
                message="📌 Select an action:",
                choices=[
                    "🔄 Convert a Single File",
                    "📂 Batch Process Multiple Files",
                    "📊 View Reports",
                    "Single Klamm Format Extraction",
                    "Batch Klamm Format Extraction",
                    "❌ Exit",
                ],
            ).execute()

            if choice == "🔄 Convert a Single File":
                run_conversion()
            elif choice == "📂 Batch Process Multiple Files":
                batch_process()
            elif choice == "📊 View Reports":
                view_reports()
            elif choice == "Single Klamm Format Extraction":
                run_single_klamm_extraction()
            elif choice == "Batch Klamm Format Extraction":
                run_batch_klamm_extraction()
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
        if ext.lower() == ".xml":
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
        xml_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".xml")]
        for xml_file in xml_files:
            input_path = os.path.join(input_dir, xml_file)
            convert_xml_to_json(input_path, None, None)

        # Process XDP files
        converter = XDPConverter()
        files_processed = converter.process_directory(input_dir, output_dir)

        sys.exit(0 if files_processed > 0 else 1)


if __name__ == "__main__":
    main()
