import pytest
import json
import os
import xml.etree.ElementTree as ET
from converter import XDPToJSONConverter
from unittest.mock import patch, mock_open

@pytest.fixture
def sample_mapping():
    return {
        "fields": {
            "timeStamp": {
                "name": "lastModified",
                "xpath": "./xdp:xdp",
                "transforms": [{"type": "default", "value": "2024-12-20T22:02:55+00:00"}]
            },
            "uuid": {
                "name": "id",
                "xpath": "./xdp:xdp",
                "transforms": [{"type": "default", "value": "uuid-1234"}]
            },
            "FormTitle": {
                "xpath": ".//template:subform",
                "name": "title",
                "transforms": [{"type": "constant", "value": "Work Search Activity Record"}]
            }
        },
        "constants": {
            "version": {"value": 8},
            "ministry_id": {"value": 2}
        }
    }


@pytest.fixture
def converter(sample_mapping, tmp_path):
    mapping_file = tmp_path / "mapping.json"
    with open(mapping_file, "w") as f:
        json.dump(sample_mapping, f)
    return  XDPToJSONConverter(str(mapping_file))

# # Test _load_mapping
# @pytest.mark.parametrize("invalid_json", ["{invalid}", "[1,2,3]"])
# def test_load_mapping_invalid(tmp_path, invalid_json):
#     mapping_file = tmp_path / "invalid_mapping.json"
#     with open(mapping_file, "w") as f:
#         f.write(invalid_json)
#     with pytest.raises(Exception):
#         XDPToJSONConverter(str(mapping_file))

# Test _apply_transformations
@pytest.mark.parametrize("value, transforms, expected", [
    ("123", [{"type": "convert_type", "target_type": "int"}], 123),
    ("true", [{"type": "convert_type", "target_type": "boolean"}], True),
    ("abcd", [{"type": "default", "value": "xyz"}], "abcd"),
    (None, [{"type": "default", "value": "xyz"}], "xyz"),
    ("2024-03-03T10:00:00Z", [{"type": "format_date", "input_format": "%Y-%m-%dT%H:%M:%SZ", "output_format": "%Y-%m-%d"}], "2024-03-03")
])
def test_apply_transformations(converter, value, transforms, expected):
    assert converter._apply_transformations(value, transforms) == expected

# Test _get_