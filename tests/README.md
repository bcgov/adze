# XML-JSON Converter Test Suite Documentation

## Overview
This test suite provides comprehensive testing for both the Orbeon and XDP XML parsers. The tests ensure proper functionality of XML parsing, field type determination, field creation, and complete XML to JSON conversion.

## Test Structure

### Setup and Teardown
- `setUp()`: Creates test data directory and generates test XML and mapping files before each test
- `tearDown()`: Cleans up test files after each test

### Test Files
- `test_orbeon.xml`: Sample Orbeon XML file with form fields
- `test_xdp.xml`: Sample XDP XML file with form fields
- `test_mapping.json`: Configuration file for field mappings

## Test Cases

### Parser Initialization Tests
1. `test_orbeon_parser_initialization`
   - Verifies proper initialization of OrbeonParser
   - Checks XML file loading, mapping file loading, and form instance detection

2. `test_xdp_parser_initialization`
   - Verifies proper initialization of XDPParser
   - Checks XML file loading, mapping file loading, and root subform detection

### Field Type Determination Tests
1. `test_orbeon_field_type_determination`
   - Tests correct field type detection for:
     - Text info fields (control-476)
     - Text input fields
     - Date fields

2. `test_xdp_field_type_determination`
   - Tests correct field type detection for:
     - Text input fields
     - Date fields

### Field Creation Tests
1. `test_orbeon_field_creation`
   - Verifies proper creation of:
     - Text info fields with values
     - Text input fields with values

2. `test_xdp_field_creation`
   - Verifies proper creation of:
     - Text input fields with labels
     - Date fields with masks and labels

### Full Conversion Tests
1. `test_orbeon_parser_full_conversion`
   - Tests complete XML to JSON conversion
   - Verifies presence of all required fields
   - Checks field values and types

2. `test_xdp_parser_full_conversion`
   - Tests complete XML to JSON conversion
   - Verifies presence of all required fields
   - Checks field labels and types

### Error Handling Tests
1. `test_invalid_xml_handling`
   - Tests parser behavior with:
     - Non-existent XML files
     - Invalid XML content

2. `test_mapping_file_handling`
   - Tests parser behavior with:
     - Non-existent mapping files
     - Invalid JSON in mapping files

## Running Tests
To run the test suite:
```bash
python -m unittest tests/test_converters.py -v
```

## Test Data
The test suite creates temporary test files in the `tests/test_data` directory. These files are automatically cleaned up after each test run. 