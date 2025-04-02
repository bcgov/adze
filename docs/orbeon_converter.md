# Orbeon XML to JSON Converter Documentation

## Overview
The Orbeon XML to JSON Converter is a Python-based tool designed to convert Orbeon Forms XML files into a standardized JSON format. This tool is particularly useful for modernizing legacy form systems or integrating Orbeon forms with other applications.

## Features
- Converts Orbeon XML forms to JSON
- Supports field type detection and mapping
- Handles form sections and grids
- Generates detailed conversion reports
- Supports custom field mapping configuration

## Installation
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface
```python
from src.orbeon_converter_class import OrbeonParser

# Basic usage
parser = OrbeonParser("input.xml")
result = parser.parse()

# With custom mapping file
parser = OrbeonParser("input.xml", "custom_mapping.json")
result = parser.parse()
```

### CLI Tool
```bash
python src/orbeon_converter_cli.py -i /path/to/input.xml [-m /path/to/mapping.json] [-o /path/to/output.json] [-v]
```

Options:
- `-i, --input`: Path to input Orbeon XML file (required)
- `-m, --mapping`: Path to XML field mapping file (defaults to xml_mapping.json)
- `-o, --output`: Path to output JSON file (defaults to auto-generated filename)
- `-v, --verbose`: Enable verbose output

## Field Mapping
The converter uses a mapping file to determine how to convert XML fields to JSON. The mapping file should be in JSON format:

```json
{
    "constants": {
        "version": "1.0",
        "ministry_id": "YOUR_MINISTRY_ID"
    },
    "mappings": [
        {
            "xmlPath": "field-name",
            "fieldType": "text-input",
            "label": "Custom Label",
            "required": true
        }
    ]
}
```

## Output Format
The converter generates JSON in the following format:

```json
{
    "version": "1.0",
    "ministry_id": "YOUR_MINISTRY_ID",
    "id": "unique-id",
    "lastModified": "2024-03-30T12:00:00+00:00",
    "title": "Form Title",
    "form_id": "FORM_ID",
    "deployed_to": null,
    "dataSources": [],
    "data": {
        "items": [
            {
                "type": "text-input",
                "value": "Field Value",
                "label": "Field Label",
                "required": true
            }
        ]
    }
}
```

## Error Handling
The converter includes comprehensive error handling:
- Invalid XML files
- Missing required fields
- Invalid mapping configurations
- File system errors

## Testing
Run the test suite:
```bash
python -m unittest tests/test_converters.py -v
```

## Contributing
Feel free to submit issues and pull requests! 