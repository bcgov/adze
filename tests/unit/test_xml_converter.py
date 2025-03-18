import pytest
from xml_converter import parse_xdp_to_json

@pytest.fixture
def sample_xdp_file(tmp_path):
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

def test_parse_xdp_to_json(sample_xdp_file):
    """Tests if the XDP file is parsed into JSON correctly."""
    result = parse_xdp_to_json(sample_xdp_file)
    
    assert result is not None, "Parsing should return a result"
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "title" in result, "Result JSON should contain a title"
    assert "form_id" in result, "Result JSON should contain a form_id"    
    