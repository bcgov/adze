# XDP XML to JSON Converter Documentation

## Overview
The `XDPParser` class converts Adobe XDP (XML Data Package) forms to a standardized JSON format. It handles Adobe-specific form elements, field types, and validation rules while maintaining form structure and functionality.

## Class: XDPParser

### Initialization
```python
parser = XDPParser(xml_filename, mapping_file=None)
```
- `xml_filename`: Path to the XDP XML file
- `mapping_file`: Optional path to JSON mapping configuration file

### Key Features
- Adobe XDP format support
- Dynamic namespace detection
- Field type conversion
- Form structure preservation
- Validation rule extraction

### Namespaces
The parser automatically detects and handles XDP namespaces:
- `xdp`: Adobe XDP namespace
- `template`: XFA Template namespace

### Field Types
Supported field types include:
1. `text-input`: Text input fields (textEdit)
2. `text-area`: Multi-line text input
3. `date`: Date picker (dateTimeEdit)
4. `dropdown`: Choice lists
5. `checkbox`: Check buttons
6. `radio`: Radio button groups
7. `button`: Form buttons
8. `signature`: Signature fields

### Main Methods

#### parse()
Main entry point for XDP conversion:
- Processes master pages
- Processes root elements
- Creates JSON structure
- Returns complete JSON output

#### process_field(field)
Processes individual form fields:
- Extracts field properties
- Determines field type
- Creates field JSON structure
- Handles validation rules
- Processes scripts

#### process_subform(subform)
Handles subform elements:
- Creates group structures
- Processes nested fields
- Handles repeating sections
- Maintains form hierarchy

#### process_draw(draw)
Processes draw elements:
- Extracts text content
- Handles HTML content
- Creates text-info fields
- Applies styling

### Special Features

#### Script Processing
Handles XFA scripts:
- Extracts validation rules
- Converts to JSON format
- Preserves script functionality

#### ExData Handling
Processes rich text content:
- HTML content extraction
- Text formatting preservation
- Style handling

#### Group Management
Supports form grouping:
- Subform processing
- Exclusion groups
- Repeating sections
- Nested structures

### Error Handling
- Comprehensive error catching
- Detailed error reporting
- Graceful failure handling
- Error logging through Report class

### Validation Rules
Supports multiple validation types:
- Required fields
- Pattern matching
- Min/max values
- Custom validation rules
- Script-based validation

### Mapping Configuration
Supports field mapping configuration:
- Field type overrides
- Custom labels
- Validation rules
- Help text
- Data source bindings

## Usage Example
```python
from src.xml_converter_class import XDPParser

# Initialize parser
parser = XDPParser('form.xdp', 'mapping.json')

# Convert XDP to JSON
json_output = parser.parse()

# Access converted data
items = json_output['data']['items']
```

## Output Format
The converter produces a standardized JSON structure:
```json
{
    "version": null,
    "ministry_id": "...",
    "id": null,
    "lastModified": "...",
    "title": "...",
    "form_id": "...",
    "deployed_to": null,
    "dataSources": [],
    "data": {
        "items": [
            {
                "type": "...",
                "id": "...",
                "label": "...",
                // Additional field-specific properties
            }
        ]
    }
}
```

### Field-Specific Properties
Different field types have specific properties:

#### Text Input
```json
{
    "type": "text-input",
    "id": "...",
    "label": "...",
    "inputType": "text",
    "placeholder": "...",
    "mask": "..."
}
```

#### Date Field
```json
{
    "type": "date",
    "id": "...",
    "fieldId": "...",
    "label": "...",
    "mask": "yyyy-MM-dd"
}
```

#### Dropdown
```json
{
    "type": "dropdown",
    "id": "...",
    "label": "...",
    "listItems": [
        {
            "text": "...",
            "value": "..."
        }
    ]
}
``` 