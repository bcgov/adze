#!/usr/bin/env python3
"""
Test script for OrbeonParser class.
This script demonstrates how to use the OrbeonParser to convert an Orbeon XML file to JSON.

Usage:
    python test_orbeon_converter.py
"""

import os
import json
from src.orbeon_converter_class import OrbeonParser

def main():
    # Define paths
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(project_root, "data", "input")
    output_dir = os.path.join(project_root, "data", "output")
    mapping_file = os.path.join(project_root, "xml_mapping.json")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Example: Convert CF2160.xml
    input_file = os.path.join(input_dir, "CF2160.xml")
    output_file = os.path.join(output_dir, "CF2160_output.json")
    
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        return
    
    print(f"Converting {input_file} to {output_file}...")
    
    try:
        # Initialize parser
        parser = OrbeonParser(input_file, mapping_file)
        
        # Parse the XML file
        output_json = parser.parse()
        
        if output_json is None:
            print("Failed to parse XML file")
            return
        
        # Write output to file
        with open(output_file, 'w') as f:
            json.dump(output_json, f, indent=4)
        
        print(f"Conversion completed successfully! Output saved to {output_file}")
    except Exception as e:
        print(f"Error converting XML to JSON: {e}")

if __name__ == "__main__":
    main() 