#!/usr/bin/env python3
"""
Helper script to directly load the HR0080R_fields.json and write a structured version.
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("helper")


class FormField:
    """
    Class representing a form field with all its properties.
    """

    def __init__(
        self,
        field_id: str,
        field_name: str,
        field_type: str,
        label: str = "",
        value: str = "",
    ):
        self.id = field_id  # Unique field ID
        self.name = field_name  # Semantic field name
        self.type = field_type  # Field type (e.g., text-input, radio, container)
        self.label = label  # Human-readable label/question
        self.content = value
        self.value = None  # Default value (if any)
        self.parent: Optional["FormField"] = None  # Parent field (for hierarchy)
        self.children: List["FormField"] = []  # Child fields (for containers)
        self.options: List[str] = []  # Options for radio/dropdown fields
        self.binding_ref: Optional[str] = None  # Data binding reference
        self.help_text: Optional[str] = None  # Help/tooltip text
        self.validation = None  # Validation rules (if any)
        self.javascript = None  # Associated JavaScript (if any)
        self.is_repeating = False  # True if field is a repeating section
        self.max_items = None  # Max items for repeating fields
        self.min_items = None  # Min items for repeating fields
        self.presence = "visible"  # Field visibility
        self.additional_properties = {}  # Any extra properties

    def to_structured_dict(self) -> Dict[str, Any]:
        """
        Convert the FormField object to the new structured format for JSON serialization.
        """
        token = str(uuid.uuid4())
        parent_id = (
            self.parent.token if self.parent and hasattr(self.parent, "token") else None
        )

        # Map field types to the new elementType format
        element_type_mapping = {
            "container": "ContainerFormElements",
            "text-info": "TextInfoFormElements",  # Generic text input
            "text-input": "TextInputFormElements",
            "textarea": "TextareaInputFormElements",
            "checkbox": "CheckboxInputFormElements",
            "radio": "RadioInputFormElements",
            "dropdown": "SelectInputFormElements",
            "date": "DateSelectInputFormElements",
            "numeric": "NumberInputFormElements",
            "button": "ButtonInputFormElements",
            "html": "HtmlFormElements",
        }

        # Default to ContainerFormElements if type not found in mapping
        element_type = element_type_mapping.get(self.type, "ContainerFormElements")

        result = {
            "token": token,
            "parentId": parent_id,
            "name": self.name or "",
            "label": self.label or "",
            "isVisible": self.presence == "visible",
            "isEnabled": True,
            "isReadOnly": False,
            "elementType": element_type,
        }

        # Store token for child references
        self.token = token

        # Add content property for text-info elements
        if self.type == "text-info" and self.value:
            result["content"] = self.value

        # Add container-specific properties
        if self.type == "container":
            result["containerType"] = "section"
            result["collapsible"] = False
            result["collapsedByDefault"] = False
            result["repeats"] = self.is_repeating
            result["minRepeats"] = int(self.min_items) if self.min_items else 1
            result["maxRepeats"] = int(self.max_items) if self.max_items else 1
            result["elements"] = []

            # Process all children and add them to the elements array
            if self.children:
                for child in self.children:
                    child_dict = child.to_structured_dict()
                    result["elements"].append(child_dict)

        # Add data binding for input fields
        if self.binding_ref and self.type not in ["container", "html"]:
            result["dataBinding"] = {
                "dataBindingPath": self.binding_ref,
                "dataBindingType": "jsonpath",
            }

        # Add format for text fields
        if "subtype" in self.additional_properties:
            result["dataFormat"] = self.additional_properties["subtype"]
        elif self.type == "text-input":
            result["dataFormat"] = "text"
        elif self.type == "text-info":
            result["dataFormat"] = "text"
        elif self.type == "numeric":
            result["dataFormat"] = "number"
        elif self.type == "date":
            result["dataFormat"] = "date"

        # Add options for select/radio/checkbox fields
        if self.options and self.type in ["dropdown", "radio"]:
            result["listItems"] = []
            # Support both list of strings and list of dicts
            for i, option in enumerate(self.options):
                if isinstance(option, dict):
                    # Already in {value, label} format
                    result["listItems"].append(option)
                else:
                    # String option, convert to proper format
                    result["listItems"].append({"value": str(i), "label": str(option)})

        # Add help text if present
        if self.help_text:
            result["helpText"] = self.help_text

        return result


def dict_to_form_field(field_dict, parent=None) -> Optional[FormField]:
    """
    Recursively convert a field dictionary to FormField objects
    """
    # Check if field is valid
    if not field_dict or not isinstance(field_dict, dict):
        logger.warning(f"Skipping invalid field: {field_dict}")
        return None

    # Create the field
    field = FormField(
        field_id=field_dict.get("id", str(uuid.uuid4())),
        field_name=field_dict.get("name", ""),
        field_type=field_dict.get("type", "container"),
        label=field_dict.get("label", ""),
    )

    # Copy all other properties
    if "binding_ref" in field_dict:
        field.binding_ref = field_dict["binding_ref"]

    if "is_repeating" in field_dict:
        field.is_repeating = field_dict["is_repeating"]

    if "max_items" in field_dict:
        field.max_items = field_dict["max_items"]

    if "min_items" in field_dict:
        field.min_items = field_dict["min_items"]

    if "presence" in field_dict:
        field.presence = field_dict["presence"]

    if "options" in field_dict:
        field.options = field_dict["options"]

    if "value" in field_dict:
        field.value = field_dict["value"]

    if "help_text" in field_dict:
        field.help_text = field_dict["help_text"]

    if "validation" in field_dict:
        field.validation = field_dict["validation"]

    if "javascript" in field_dict:
        field.javascript = field_dict["javascript"]

    if "subtype" in field_dict:
        field.additional_properties["subtype"] = field_dict["subtype"]

    # Set parent relationship
    field.parent = parent

    # Process children recursively
    if "children" in field_dict and isinstance(field_dict["children"], list):
        logger.info(
            f"Processing {len(field_dict['children'])} children for field {field.name}"
        )

        for child_dict in field_dict["children"]:
            child = dict_to_form_field(child_dict, parent=field)
            if child:
                field.children.append(child)

        logger.info(f"Added {len(field.children)} children to field {field.name}")

    return field


def convert_to_structured_format(fields_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert fields data to structured format"""
    try:
        form_id = fields_data.get("form_id", "unknown")

        # Process each field
        structured_fields = []
        for field_dict in fields_data.get("fields", []):
            field = dict_to_form_field(field_dict)
            if field:
                structured_fields.append(field)

        # Create the output structure
        result = {
            "form_id": form_id,
            "title": f"Converted Form: {form_id}",
            "data": {
                "metadata": {
                    "name": form_id,
                    "status": "draft",
                    "version": "1.0.0",
                    "description": "Converted from old form template",
                },
                "elements": [field.to_structured_dict() for field in structured_fields],
            },
        }

        return result

    except Exception as e:
        logger.error(f"Error in convert_to_structured_format: {e}")
        return None


