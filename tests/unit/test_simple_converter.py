import unittest
from unittest.mock import patch, mock_open, MagicMock
from simple_converter import *
import json
import xml.etree.ElementTree as ET

class TestSimpleConverter(unittest.TestCase):

    def setUp(self):
        self.mock_mapping = {
            "root_config": {"version": 8, "ministry_id": 2, "deployed_to": None, "dataSources": []},
            "form_id": {"xpath": ".//template:draw[@name=\"formnumber\"]", "text_xpath": ".//template:value/template:text"},
            "form_title": {"xpath": ".//template:draw[@name=\"FormTitle\"]", "text_xpath": ".//template:value/template:text"},
            "page_area": {"xpath": ".//template:pageArea[@id=\"Page1\"]"},
            "special_elements": []
        }

    def test_get_id(self):
        """Test that get_id increments and returns a string"""
        global_id = 0  # Reset global ID for test consistency
        self.assertEqual(get_id(), "1")
        self.assertEqual(get_id(), "2")

    def test_extract_namespaces(self):
        """Test extraction of XML namespaces"""
        xml_content = '''<root xmlns:xdp="http://ns.adobe.com/xdp/"
                             xmlns:template="http://www.xfa.org/schema/xfa-template/3.0/">
                            <child />
                         </root>'''
        root = ET.fromstring(xml_content)
        namespaces = extract_namespaces(root)
        self.assertEqual(namespaces, {
            "xdp": "http://ns.adobe.com/xdp/",
            "template": "http://www.xfa.org/schema/xfa-template/3.0/"
        })

    @patch("os.path.exists", return_value=True)  # Mock os.path.exists to always return True
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({"key": "value"}))
    def test_load_mapping_file_success(self, mock_file, mock_exists):
        """Test that load_mapping_file correctly loads a JSON file"""
        mapping = load_mapping_file("dummy.json")
        self.assertEqual(mapping, {"key": "value"})
        mock_file.assert_called_once_with("dummy.json", "r")

    @patch("os.path.exists", return_value=False)  # Mock os.path.exists to return False
    def test_load_mapping_file_file_not_found(self, mock_exists):
        """Test that load_mapping_file raises FileNotFoundError if the file is missing"""
        with self.assertRaises(FileNotFoundError):
            load_mapping_file("nonexistent.json")

    @patch("os.path.exists", return_value=True)  # Mock os.path.exists to always return True
    @patch("builtins.open", new_callable=mock_open, read_data="{invalid_json}")  # Invalid JSON format
    def test_load_mapping_file_invalid_json(self, mock_file, mock_exists):
        """Test that load_mapping_file raises JSONDecodeError for invalid JSON"""
        with self.assertRaises(json.JSONDecodeError):
            load_mapping_file("dummy.json")

    def test_get_root_attributes(self):
        """Test UUID and timestamp extraction"""
        xml_content = '''<xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/"
                                  uuid="123e4567-e89b-12d3-a456-426614174000"
                                  timeStamp="2025-01-01T00:00:00Z" />'''
        root = ET.fromstring(xml_content)
        namespaces = {"xdp": "http://ns.adobe.com/xdp/"}
        uuid, timestamp = get_root_attributes(root, namespaces)
        self.assertEqual(uuid, "123e4567-e89b-12d3-a456-426614174000")
        self.assertEqual(timestamp, "2025-01-01T00:00:00Z")

    def test_get_form_id(self):
        """Test extracting form ID with regex transformation"""
        xml_content = '''<root xmlns:template="http://www.xfa.org/schema/xfa-template/3.0/">
                            <template:draw name="formnumber">
                                <template:value>
                                    <template:text>HR1234</template:text>
                                </template:value>
                            </template:draw>
                         </root>'''
        root = ET.fromstring(xml_content)
        namespaces = {"template": "http://www.xfa.org/schema/xfa-template/3.0/"}
        mapping = {"xpath": ".//template:draw[@name=\"formnumber\"]",
                   "text_xpath": ".//template:value/template:text",
                   "transform": "regex",
                   "pattern": "([A-Z]+\\d+)"}

        form_id = get_form_id(root, namespaces, mapping)
        self.assertEqual(form_id, "HR1234")

    def test_get_form_title(self):
        """Test extracting form title"""
        xml_content = '''<root xmlns:template="http://www.xfa.org/schema/xfa-template/3.0/">
                            <template:draw name="FormTitle">
                                <template:value>
                                    <template:text>Application Form</template:text>
                                </template:value>
                            </template:draw>
                         </root>'''
        root = ET.fromstring(xml_content)
        namespaces = {"template": "http://www.xfa.org/schema/xfa-template/3.0/"}
        mapping = {"xpath": ".//template:draw[@name=\"FormTitle\"]", "text_xpath": ".//template:value/template:text"}

        form_title = get_form_title(root, namespaces, mapping)
        self.assertEqual(form_title, "Application Form")