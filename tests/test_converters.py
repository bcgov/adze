import unittest
import os
import json
import xml.etree.ElementTree as ET
from src.orbeon_converter_class import OrbeonParser
from src.xml_converter_class import XDPParser

class TestConverters(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create test data directory if it doesn't exist
        self.test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Set paths for test files
        self.orbeon_xml_path = os.path.join(self.test_data_dir, 'test_orbeon.xml')
        self.xdp_xml_path = os.path.join(self.test_data_dir, 'test_xdp.xml')
        self.mapping_file_path = os.path.join(self.test_data_dir, 'test_mapping.json')
        
        # Create test files
        self.create_test_xml_files()
        self.create_test_mapping_file()

    def tearDown(self):
        """Clean up after each test method."""
        # Remove test files
        if os.path.exists(self.orbeon_xml_path):
            os.remove(self.orbeon_xml_path)
        if os.path.exists(self.xdp_xml_path):
            os.remove(self.xdp_xml_path)
        if os.path.exists(self.mapping_file_path):
            os.remove(self.mapping_file_path)

    def create_test_xml_files(self):
        """Create test XML files for both converters."""
        # Create test Orbeon XML
        orbeon_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <xh:html xmlns:xh="http://www.w3.org/1999/xhtml"
                 xmlns:xf="http://www.w3.org/2002/xforms"
                 xmlns:fr="http://orbeon.org/oxf/xml/form-runner"
                 xmlns:fb="http://orbeon.org/oxf/xml/form-builder"
                 xmlns:xxf="http://orbeon.org/oxf/xml/xforms">
            <xh:head>
                <xh:title>Test Form</xh:title>
            </xh:head>
            <xh:body>
                <xf:model>
                    <xf:instance id="fr-form-instance">
                        <form>
                            <section-a>
                                <grid-1>
                                    <control-476>
                                        <text>Test Text Info</text>
                                    </control-476>
                                    <text-input-field>Sample Text</text-input-field>
                                    <date-field>2024-03-30</date-field>
                                    <dropdown-field>option1</dropdown-field>
                                </grid-1>
                            </section-a>
                        </form>
                    </xf:instance>
                    <xf:bind id="fr-form-binds">
                        <xf:bind id="text-input-field-bind" ref="text-input-field" name="Text Input Field"/>
                        <xf:bind id="date-field-bind" ref="date-field" name="Date Field"/>
                        <xf:bind id="dropdown-field-bind" ref="dropdown-field" name="Dropdown Field"/>
                    </xf:bind>
                </xf:model>
            </xh:body>
        </xh:html>'''
        
        # Create test XDP XML
        xdp_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/"
                 xmlns:template="http://www.xfa.org/schema/xfa-template/3.0/">
            <template:template>
                <template:subform name="root">
                    <template:field name="text_field">
                        <template:caption>
                            <template:value>
                                <template:text>Text Field</template:text>
                            </template:value>
                        </template:caption>
                        <template:ui>
                            <template:textEdit/>
                        </template:ui>
                    </template:field>
                    <template:field name="date_field">
                        <template:caption>
                            <template:value>
                                <template:text>Date Field</template:text>
                            </template:value>
                        </template:caption>
                        <template:ui>
                            <template:dateTimeEdit>
                                <template:format>
                                    <template:picture>yyyy-MM-dd</template:picture>
                                </template:format>
                            </template:dateTimeEdit>
                        </template:ui>
                    </template:field>
                </template:subform>
            </template:template>
        </xdp:xdp>'''
        
        # Write test files
        with open(self.orbeon_xml_path, 'w') as f:
            f.write(orbeon_xml)
        with open(self.xdp_xml_path, 'w') as f:
            f.write(xdp_xml)

    def create_test_mapping_file(self):
        """Create a test mapping file."""
        test_mapping = {
            "constants": {
                "version": "1.0",
                "ministry_id": "TEST001"
            },
            "mappings": [
                {
                    "xmlPath": "text-input-field",
                    "fieldType": "text-input",
                    "label": "Custom Text Input",
                    "required": True
                },
                {
                    "xmlPath": "date-field",
                    "fieldType": "date",
                    "label": "Custom Date Field",
                    "validation": [
                        {
                            "type": "required",
                            "value": True,
                            "errorMessage": "Date is required"
                        }
                    ]
                }
            ]
        }
        
        with open(self.mapping_file_path, 'w') as f:
            json.dump(test_mapping, f)

    def test_orbeon_parser_initialization(self):
        """Test OrbeonParser initialization."""
        parser = OrbeonParser(self.orbeon_xml_path, self.mapping_file_path)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.xml_filename, self.orbeon_xml_path)
        self.assertEqual(parser.mapping_file, self.mapping_file_path)
        self.assertIsNotNone(parser.mapping)
        self.assertIsNotNone(parser.root)
        self.assertIsNotNone(parser.form_instance)

    def test_xdp_parser_initialization(self):
        """Test XDPParser initialization."""
        parser = XDPParser(self.xdp_xml_path, self.mapping_file_path)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.xml_filename, self.xdp_xml_path)
        self.assertEqual(parser.mapping_file, self.mapping_file_path)
        self.assertIsNotNone(parser.mapping)
        self.assertIsNotNone(parser.root)
        self.assertIsNotNone(parser.root_subform)

    def test_orbeon_field_type_determination(self):
        """Test field type determination in OrbeonParser."""
        parser = OrbeonParser(self.orbeon_xml_path, self.mapping_file_path)
        
        # Test text-info type
        text_info_type = parser.determine_field_type("control-476", None, {}, None)
        self.assertEqual(text_info_type, "text-info")
        
        # Test text-input type
        text_input_type = parser.determine_field_type("text-input-field", "value", {}, None)
        self.assertEqual(text_input_type, "text-input")
        
        # Test date type
        date_type = parser.determine_field_type("date-field", "2024-03-30", {}, None)
        self.assertEqual(date_type, "date")

    def test_xdp_field_type_determination(self):
        """Test field type determination in XDPParser."""
        parser = XDPParser(self.xdp_xml_path, self.mapping_file_path)
        
        # Test text input type
        text_field = parser.root_subform.find(".//template:field[@name='text_field']", parser.namespaces)
        text_type = parser.process_field(text_field)["type"]
        self.assertEqual(text_type, "text-input")
        
        # Test date type
        date_field = parser.root_subform.find(".//template:field[@name='date_field']", parser.namespaces)
        date_type = parser.process_field(date_field)["type"]
        self.assertEqual(date_type, "date")

    def test_orbeon_field_creation(self):
        """Test field object creation in OrbeonParser."""
        parser = OrbeonParser(self.orbeon_xml_path, self.mapping_file_path)
        
        # Test text-info field creation
        text_info_field = parser.create_field_object(
            "text-info",
            "control-476",
            "Test Text Info",
            {},
            None
        )
        self.assertEqual(text_info_field["type"], "text-info")
        self.assertEqual(text_info_field["value"], "Test Text Info")
        
        # Test text-input field creation
        text_input_field = parser.create_field_object(
            "text-input",
            "text-input-field",
            "Sample Text",
            {},
            None
        )
        self.assertEqual(text_input_field["type"], "text-input")
        self.assertEqual(text_input_field["value"], "Sample Text")

    def test_xdp_field_creation(self):
        """Test field object creation in XDPParser."""
        parser = XDPParser(self.xdp_xml_path, self.mapping_file_path)
        
        # Test text field creation
        text_field = parser.root_subform.find(".//template:field[@name='text_field']", parser.namespaces)
        text_obj = parser.process_field(text_field)
        self.assertEqual(text_obj["type"], "text-input")
        self.assertEqual(text_obj["label"], "Text Field")
        
        # Test date field creation
        date_field = parser.root_subform.find(".//template:field[@name='date_field']", parser.namespaces)
        date_obj = parser.process_field(date_field)
        self.assertEqual(date_obj["type"], "date")
        self.assertEqual(date_obj["label"], "Date Field")
        self.assertEqual(date_obj["mask"], "yyyy-MM-dd")

    def test_orbeon_parser_full_conversion(self):
        """Test complete Orbeon XML to JSON conversion."""
        parser = OrbeonParser(self.orbeon_xml_path, self.mapping_file_path)
        result = parser.parse()
        
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        self.assertIn("items", result["data"])
        self.assertGreater(len(result["data"]["items"]), 0)
        
        # Verify specific fields
        items = result["data"]["items"]
        text_info = next((item for item in items if item["type"] == "text-info"), None)
        self.assertIsNotNone(text_info)
        self.assertEqual(text_info["value"], "Test Text Info")

    def test_xdp_parser_full_conversion(self):
        """Test complete XDP XML to JSON conversion."""
        parser = XDPParser(self.xdp_xml_path, self.mapping_file_path)
        result = parser.parse()
        
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        self.assertIn("items", result["data"])
        self.assertGreater(len(result["data"]["items"]), 0)
        
        # Verify specific fields
        items = result["data"]["items"]
        text_field = next((item for item in items if item["type"] == "text-input"), None)
        self.assertIsNotNone(text_field)
        self.assertEqual(text_field["label"], "Text Field")

    def test_invalid_xml_handling(self):
        """Test handling of invalid XML files."""
        # Test with non-existent file
        with self.assertRaises(FileNotFoundError):
            OrbeonParser("nonexistent.xml")
        
        # Test with invalid XML content
        invalid_xml_path = os.path.join(self.test_data_dir, 'invalid.xml')
        with open(invalid_xml_path, 'w') as f:
            f.write("<invalid>xml</invalid>")
        
        with self.assertRaises(Exception):
            OrbeonParser(invalid_xml_path)
        
        # Clean up
        if os.path.exists(invalid_xml_path):
            os.remove(invalid_xml_path)

    def test_mapping_file_handling(self):
        """Test handling of mapping file."""
        # Test with non-existent mapping file
        parser = OrbeonParser(self.orbeon_xml_path, "nonexistent.json")
        self.assertIsNone(parser.mapping)
        
        # Test with invalid JSON in mapping file
        invalid_mapping_path = os.path.join(self.test_data_dir, 'invalid_mapping.json')
        with open(invalid_mapping_path, 'w') as f:
            f.write("{invalid json}")
        
        parser = OrbeonParser(self.orbeon_xml_path, invalid_mapping_path)
        self.assertIsNone(parser.mapping)
        
        # Clean up
        if os.path.exists(invalid_mapping_path):
            os.remove(invalid_mapping_path)

if __name__ == '__main__':
    unittest.main() 