def main():
    """
    Main function to process the HR0080R_fields.json file
    """
    input_path = Path("HR0080R_fields.json")
    output_path = Path("HR0080R-form-template-v.2.0.json")

    # Check if input file exists
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return False

    # Load the input file
    with open(input_path, "r") as f:
        input_data = json.load(f)

    logger.info(
        f"Loaded input file with {len(input_data.get('fields', []))} top-level fields"
    )

    # Process each field
    fields = []
    for field_dict in input_data.get("fields", []):
        field = dict_to_form_field(field_dict)
        if field:
            fields.append(field)

    # Debug the field structure
    for field in fields:
        logger.info(
            f"Top-level field: {field.name} with {len(field.children)} direct children"
        )

    # Create the output structure
    form_id = input_data.get("form_id", "unknown")
    result = {
        "form_id": form_id,
        "title": f"Converted Form: {form_id}",
        "data": {
            "metadata": {
                "name": form_id,
                "status": "draft",
                "version": "1.0.0",
                "description": "Converted from old form template",
            },
            "elements": [field.to_structured_dict() for field in fields],
        },
    }

    # Write to output file
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Successfully wrote output file to {output_path}")
    return True


def find_matching_conversion_file(fields_file_path: str) -> Optional[str]:
    """Find the corresponding conversion output file for a fields file"""
    fields_path = Path(fields_file_path)
    base_name = fields_path.stem.replace("_fields", "").split("_")[
        0
    ]  # Extract base form name

    # Look in the working-files directory for conversion output
    working_dir = fields_path.parent

    # Search for conversion files with similar names
    for conversion_file in working_dir.glob(f"{base_name}*.json"):
        if "conversion" in conversion_file.name or "output" in conversion_file.name:
            return str(conversion_file)

    return None


