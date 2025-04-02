# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os
import time
import json
from typing import Any, Optional, Dict, List
from xml_converter_class import XDPParser
from filename_generator import generate_filename

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Dynamically resolve project root and default mapping file path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_MAPPING_FILE = os.path.join(PROJECT_ROOT, "xml_mapping.json")

class XDPConverter:
    """Class for converting XDP files to JSON format"""
    
    def __init__(self, mapping_file=None):
        """
        Initialize the XDP converter
        
        Args:
            mapping_file: Optional path to the XML mapping file
        """
        self.mapping_file = mapping_file or DEFAULT_MAPPING_FILE
        
        if not os.path.exists(self.mapping_file):
            logger.error(f"Mapping file not found: {self.mapping_file}")
            raise FileNotFoundError(f"Mapping file not found: {self.mapping_file}")
    
    def parse_xdp_to_json(self, file_path):
        """
        Convert XDP file to JSON
        
        Args:
            file_path: Path to the XDP file
            
        Returns:
            JSON data as a dictionary
        """
        try:
            parser = XDPParser(file_path, self.mapping_file)
            return parser.parse()
        except Exception as e:
            logger.error(f"Error processing XDP: {e}")
            return None
    
    def process_file(self, xdp_file: str, output_file: Optional[str] = None) -> bool:
        """
        Process a single XDP file and output JSON.
        
        Args:
            xdp_file: Path to the XDP file.
            output_file: Optional path to the output JSON file. If None, uses generate_filename.
            
        Returns:
            True if conversion was successful, False otherwise
        """
        if not os.path.exists(xdp_file):
            logger.error(f"XDP file not found: {xdp_file}")
            return False
        
        try:
            logger.info(f"Processing file: {xdp_file}")
            # Convert the XDP to JSON
            json_data = self.parse_xdp_to_json(xdp_file)

            if not json_data:
                logger.warning(f"Conversion failed: {xdp_file} (Empty JSON)")
                return False
            
            # Generate unique output filename if not provided
            if output_file is None:
                output_file = generate_filename(xdp_file, "output")
            
            # Write the JSON output to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Successfully converted {xdp_file} to {output_file}")
            return True 
        except Exception as e:
            logger.error(f"Failed to process {xdp_file}: {e}")
            return False
    
    def process_directory(self, input_dir: str, output_dir: str) -> int:
        """
        Process all XDP files in a directory.

        Args:
            input_dir: Directory containing XDP files.
            output_dir: Directory for output JSON files.
            
        Returns:
            Number of files processed successfully
        """
        if not os.path.isdir(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            return 0

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        files_processed = 0
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.xdp'):
                input_file = os.path.join(input_dir, filename)
                # Use generate_filename for each file in the directory
                output_file = generate_filename(input_file, "output")
                
                if self.process_file(input_file, output_file):
                    files_processed += 1

        logger.info(f"Processed {files_processed} XDP files")
        return files_processed
    
    def watch_directory(self, input_dir: str, output_dir: str):
        """
        Watches for new XDP files and triggers process_file() when they appear.
        
        Args:
            input_dir: Directory to watch for XDP files
            output_dir: Directory for output JSON files
        """
        processed_files = {}  # Track filename + last modified timestamp
        input_dir = os.path.normpath(input_dir)
        output_dir = os.path.normpath(output_dir)
        
        logger.info(f"Watching directory: {input_dir}")

        try:
            while True:
                for filename in os.listdir(input_dir):
                    if filename.endswith(".xdp"):
                        file_path = os.path.normpath(os.path.join(input_dir, filename))
                        last_modified = os.path.getmtime(file_path)

                        if filename not in processed_files or processed_files[filename] != last_modified:
                            logger.info(f"New or modified file detected: {file_path}")

                            # Use generate_filename for watched files
                            output_file = generate_filename(file_path, "output")

                            if self.process_file(file_path, output_file):
                                processed_files[filename] = last_modified

                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Watch mode stopped by user.")
        except Exception as e:
            logger.error(f"Error in watch mode: {e}")

# For backward compatibility, keep the original functions that use the new class
def parse_xdp_to_json(file_path, mapping_file=None):
    """Main function to convert XDP to JSON"""
    converter = XDPConverter(mapping_file)
    return converter.parse_xdp_to_json(file_path)

def process_file(xdp_file: str, output_file: Optional[str] = None, mapping_file: Optional[str] = None) -> bool:
    """Process a single XDP file and output JSON."""
    converter = XDPConverter(mapping_file)
    return converter.process_file(xdp_file, output_file)

def process_directory(input_dir: str, output_dir: str, mapping_file: Optional[str] = None) -> None:
    """Process all XDP files in a directory."""
    converter = XDPConverter(mapping_file)
    converter.process_directory(input_dir, output_dir)

def watch_directory(input_dir: str, output_dir: str, mapping_file: Optional[str] = None):
    """Watches for new XDP files and triggers process_file() when they appear."""
    converter = XDPConverter(mapping_file)
    converter.watch_directory(input_dir, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert XDP to JSON.')
    parser.add_argument('-f', type=str, help='Path to the XDP file')
    parser.add_argument('-m', type=str, help='Path to the XML mapping file')
    parser.add_argument('--input-dir', '-i', help='Directory containing XDP files to convert')
    parser.add_argument('--output-dir', '-o', help='Directory for output JSON files')
    parser.add_argument('--output', help='Output file for single file conversion')
    parser.add_argument("-w", "--watch", action="store_true", help="Watch directory for new XDP files")
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()

    # Set `mapping_file` to default if `-m` is not provided
    mapping_file = args.m if args.m else DEFAULT_MAPPING_FILE

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate arguments
    if not os.path.exists(mapping_file):
        logger.error(f"Mapping file not found: {mapping_file}")
        sys.exit(1)
    
    if not args.f and not args.input_dir:
        logger.error("Either --file or --input-dir must be specified")
        parser.print_help()
        sys.exit(1)
    
    if args.input_dir and not args.output_dir:
        logger.error("Output directory is required when processing a directory")
        sys.exit(1)

    result = None         

    file_path = args.f
    output_file = args.output
    mapping_file = args.m if args.m else DEFAULT_MAPPING_FILE

    # Create converter instance
    converter = XDPConverter(mapping_file)

    if args.input_dir:
        converter.process_directory(args.input_dir, args.output_dir)
    else:
        result = converter.process_file(file_path, output_file)
        print('result', result)
        logger.info("XML conversion " + ("successful" if result else "failed"))

    if args.watch and args.input_dir:
        logger.info(f"Watch mode enabled. Monitoring directory: {args.input_dir}")
        converter.watch_directory(args.input_dir, args.output_dir)


