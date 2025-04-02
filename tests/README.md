# XML-JSON Converter Test Suite Documentation

## Overview
This test suite provides comprehensive testing for both the Orbeon and XDP XML parsers. The tests ensure proper functionality of XML parsing, field type determination, field creation, and complete XML to JSON conversion.

## Test Structure

### Test Files
- `test_orbeon_converter.py`: Tests for the Orbeon XML parser
- `test_xml_converter.py`: Tests for the XDP XML parser
- `test_data/`: Directory containing test XML and mapping files
- `test_output/`: Directory for test output files

## Test Cases

### Orbeon Parser Tests (`test_orbeon_converter.py`)
1. `test_parser_initialization`
   - Verifies proper initialization of OrbeonParser
   - Checks XML file loading and mapping file loading

2. `test_load_mapping_file`
   - Tests loading and parsing of mapping file
   - Verifies constants and mappings structure

3. `test_extract_binds`
   - Tests extraction of form bindings
   - Verifies bind map creation

4. `test_create_output_structure`
   - Tests creation of initial output JSON structure
   - Verifies required fields and data sources

5. `test_parse_method`
   - Tests complete XML to JSON conversion
   - Verifies data structure and items

6. `test_process_section`
   - Tests section processing
   - Verifies item collection

7. `test_process_field`
   - Tests field processing
   - Verifies field object creation

8. `test_determine_field_type`
   - Tests field type determination logic
   - Verifies mapping-based type assignment

9. `test_create_field_object`
   - Tests field object creation
   - Verifies field properties and structure

### XDP Parser Tests (`test_xml_converter.py`)
1. `test_parser_initialization`
   - Verifies proper initialization of XDPParser
   - Checks XML file loading and mapping file loading

2. `test_load_mapping_file`
   - Tests loading and parsing of mapping file
   - Verifies constants and mappings structure

3. `test_extract_namespaces`
   - Tests XML namespace extraction
   - Verifies namespace mapping

4. `test_create_output_structure`
   - Tests creation of initial output JSON structure
   - Verifies required fields

5. `test_parse_method`
   - Tests complete XML to JSON conversion
   - Verifies data structure and items

6. `test_process_field`
   - Tests field processing
   - Verifies field object creation

7. `test_process_draw`
   - Tests draw element processing
   - Verifies draw object creation

## Running Tests
To run the test suite:
```bash
# Run all tests
python -m unittest discover tests -v

# Run specific test file
python -m unittest tests/test_orbeon_converter.py -v
python -m unittest tests/test_xml_converter.py -v
```

## Test Data
The test suite creates temporary test files in the `tests/test_data` directory. These files are automatically cleaned up after each test run. The test data includes:
- Sample Orbeon XML form
- Sample XDP XML form
- Mapping configuration files 