def merge_field_data(structured_field: dict, conversion_data: dict) -> dict:
    """Merge data from conversion output into structured field"""
    # Add dataSources if available
    if "dataSources" in conversion_data:
        structured_field["dataSources"] = conversion_data["dataSources"]

    # Add global JavaScript (always add, even if empty)
    if "javascript" in conversion_data:
        structured_field["javascript"] = conversion_data["javascript"]
    else:
        # If no javascript in conversion, add empty object
        structured_field["javascript"] = {}

    # Add codeContext
    if "codeContext" not in structured_field:
        structured_field["codeContext"] = {"name": None}

    return structured_field


def integrate_conversion_data(
    fields_file_path: str, conversion_file_path: str
) -> Dict[str, Any]:
    """Integrate data from both extraction methods"""
    try:
        # Load both files
        with open(fields_file_path, "r", encoding="utf-8") as f:
            fields_data = json.load(f)

        with open(conversion_file_path, "r", encoding="utf-8") as f:
            conversion_data = json.load(f)

        # Convert fields data to structured format
        structured_result = convert_to_structured_format(fields_data)

        # Merge conversion data
        if "data" in structured_result:
            structured_result["data"] = merge_field_data(
                structured_result["data"], conversion_data
            )

        return structured_result

    except Exception as e:
        logger.error(f"Error integrating conversion data: {e}")
        return None


def create_integrated_template(fields_file_path: str) -> bool:
    """Create integrated template combining both extraction methods"""
    try:
        # Find matching conversion file
        conversion_file_path = find_matching_conversion_file(fields_file_path)

        if not conversion_file_path:
            logger.warning(f"No matching conversion file found for {fields_file_path}")
            # Fall back to original method
            return convert_to_structured_format_file(fields_file_path)

        logger.info(f"Integrating {fields_file_path} with {conversion_file_path}")

        # Integrate the data
        integrated_result = integrate_conversion_data(
            fields_file_path, conversion_file_path
        )

        if not integrated_result:
            return False

        # Generate output file path
        fields_path = Path(fields_file_path)
        base_name = fields_path.stem.replace("_fields", "").split("_")[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save to templates directory
        templates_dir = fields_path.parent.parent / "templates"
        templates_dir.mkdir(exist_ok=True)

        output_file = (
            templates_dir / f"{base_name}-integrated-template-v.2.0_{timestamp}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(integrated_result, f, indent=2)

        logger.info(f"Integrated template saved to {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error creating integrated template: {e}")
        return False


def convert_to_structured_format_file(fields_file_path: str) -> bool:
    """Convert fields file to structured format (fallback method)"""
    try:
        with open(fields_file_path, "r", encoding="utf-8") as f:
            fields_data = json.load(f)

        structured_result = convert_to_structured_format(fields_data)

        # Generate output file path
        fields_path = Path(fields_file_path)
        base_name = fields_path.stem.replace("_fields", "").split("_")[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        templates_dir = fields_path.parent.parent / "templates"
        templates_dir.mkdir(exist_ok=True)

        output_file = (
            templates_dir / f"{base_name}-form-template-v.2.0_{timestamp}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_result, f, indent=2)

        logger.info(f"Structured template saved to {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error converting to structured format: {e}")
        return False
