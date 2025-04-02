import unittest
import os
import json
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orbeon_converter_class import OrbeonParser

class TestOrbeonParser(unittest.TestCase):
    def setUp(self):
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Move up one level to project root
        project_root = os.path.dirname(current_dir)
        
        # Set up test file paths
        self.test_xml_file = os.path.join(project_root, "test_data", "test_orbeon_form.xml")
        self.test_mapping_file = os.path.join(project_root, "test_data", "test_orbeon_mapping.json")
        
        # Create test directories if they don't exist
        os.makedirs(os.path.join(project_root, "test_data"), exist_ok=True)
        
        # Create a simple test XML file
        self.create_test_xml_file()
        
        # Create a simple test mapping file
        self.create_test_mapping_file()

    def create_test_xml_file(self):
        """Create a simple test Orbeon XML file"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <xh:html xmlns:xh="http://www.w3.org/1999/xhtml" xmlns:xf="http://www.w3.org/2002/xforms" xmlns:fr="http://orbeon.org/oxf/xml/form-runner">
            <xh:head>
                <xf:model id="fr-form-model">
                    <xf:instance id="fr-form-instance">
                        <form>
                            <section-1>
                                <grid-1>
                                    <control-1>Test Control</control-1>
                                    <control-2>Another Control</control-2>
                                </grid-1>
                            </section-1>
                        </form>
                    </xf:instance>
                    <xf:instance id="fr-form-resources">
                        <resources>
                            <resource xml:lang="en">
                                <control-1>
                                    <label>Control 1 Label</label>
                                    <hint>Control 1 Hint</hint>
                                </control-1>
                                <control-2>
                                    <label>Control 2 Label</label>
                                    <hint>Control 2 Hint</hint>
                                </control-2>
                            </resource>
                        </resources>
                    </xf:instance>
                    <xf:bind id="fr-form-binds" ref="instance('fr-form-instance')">
                        <xf:bind id="control-1-bind" name="control-1" ref="control-1"/>
                        <xf:bind id="control-2-bind" name="control-2" ref="control-2"/>
                    </xf:bind>
                </xf:model>
            </xh:head>
            <xh:body>
                <fr:view>
                    <fr:body>
                        <fr:section id="section-1-control" bind="section-1-bind">
                            <fr:grid id="grid-1-control" bind="grid-1-bind">
                                <fr:c>
                                    <fr:label>Control 1</fr:label>
                                    <fr:widget id="control-1-control" bind="control-1-bind">
                                        <xf:input>
                                            <xf:label>Control 1 Label</xf:label>
                                        </xf:input>
                                    </fr:widget>
                                </fr:c>
                                <fr:c>
                                    <fr:label>Control 2</fr:label>
                                    <fr:widget id="control-2-control" bind="control-2-bind">
                                        <xf:input>
                                            <xf:label>Control 2 Label</xf:label>
                                        </xf:input>
                                    </fr:widget>
                                </fr:c>
                            </fr:grid>
                        </fr:section>
                    </fr:body>
                </fr:view>
            </xh:body>
        </xh:html>
        """
        with open(self.test_xml_file, 'w') as f:
            f.write(xml_content)

    def create_test_mapping_file(self):
        """Create a simple test mapping file for Orbeon"""
        mapping_content = {
            "constants": {
                "ministry_id": "TEST002"
            },
            "mappings": [
                {
                    "xmlPath": "control-1",
                    "fieldType": "text-input",
                    "required": True
                },
                {
                    "xmlPath": "control-2",
                    "fieldType": "text-input",
                    "required": False
                }
            ]
        }
        with open(self.test_mapping_file, 'w') as f:
            json.dump(mapping_content, f, indent=4)

    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.xml_filename, self.test_xml_file)
        self.assertEqual(parser.mapping_file, self.test_mapping_file)

    def test_load_mapping_file(self):
        """Test loading mapping file"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        mapping = parser.load_mapping_file()
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping["constants"]["ministry_id"], "TEST002")
        self.assertEqual(len(mapping["mappings"]), 2)

    def test_extract_binds(self):
        """Test bind extraction"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        self.assertIsNotNone(parser.binds_map)
        self.assertIn("control-1", parser.binds_map)
        self.assertIn("control-2", parser.binds_map)

    def test_create_output_structure(self):
        """Test output structure creation"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        output = parser.create_output_structure()
        self.assertIsNotNone(output)
        self.assertEqual(output["ministry_id"], "TEST002")
        self.assertIn("form_id", output)
        self.assertEqual(output["form_id"], "test_orbeon_form")
        self.assertIn("lastModified", output)
        self.assertIn("dataSources", output)
        self.assertEqual(output["dataSources"], [])

    def test_parse_method(self):
        """Test main parse method"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        result = parser.parse()
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        self.assertIn("items", result["data"])

    def test_process_section(self):
        """Test section processing"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        sections = parser.form_data.findall(".//section-1", parser.namespaces)
        for section in sections:
            parser.process_section(section)
            # Check that items were added to all_items
            self.assertGreater(len(parser.all_items), 0)

    def test_process_field(self):
        """Test field processing"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        fields = parser.form_data.findall(".//control-1", parser.namespaces)
        for field in fields:
            field_obj = parser.process_field(field)
            self.assertIsNotNone(field_obj)
            self.assertIn("type", field_obj)
            self.assertIn("id", field_obj)

    def test_determine_field_type(self):
        """Test field type determination"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        field_name = "control-1"
        field_value = "Test Value"
        field_attributes = {}
        mapping = parser.find_mapping_for_path(field_name)
        
        field_type = parser.determine_field_type(field_name, field_value, field_attributes, mapping)
        self.assertEqual(field_type, "text-input")

    def test_create_field_object(self):
        """Test field object creation"""
        parser = OrbeonParser(self.test_xml_file, self.test_mapping_file)
        field_type = "text-input"
        field_name = "test_field"
        field_value = "Test Value"
        field_attributes = {}
        mapping = parser.find_mapping_for_path(field_name)
        
        field_obj = parser.create_field_object(field_type, field_name, field_value, field_attributes, mapping)
        self.assertIsNotNone(field_obj)
        self.assertEqual(field_obj["type"], "text-input")
        self.assertIn("id", field_obj)
        self.assertIn("label", field_obj)

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