#!/usr/bin/env python3
import argparse
import json
import os
import sys
import logging
from datetime import datetime
from oberon_converter_class import OberonParser
from filename_generator import generate_filename

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Convert Oberon XML form files to JSON')
    parser.add_argument('-i', '--input', help='Path to input Oberon XML file', required=True)
    parser.add_argument('-m', '--mapping', help='Path to XML field mapping file (defaults to xml_mapping.json in project root)', required=False)
    parser.add_argument('-o', '--output', help='Path to output JSON file (defaults to auto-generated filename in the output directory)', required=False)
    parser.add_argument('-v', '--verbose', help='Enable verbose output', action='store_true')
    return parser.parse_args()

def validate_input_file(input_path):
    """Validate that the input file exists and is an XML file"""
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return False
    
    _, ext = os.path.splitext(input_path)
    if ext.lower() not in ['.xml']:
        logger.error(f"Input file must be an XML file: {input_path}")
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
        parser = OberonParser(input_path, mapping_path)
        
        # Parse the XML file
        logger.info("Parsing XML file...")
        output_json = parser.parse()
        
        if output_json is None:
            logger.error("Failed to parse XML file")
            return False
        
        # Generate output path if not provided
        if output_path is None or os.path.isdir(output_path):
            output_path = os.path.join(output_path or "output", generate_filename(input_path, "output"))

        
        # Write output to file
        logger.info(f"Writing output to {output_path}")
        with open(output_path, 'w') as f:
            json.dump(output_json, f, indent=4)
        
        logger.info(f"Conversion completed successfully! Output saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting XML to JSON: {e}")
        return False

def main():
    """Main entry point for the CLI tool"""
    # Parse arguments
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
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
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Convert XML to JSON
    success = convert_xml_to_json(input_path, mapping_path, output_path)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
