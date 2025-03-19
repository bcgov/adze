import argparse
import logging
import sys
import os
import time
import json
from typing import Dict, Any, Optional, List
from xml_converter_class import XDPParser
from filename_generator import generate_filename

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_xdp_to_json(file_path, mapping_file='xml_mapping.json'):
    """Main function to convert XDP to JSON"""
    try:
        logger.info(f"📝 Processing file: {file_path}")
        parser = XDPParser(file_path, mapping_file)
        return parser.parse()
    except Exception as e:
        logger.error(f"❌ Error processing XDP: {file_path} - {e}", exc_info=True)
        print(f"Error processing XDP: {e}")

def process_file(xdp_file: str, output_file: Optional[str] = None, mapping_file: Optional[str] = None) -> bool:
        """
        Process a single XDP file and output JSON.
        
        Args:
            xdp_file: Path to the XDP file.
            output_file: Optional path to the output JSON file. If None, uses the same base name.
        """
        if not os.path.exists(xdp_file):
            logger.error(f"❌ XDP file not found: {xdp_file}")
            return False
        
        try:
            logger.info(f"file_path: {xdp_file}")
            # Convert the XDP to JSON
            json_data = parse_xdp_to_json(xdp_file, mapping_file)

            if not json_data:
                logger.warning(f"⚠️ Conversion failed: {xdp_file} (Empty JSON)")
                return False
            
            # Generate unique output filename
            output_file = generate_filename(xdp_file, "output")

            
            # Write the JSON output to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"✅ Successfully converted {xdp_file} to {output_file}")
            return True 
        except Exception as e:
            logger.error(f"❌ Failed to process {xdp_file}: {e}")
            return False
    
def process_directory(input_dir: str, output_dir: str) -> None:
    """
    Process all XDP files in a directory.
    
    Args:
        input_dir: Directory containing XDP files.
        output_dir: Directory for output JSON files.
    """
    if not os.path.isdir(input_dir):
        logger.error(f"❌ Input directory not found: {input_dir}")
        return
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Process all XDP files in the input directory
    files_processed = 0
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.xdp'):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(output_dir, os.path.splitext(filename)[0] + '.json')
            
            process_file(input_file, output_file)
            files_processed += 1
    
    logger.info(f"Processed {files_processed} XDP files")

def watch_directory(input_dir: str, output_dir: str, mapping_file: str = "xml_mapping.json"):
    """Watches for new XDP files and triggers process_file() when they appear."""
    processed_files = {}  # ✅ Track filename + last modified timestamp
    input_dir = os.path.normpath(input_dir)
    output_dir = os.path.normpath(output_dir)
    
    logger.info(f"📂 Watching directory: {input_dir}")

    try:
        while True:
            for filename in os.listdir(input_dir):
                if filename.endswith(".xdp"):
                    file_path = os.path.normpath(os.path.join(input_dir, filename))
                    last_modified = os.path.getmtime(file_path)

                    if filename not in processed_files or processed_files[filename] != last_modified:
                        logger.info(f"🔄 New or modified file detected: {file_path}")

                        output_file = os.path.normpath(os.path.join(output_dir, filename.replace(".xdp", ".json")))

                        # ✅ Process the file and update tracking
                        if process_file(file_path, output_file, mapping_file=mapping_file):
                            processed_files[filename] = last_modified

            time.sleep(5)  # ✅ Keeps watching for new files
    except KeyboardInterrupt:
        logger.info("🛑 Watch mode stopped by user.")
    except Exception as e:
        logger.error(f"❌ Error in watch mode: {e}")

if __name__ == "__main__":
    # file_path = './sample_pdfs/eg medium-complexity-A HR0077.xdp'
    parser = argparse.ArgumentParser(description='Convert XDP to JSON.')
    parser.add_argument('-f', type=str, help='Path to the XDP file')
    parser.add_argument('-m', type=str, default='xml_mapping.json', help='Path to the XML mapping file')
    parser.add_argument('--input-dir', '-i', help='Directory containing XDP files to convert')
    parser.add_argument('--output-dir', '-o', help='Directory for output JSON files')
    parser.add_argument('--output', default="mapping_output.json", help='Output file for single file conversion')
    parser.add_argument("-w", "--watch", action="store_true", help="Watch directory for new XDP files")
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate arguments
    if not args.m:
        logger.error("❌ Mapping file (-m) is required")
        sys.exit(1)
    
    if not args.f and not args.input_dir:
        logger.error("❌ Either --file or --input-dir must be specified")
        parser.print_help()
        sys.exit(1)
    
    if args.input_dir and not args.output_dir:
        logger.error("❌ Output directory is required when processing a directory")
        sys.exit(1)

    result = None         

    file_path = args.f
    output_file = args.output
    mapping_file = args.m
    # file_path = './sample_pdfs/eg medium-complexity-B HR0095.xdp'
    # result = parse_xdp_to_json(file_path, mapping_file)
    if args.input_dir:
        process_directory(args.input_dir, args.output_dir)
    else:
        result = process_file(file_path, output_file, mapping_file)
        print('result', result)
        logger.info("XML conversion " + ("✅ successful" if result else "❌ failed"))

    if args.watch and args.input_dir:
        logger.info(f"🔄 Watch mode enabled. Monitoring directory: {args.input_dir}")
        watch_directory(args.input_dir, mapping_file)        


