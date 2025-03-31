# Oberon XML to JSON Converter Documentation

## Overview
The `OberonParser` class is responsible for converting Oberon XML forms to a standardized JSON format. It handles various field types, validation rules, and form structures specific to Oberon forms.

## Class: OberonParser

### Initialization
```python
parser = OberonParser(xml_filename, mapping_file=None)
```
- `xml_filename`: Path to the Oberon XML file
- `mapping_file`: Optional path to JSON mapping configuration file

### Key Features
- XML parsing with namespace support
- Field type detection and conversion
- Validation rule extraction
- Form structure preservation
- Error reporting

### Namespaces
The parser supports multiple XML namespaces:
- `xh`: XHTML namespace
- `xf`: XForms namespace
- `fr`: Form Runner namespace
- `fb`: Form Builder namespace
- `xxf`: XForms Extensions namespace

### Field Types
Supported field types include:
1. `text-info`: Static text display
2. `text-input`: Single-line text input
3. `text-area`: Multi-line text input
4. `date`: Date picker
5. `checkbox`: Boolean checkbox
6. `radio`: Radio button group
7. `dropdown`: Dropdown selection
8. `email`: Email input
9. `phone`: Phone number input
10. `address`: Address input

### Main Methods

#### parse()
Main entry point for XML conversion:
- Processes form sections
- Creates JSON structure
- Handles validation rules
- Returns complete JSON output

#### determine_field_type(field_name, field_value, field_attributes, mapping)
Determines field type based on:
- Field name patterns
- XML structure
- Mapping configuration
- Field attributes

#### process_field(field_elem)
Processes individual form fields:
- Extracts field properties
- Determines field type
- Creates field JSON structure
- Handles validation rules

#### create_field_object(field_type, field_name, field_value, field_attributes, mapping)
Creates standardized JSON objects for fields:
- Sets field properties
- Applies validation rules
- Handles field-specific attributes
- Applies mapping configurations

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
- Date range validation

### Mapping Configuration
Supports field mapping configuration:
- Field type overrides
- Custom labels
- Validation rules
- Help text
- Required status

## Usage Example
```python
from src.oberon_converter_class import OberonParser

# Initialize parser
parser = OberonParser('form.xml', 'mapping.json')

# Convert XML to JSON
json_output = parser.parse()

# Access converted data
items = json_output['data']['items']
```

## Output Format
The converter produces a standardized JSON structure:
```json
{
    "version": "1.0",
    "ministry_id": "...",
    "id": "...",
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