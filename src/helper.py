#!/usr/bin/env python3
"""
Helper script for klamm batch conversion
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
                    result["listItems"].append(
                        {"value": str(option), "label": str(option)}
                    )

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


def find_matching_conversion_file(fields_file_path: str) -> Optional[str]:
    """Find the corresponding conversion output file for a fields file"""
    fields_path = Path(fields_file_path)
    base_name = fields_path.stem.replace("_fields", "").split("_")[
        0
    ]  # Extract base form name

    # Look in the parent directory for working-files directory
    working_dir = fields_path.parent  # This is the working-files directory
    output_dir = working_dir.parent  # This is the output directory
    temp_conversion_dir = output_dir / "working-files"  # Now we get the correct path

    logger.info(f"Looking for working-files directory at: {temp_conversion_dir}")

    if not temp_conversion_dir.exists():
        logger.warning(f"working-files directory not found: {temp_conversion_dir}")
        return None

    logger.info(
        f"Found working-files directory. Searching for files matching: {base_name}*.json"
    )

    # Search for conversion files with similar names
    conversion_files = list(temp_conversion_dir.glob(f"{base_name}*.json"))
    logger.info(
        f"Found {len(conversion_files)} potential conversion files: {[f.name for f in conversion_files]}"
    )

    for conversion_file in conversion_files:
        if "conversion" in conversion_file.name:
            logger.info(f"Found matching conversion file: {conversion_file}")
            return str(conversion_file)

    logger.warning(f"No matching conversion file found for {base_name}")
    return None


def find_field_by_databinding(
    elements: List[dict], databinding_path: str
) -> Optional[dict]:
    """Find a field in the elements list by its databinding path"""
    for element in elements:
        # Check if this element has the matching databinding
        if element.get("dataBinding", {}).get("dataBindingPath") == databinding_path:
            return element

        # Recursively search in child elements
        if "elements" in element:
            found = find_field_by_databinding(element["elements"], databinding_path)
            if found:
                return found

    return None


def find_field_by_name_or_id(
    elements: List[dict], name: str, field_id: str = None
) -> Optional[dict]:
    """Find a field in the elements list by name or id"""
    for element in elements:
        # Check if this element matches by name or id
        if element.get("name") == name or element.get("id") == field_id:
            return element

        # Recursively search in child elements
        if "elements" in element:
            found = find_field_by_name_or_id(element["elements"], name, field_id)
            if found:
                return found

    return None


def merge_conversion_field_data(structured_field: dict, conversion_field: dict) -> dict:
    """Merge data from a single conversion field into a structured field"""

    # Update label if conversion has a better one and structured field doesn't have one
    if conversion_field.get("label") and conversion_field["label"] != "null":
        if not structured_field.get("label") or structured_field["label"] == "":
            structured_field["label"] = conversion_field["label"]

    # Add or update codeContext
    if "codeContext" in conversion_field:
        structured_field["codeContext"] = conversion_field["codeContext"]
    elif "codeContext" not in structured_field:
        structured_field["codeContext"] = {"name": None}

    # Add databindings information - update existing dataBinding if it matches
    if "databindings" in conversion_field:
        databinding = conversion_field["databindings"]
        if "path" in databinding:
            # If the structured field already has a matching dataBinding path, preserve it
            existing_path = structured_field.get("dataBinding", {}).get(
                "dataBindingPath"
            )
            if not existing_path or existing_path == databinding["path"]:
                structured_field["dataBinding"] = {
                    "dataBindingPath": databinding["path"],
                    "dataBindingType": "jsonpath",
                }
                # Also add source if available
                if "source" in databinding:
                    structured_field["dataBinding"]["source"] = databinding["source"]

    # Add styles if present
    if "styles" in conversion_field and conversion_field["styles"]:
        structured_field["styles"] = conversion_field["styles"]

    # Add mask/format information
    if "mask" in conversion_field and conversion_field["mask"]:
        structured_field["mask"] = conversion_field["mask"]
        # For date fields, also set the format
        if structured_field.get("elementType") == "DateSelectInputFormElements":
            structured_field["dateFormat"] = conversion_field["mask"]

    # Add placeholder
    if "placeholder" in conversion_field and conversion_field["placeholder"]:
        structured_field["placeholder"] = conversion_field["placeholder"]

    # Add input type information
    if "inputType" in conversion_field:
        structured_field["inputType"] = conversion_field["inputType"]

    # Add conditions/validation
    if "conditions" in conversion_field:
        structured_field["conditions"] = conversion_field["conditions"]

    if "validation" in conversion_field:
        structured_field["validation"] = conversion_field["validation"]

    # Add calculated values
    if "calculatedValue" in conversion_field:
        structured_field["calculatedValue"] = conversion_field["calculatedValue"]

    # Add list items for dropdowns/selects
    if "listItems" in conversion_field:
        structured_field["listItems"] = conversion_field["listItems"]

    # Add button-specific properties
    if "buttonType" in conversion_field:
        structured_field["buttonType"] = conversion_field["buttonType"]

    # Add checkbox/radio specific properties
    if (
        "value" in conversion_field
        and structured_field.get("elementType") == "CheckboxInputFormElements"
    ):
        structured_field["defaultValue"] = conversion_field["value"]

    # Add repeater information for groups
    if "repeater" in conversion_field:
        structured_field["repeats"] = conversion_field["repeater"]
        if "groupItems" in conversion_field:
            structured_field["groupItems"] = conversion_field["groupItems"]

    return structured_field


def integrate_fields_recursive(
    structured_elements: List[dict], conversion_items: List[dict]
) -> None:
    """Recursively integrate conversion data into structured elements"""

    logger.info(
        f"integrate_fields_recursive: Processing {len(structured_elements)} elements with {len(conversion_items)} conversion items"
    )

    # Create a mapping of conversion items by databinding path (most reliable identifier)
    conversion_map = {}
    for item in conversion_items:
        # Map by databinding path (most reliable)
        if "databindings" in item and "path" in item["databindings"]:
            conversion_map[item["databindings"]["path"]] = item
            logger.debug(
                f"Mapped conversion item by path: {item['databindings']['path']}"
            )

    logger.info(
        f"Created conversion map with {len(conversion_map)} entries by databinding path"
    )

    # Update each structured element
    matches_found = 0
    for element in structured_elements:
        # Try to find matching conversion data by databinding path
        conversion_data = None

        if element.get("dataBinding", {}).get("dataBindingPath"):
            path = element["dataBinding"]["dataBindingPath"]
            conversion_data = conversion_map.get(path)
            if conversion_data:
                logger.debug(f"Found match for path: {path}")
                # Merge the data directly into the element (modify in place)
                merge_conversion_field_data(element, conversion_data)
                matches_found += 1
                logger.debug(
                    f"Merged conversion data for field: {element.get('name', 'unnamed')}"
                )

        # Recursively process child elements
        if "elements" in element and element["elements"]:
            integrate_fields_recursive(element["elements"], conversion_items)

    logger.info(f"Found {matches_found} matches in this level")


def integrate_conversion_data(
    fields_file_path: str, conversion_file_path: str
) -> Dict[str, Any]:
    """Integrate data from both extraction methods"""
    try:
        logger.info(
            f"Starting integration of {fields_file_path} with {conversion_file_path}"
        )

        # Load both files
        with open(fields_file_path, "r", encoding="utf-8") as f:
            fields_data = json.load(f)

        with open(conversion_file_path, "r", encoding="utf-8") as f:
            conversion_data = json.load(f)

        logger.info(
            f"Loaded {len(fields_data.get('fields', []))} fields from extraction"
        )
        logger.info(
            f"Loaded {len(conversion_data.get('data', {}).get('items', []))} items from conversion"
        )

        # Convert fields data to structured format
        logger.info("Converting fields data to structured format...")
        structured_result = convert_to_structured_format(fields_data)

        if not structured_result:
            logger.error("Failed to convert fields data to structured format")
            return None

        logger.info("Successfully converted to structured format")

        # Merge conversion data
        if "data" in structured_result:
            logger.info("Merging conversion data...")
            structured_result["data"] = merge_field_data(
                structured_result["data"], conversion_data
            )
            logger.info("Successfully merged conversion data")

        logger.info("Integration completed successfully")
        return structured_result

    except Exception as e:
        logger.error(f"Error integrating conversion data: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


def merge_field_data(structured_data: dict, conversion_data: dict) -> dict:
    """Merge data from conversion output into structured field data"""
    logger.info("Starting merge_field_data")

    # Add dataSources if available
    if "dataSources" in conversion_data:
        structured_data["dataSources"] = conversion_data["dataSources"]
        logger.info("Added dataSources")

    # Add global JavaScript (always add, even if empty)
    if "javascript" in conversion_data:
        structured_data["javascript"] = conversion_data["javascript"]
        logger.info("Added JavaScript from conversion")
    else:
        # If no javascript in conversion, add empty object
        structured_data["javascript"] = {}
        logger.info("Added empty JavaScript object")

    # Integrate field-level data from conversion items
    if "data" in conversion_data and "items" in conversion_data["data"]:
        conversion_items = conversion_data["data"]["items"]
        logger.info(f"Found {len(conversion_items)} conversion items to integrate")

        # Recursively integrate the conversion data into structured elements
        if "elements" in structured_data:
            logger.info(
                f"Integrating into {len(structured_data['elements'])} structured elements"
            )
            integrate_fields_recursive(structured_data["elements"], conversion_items)
            logger.info("Completed recursive field integration")
        else:
            logger.warning("No elements found in structured data")
    else:
        logger.warning("No conversion items found to integrate")

    logger.info("Completed merge_field_data")
    return structured_data


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
        templates_dir = fields_path.parent.parent / "final_templates"
        templates_dir.mkdir(exist_ok=True)

        output_file = templates_dir / f"{base_name}.json"

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
