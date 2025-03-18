import pytest
import json
import xml.etree.ElementTree as ET
from unittest.mock import patch, mock_open
from xml_converter_class import XDPParser

@pytest.fixture
def sample_mapping():
    return {
        "constants": {
            "version": 8,
            "ministry_id": 2
        }
    }

@pytest.fixture
def sample_xdp(tmp_path):
    """Creates a temporary XDP file for testing."""
    xdp_content = """<?xml version="1.0" encoding="UTF-8"?>
    <xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">
        <template xmlns="http://www.xfa.org/schema/xfa-template/3.0/">
            <subform name="TestForm">
                <field name="TestField">
                    <value>
                        <text>Hello World</text>
                    </value>
                </field>
            </subform>
        </template>
    </xdp:xdp>"""
    
    xdp_file = tmp_path / "test.xdp"
    xdp_file.write_text(xdp_content)
    return str(xdp_file)

@pytest.fixture
def sample_mapping_file(tmp_path, sample_mapping):
    mapping_file = tmp_path / "mapping.json"
    with open(mapping_file, "w") as f:
        json.dump(sample_mapping, f)
    return str(mapping_file)

@pytest.fixture
def sample_mapping_file():
    """Returns a static mapping file path instead of generating a temp file."""
    return "tests/data/mapping.json"

# Test loading a mapping file
def test_load_mapping_file(sample_xdp, sample_mapping_file):
    parser = XDPParser(sample_xdp, sample_mapping_file)
    assert parser.mapping is not None, "Mapping file should be loaded"
    assert "constants" in parser.mapping, "Mapping should contain constants"

# Test extracting namespaces
def test_extract_namespaces(sample_xdp, sample_mapping_file):
    parser = XDPParser(sample_xdp, sample_mapping_file)
    namespaces = parser.extract_namespaces()
    assert "xdp" in namespaces, "Should extract xdp namespace"
    assert "template" in namespaces, "Should extract template namespace"

# Test JSON structure creation
def test_create_output_structure(sample_xdp, sample_mapping_file):
    parser = XDPParser(sample_xdp, sample_mapping_file)
    output = parser.create_output_structure()
    assert isinstance(output, dict), "Output should be a dictionary"
    assert "version" in output, "Output should contain version"
    assert "form_id" in output, "Output should contain form_id"
    assert "title" in output, "Output should contain title"

# Test full parsing process
def test_parse(sample_xdp, sample_mapping_file):
    parser = XDPParser(sample_xdp, sample_mapping_file)
    result = parser.parse()
    assert result is not None, "Parsing should return a result"
    assert isinstance(result, dict), "Parsed output should be a dictionary"
    assert "data" in result, "Parsed output should contain data"

# Test handling of missing mapping file
def test_missing_mapping_file():
    with pytest.raises(FileNotFoundError):
        XDPParser("dummy.xdp", "nonexistent.json")

# Test malformed XML handling
def test_malformed_xml(tmp_path, sample_mapping_file):
    malformed_content = """<?xml version="1.0" encoding="UTF-8"?>
    <xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">
        <template xmlns="http://www.xfa.org/schema/xfa-template/3.0/">
            <subform name="TestForm">
                <field name="TestField">
                    <value>
                        <text>Hello World"""
    
    xdp_file = tmp_path / "malformed.xdp"
    xdp_file.write_text(malformed_content)
    
    with pytest.raises(ET.ParseError):
        XDPParser(str(xdp_file), sample_mapping_file)