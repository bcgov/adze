import unittest
import os
import json
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.xml_converter_class import XDPParser

class TestXDPParser(unittest.TestCase):
    def setUp(self):
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Move up one level to project root
        project_root = os.path.dirname(current_dir)
        
        # Set up test file paths
        self.test_xml_file = os.path.join(project_root, "test_data", "test_form.xml")
        self.test_mapping_file = os.path.join(project_root, "test_data", "test_mapping.json")
        
        # Create test directories if they don't exist
        os.makedirs(os.path.join(project_root, "test_data"), exist_ok=True)
        
        # Create a simple test XML file
        self.create_test_xml_file()
        
        # Create a simple test mapping file
        self.create_test_mapping_file()

    def create_test_xml_file(self):
        """Create a simple test XML file"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">
            <template xmlns="http://www.xfa.org/schema/xfa-template/3.0/">
                <subform name="form1">
                    <field name="test_field">
                        <ui>
                            <textEdit/>
                        </ui>
                        <value>
                            <text>Test Value</text>
                        </value>
                    </field>
                    <draw name="test_draw">
                        <value>
                            <text>Test Draw Text</text>
                        </value>
                    </draw>
                </subform>
            </template>
        </xdp:xdp>
        """
        with open(self.test_xml_file, 'w') as f:
            f.write(xml_content)

    def create_test_mapping_file(self):
        """Create a simple test mapping file"""
        mapping_content = {
            "constants": {
                "ministry_id": "TEST001"
            },
            "mappings": [
                {
                    "xmlPath": "test_field",
                    "fieldType": "text-input",
                    "required": True
                }
            ]
        }
        with open(self.test_mapping_file, 'w') as f:
            json.dump(mapping_content, f, indent=4)

    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.xml_filename, self.test_xml_file)
        self.assertEqual(parser.mapping_file, self.test_mapping_file)

    def test_load_mapping_file(self):
        """Test loading mapping file"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        mapping = parser.load_mapping_file()
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping["constants"]["ministry_id"], "TEST001")
        self.assertEqual(len(mapping["mappings"]), 1)

    def test_extract_namespaces(self):
        """Test namespace extraction"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        namespaces = parser.extract_namespaces()
        self.assertIsNotNone(namespaces)
        self.assertIn('template', namespaces)
        self.assertIn('xdp', namespaces)

    def test_create_output_structure(self):
        """Test output structure creation"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        output = parser.create_output_structure()
        self.assertIsNotNone(output)
        self.assertEqual(output["ministry_id"], "TEST001")
        self.assertIn("data", output)

    def test_parse_method(self):
        """Test main parse method"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        result = parser.parse()
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        self.assertIn("items", result["data"])

    def test_process_field(self):
        """Test field processing"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        fields = parser.root_subform.findall(".//template:field", parser.namespaces)
        for field in fields:
            field_obj = parser.process_field(field)
            self.assertIsNotNone(field_obj)
            self.assertIn("type", field_obj)
            self.assertIn("id", field_obj)

    def test_process_draw(self):
        """Test draw element processing"""
        parser = XDPParser(self.test_xml_file, self.test_mapping_file)
        draws = parser.root_subform.findall(".//template:draw", parser.namespaces)
        for draw in draws:
            draw_obj = parser.process_draw(draw)
            self.assertIsNotNone(draw_obj)
            self.assertIn("type", draw_obj)
            self.assertIn("id", draw_obj)

    def tearDown(self):
        """Clean up test files"""
        try:
            os.remove(self.test_xml_file)
            os.remove(self.test_mapping_file)
            os.rmdir(os.path.dirname(self.test_xml_file))
        except:
            pass

if __name__ == '__main__':
    unittest.main() 