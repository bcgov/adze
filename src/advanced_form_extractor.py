#!/usr/bin/env python3
"""
Advanced Form Field Extractor for XDP and PDF Forms

This script provides comprehensive field extraction for XDP forms,
maintaining hierarchical structure, properly handling repeater sections, and
extracting all relevant field metadata. It supports batch processing.

Usage:
    python advanced_form_extractor.py --input-file <path_to_form_file> --output-dir <output_directory>

"""

import os
import re
import argparse
import json
import logging
import xml.etree.ElementTree as ET
import pypdf
import uuid
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from collections import defaultdict, OrderedDict
from typing import Dict, List, Any, Union, Optional, Set, Tuple

# Configure logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("advanced_form_extractor")

# Import FormField class from helper module
from helper import FormField as StructuredFormField

# Fix the XDPParser import with error handling
try:
    from xml_converter_class import XDPParser  # <-- for JS and metadata extraction
except ImportError as e:
    # If XDPParser is not available, create a stub
    logger.warning(f"XDPParser not available: {e}. Using stub implementation.")

    class XDPParser:
        def __init__(self, xdp_file_path):
            self.xdp_file_path = xdp_file_path

        def extract_all_javascript(self):
            return {}

        def extract_field_metadata(self, field_elem):
            return {}

        def extract_field_javascript(self, field_elem):
            return None


class XDPFormExtractor:
    """Extract form fields from an XDP file maintaining hierarchical structure"""

    def __init__(self, xdp_file_path: str):
        self.xdp_file_path = xdp_file_path
        self.namespaces = {
            "xdp": "http://ns.adobe.com/xdp/",
            "template": "http://www.xfa.org/schema/xfa-template/3.0/",
            "xfa": "http://www.xfa.org/schema/xfa/3.0/",
        }
        self.next_id = 1
        self.fields = []
        self.javascript_cache = {}
        self.field_names = set()
        self.form_id = os.path.basename(xdp_file_path).split(".")[0]
        # Track processed field labels to avoid duplication and maintain consistency
        self.processed_labels = {}
        # Store standardized names for consistent naming across different forms
        self.standardized_fields = {}
        self.generic_field_patterns = {
            "text-input": re.compile(
                r"^(TextField|Text|Input|String|Field|txt|entry|value|content)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "checkbox": re.compile(
                r"^(CheckBox|Check|chk|toggle|flag|indicator)\d*(_\d+)?$", re.IGNORECASE
            ),
            "radio": re.compile(
                r"^(Radio|RadioButton|option|choice|select)\d*(_\d+)?$", re.IGNORECASE
            ),
            "dropdown": re.compile(
                r"^(DropDown|Select|Choice|ComboBox|list|menu|options)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "date": re.compile(
                r"^(Date|DateField|DateTime|calendar|day|time)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "numeric": re.compile(
                r"^(NumericField|Number|Integer|Float|Decimal|amount|sum|total|count)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "signature": re.compile(
                r"^(SignField|Signature|Sign|esign|autograph)\d*(_\d+)?$", re.IGNORECASE
            ),
            "address": re.compile(
                r"^(Address|AddressField|location|place|residence)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "comment": re.compile(
                r"^(Comment|Comments|CommentField|note|feedback|message)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
        }
        self.field_context = {}  # To store parent-child relationships for context

        try:
            self.tree = ET.parse(xdp_file_path)
            self.root = self.tree.getroot()
            self.extract_namespaces()
        except Exception as e:
            logger.error(f"Error parsing XDP file: {e}")
            raise

        # Only initialize XDPParser if it's available
        try:
            self.xdp_parser = XDPParser(
                xdp_file_path
            )  # Use for JS and metadata extraction
        except Exception as e:
            logger.warning(f"Failed to initialize XDPParser: {e}")
            self.xdp_parser = None

    def get_next_id(self) -> str:
        """Get the next unique ID"""
        current_id = str(self.next_id)
        self.next_id += 1
        return current_id

    def extract_namespaces(self):
        """Extract namespaces from the XDP document"""
        for elem in self.root.iter():
            if "}" in elem.tag:
                uri = elem.tag.split("}")[0].strip("{")
                for prefix in ["xdp", "template", "xfa"]:
                    if prefix in uri.lower():
                        self.namespaces[prefix] = uri

    def extract_label(self, field_elem):
        """Extract label from field using multiple methods - enhanced version from XML converter"""
        try:
            label = None

            # Method 0: Check for rich HTML caption (exData inside caption/value)
            caption_elem = field_elem.find(".//template:caption", self.namespaces)
            if caption_elem is not None:
                for val in caption_elem.findall(".//template:value", self.namespaces):
                    exdata = val.find(".//template:exData", self.namespaces)
                    if exdata is not None:
                        # Even if exdata.text is None, extract the inner XML
                        html_content = ET.tostring(
                            exdata, encoding="unicode", method="xml"
                        )
                        soup = BeautifulSoup(html_content, "html.parser")

                        for tag_name in ["p", "div", "span"]:
                            tag_elem = soup.find(tag_name)
                            if tag_elem and tag_elem.get_text(strip=True):
                                label = tag_elem.get_text(strip=True)
                                break

                        if not label:
                            label = soup.get_text(strip=True)
                        if (
                            label and label.strip()
                        ):  # Only break if we have actual content
                            break

            # Method 1: Direct caption text
            if not label or not label.strip():
                caption_elem = field_elem.find(
                    ".//template:caption//template:text", self.namespaces
                )
                if (
                    caption_elem is not None
                    and caption_elem.text
                    and caption_elem.text.strip()
                ):
                    label = caption_elem.text.strip()

            # Method 2: Value text that looks like a label
            if not label or not label.strip():
                value_elem = field_elem.find(
                    ".//template:value//template:text", self.namespaces
                )
                if (
                    value_elem is not None
                    and value_elem.text
                    and value_elem.text.strip()
                ):
                    text = value_elem.text.strip()
                    # Check if this looks like a label (ends with :, all caps, etc)
                    if text.endswith(":") or text.isupper() or len(text.split()) <= 4:
                        label = text

            # Method 3: Field name converted to label - ENHANCED
            if not label or not label.strip():
                field_name = field_elem.get("name", "")
                if field_name:
                    # Convert camelCase/snake_case to space-separated words
                    import re

                    # Handle camelCase like "childSex" -> "child Sex"
                    # First insert space before uppercase letters that follow lowercase letters
                    label = re.sub(r"([a-z])([A-Z])", r"\1 \2", field_name)

                    # Handle sequences of uppercase letters followed by lowercase
                    label = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", label)

                    # Replace underscores and hyphens with spaces
                    label = re.sub(r"[-_]+", " ", label)

                    # Clean up multiple spaces and capitalize each word
                    label = " ".join(
                        word.capitalize() for word in label.split() if word
                    )

                    # Log the conversion for debugging
                    logger.debug(
                        f"Converted field name '{field_name}' to label '{label}'"
                    )

            # Fallback: Use field name as-is if nothing else worked
            if not label or not label.strip():
                field_name = field_elem.get("name", "")
                if field_name:
                    label = field_name.replace("_", " ").replace("-", " ").title()
                    logger.debug(f"Using field name as fallback label: '{label}'")

            return label if label and label.strip() else None

        except Exception as e:
            logger.warning(f"Error extracting label: {e}")
            field_name = field_elem.get("name", "")
            if field_name:
                # Emergency fallback
                return field_name.replace("_", " ").replace("-", " ").title()
            return None

    def get_field_type(self, ui_elem):
        """Determine field type from UI element"""
        if ui_elem is None:
            return "text-input", None

        # Check for specific UI types
        if ui_elem.find("./template:textEdit", self.namespaces) is not None:
            return "text-input", None
        elif ui_elem.find("./template:checkButton", self.namespaces) is not None:
            return "checkbox", None
        elif ui_elem.find("./template:choiceList", self.namespaces) is not None:
            choice_elem = ui_elem.find("./template:choiceList", self.namespaces)
            if choice_elem.get("open") == "userControl":
                return "dropdown", "combobox"
            else:
                return "dropdown", "list"
        elif ui_elem.find("./template:signature", self.namespaces) is not None:
            return "signature", None
        elif ui_elem.find("./template:numericEdit", self.namespaces) is not None:
            return "numeric", None
        elif ui_elem.find("./template:dateTimeEdit", self.namespaces) is not None:
            return "date", None
        elif ui_elem.find("./template:passwordEdit", self.namespaces) is not None:
            return "password", None
        elif ui_elem.find("./template:button", self.namespaces) is not None:
            return "button", None

        return "text-input", None

    def extract_options(self, field_elem):
        """Extract options for choice fields, ignoring items with presence='hidden'"""
        options = []
        # Find all <items> elements under the field
        items_elements = field_elem.findall(".//template:items", self.namespaces)
        for items_elem in items_elements:
            # Skip <items> with presence="hidden"
            if items_elem.get("presence", "").lower() == "hidden":
                continue
            # For each <text> child, add its text as an option
            for item in items_elem.findall("template:text", self.namespaces):
                if item.text:
                    options.append(item.text.strip())
        return options

    def extract_binding(self, field_elem):
        """Extract data binding reference"""
        bind_elem = field_elem.find("./template:bind", self.namespaces)
        if bind_elem is not None:
            return bind_elem.get("ref", "")
        return ""

    def extract_help_text(self, field_elem):
        """Extract help text from field"""
        # Look for assist text
        assist_elem = field_elem.find(
            ".//template:assist/template:text", self.namespaces
        )
        if assist_elem is not None and assist_elem.text:
            return assist_elem.text.strip()

        # Look for toolTip
        tooltip_elem = field_elem.find(
            ".//template:assist/template:toolTip", self.namespaces
        )
        if tooltip_elem is not None and tooltip_elem.text:
            return tooltip_elem.text.strip()

        return ""

    def extract_javascript(self):
        """Extract all JavaScript from the XDP file using XDPParser logic"""
        if self.xdp_parser:
            self.javascript_cache = self.xdp_parser.extract_all_javascript()
        else:
            self.javascript_cache = {}

    def extract_field_metadata(self, field_elem):
        """Extract rich metadata using XDPParser logic"""
        meta = {}
        if self.xdp_parser:
            # calculatedValue, conditions, mask, styles, placeholder, inputType, databindings, etc.
            meta.update(self.xdp_parser.extract_field_metadata(field_elem))
        return meta

    def extract_draw_text(self, draw_elem):
        """Extract all text from <draw> including textRun and <value><text>"""
        texts = []
        # <value><text>
        value_text = draw_elem.find(".//template:value/template:text", self.namespaces)
        if value_text is not None and value_text.text:
            texts.append(value_text.text.strip())
        # <?renderCache.textRun ...?>
        if draw_elem.tail:
            # Sometimes textRun is in tail, but more robust is to check .text and .tail for each child
            pass
        # Also check for processing instructions (textRun) in the XML string
        xml_str = ET.tostring(draw_elem, encoding="unicode")
        for match in re.findall(r"<\?renderCache\.textRun\s+\d+\s+(.*?)\?>", xml_str):
            # Remove font and encoding info, just get the text
            parts = match.split('"')
            if len(parts) > 1:
                texts.append(parts[1])
            else:
                # fallback: take the first wordy part
                texts.append(match.strip())
        return " ".join(texts).strip()

    def extract_subform_fields(
        self, subform_elem, parent=None, parent_path=""
    ) -> List[StructuredFormField]:
        """Recursively extract fields from a subform element, limit nesting to one level"""
        result = []

        # Process the subform itself as a container field
        original_subform_name = subform_elem.get("name", "")
        if not original_subform_name:
            subform_name = f"subform_{self.get_next_id()}"
        else:
            subform_name = original_subform_name

        # Store the full path for context
        current_path = f"{parent_path}.{subform_name}" if parent_path else subform_name

        # Extract label for the subform if available
        subform_label = self.extract_label(subform_elem)

        # Generate semantic name for the subform
        if original_subform_name:
            # Only generate a semantic name if it's not already a good name
            if self._is_generic_field_name(original_subform_name, "container"):
                semantic_subform_name = self.generate_semantic_field_name(
                    subform_elem, "container", subform_label, parent_path
                )
                # Don't override original names for key structural elements
                if original_subform_name not in [
                    "ListOfDtFormInstanceLw",
                    "page1",
                    "Top",
                ]:
                    subform_name = semantic_subform_name

        subform_field = StructuredFormField(
            field_id=self.get_next_id(),
            field_name=subform_name,
            field_type="container",
            label=subform_label or "",
        )

        # Check if this is a repeating subform
        occur_elem = subform_elem.find(".//template:occur", self.namespaces)
        if occur_elem is not None:
            subform_field.is_repeating = True
            subform_field.min_items = occur_elem.get("min", "1")
            subform_field.max_items = occur_elem.get("max", "-1")  # -1 means unlimited

        # Set presence attribute if specified
        presence = subform_elem.get("presence", "visible")
        if presence != "visible":
            subform_field.presence = presence

        if parent:
            subform_field.parent = parent
            parent.children.append(subform_field)

        # --- ENHANCEMENT: Add <draw> text as "text-info" fields grouped by draw ---
        for draw_elem in subform_elem.findall("./template:draw", self.namespaces):
            text = self.extract_draw_text(draw_elem)
            if text:
                draw_name = draw_elem.get("name", f"text_info_{self.get_next_id()}")
                text_field = StructuredFormField(
                    field_id=self.get_next_id(),
                    field_name=draw_name,
                    field_type="text-info",
                    label="",
                )
                text_field.value = text
                # Add draw metadata if available
                text_field.additional_properties.update(
                    self.extract_field_metadata(draw_elem)
                )
                subform_field.children.append(text_field)

        # --- ENHANCEMENT: Add fields with rich metadata ---
        for field_elem in subform_elem.findall("./template:field", self.namespaces):
            # Get UI element to determine field type
            ui_elem = field_elem.find("./template:ui", self.namespaces)
            field_type, field_subtype = self.get_field_type(ui_elem)

            # Extract the label first as we need it for name generation
            field_label = self.extract_label(field_elem)

            # Generate semantic field name
            field_name = self.generate_semantic_field_name(
                field_elem, field_type, field_label, current_path
            )

            # Ensure uniqueness
            if field_name in self.field_names:
                field_name = f"{field_name}_{self.get_next_id()}"
            self.field_names.add(field_name)

            # Update field context for future reference
            self.field_context[field_name] = {
                "parent_path": current_path,
                "type": field_type,
                "label": field_label,
            }

            # Create the field
            field = StructuredFormField(
                field_id=self.get_next_id(),
                field_name=field_name,
                field_type=field_type,
                label=field_label or "",
            )

            # Set presence attribute
            presence = field_elem.get("presence", "visible")
            if presence != "visible":
                field.presence = presence

            # Add subtype if available
            if field_subtype:
                field.additional_properties["subtype"] = field_subtype

            # Extract options for choice fields
            if field_type in ["radio", "dropdown"]:
                field.options = self.extract_options(field_elem)

            # Extract data binding
            binding_ref = self.extract_binding(field_elem)
            if binding_ref:
                field.binding_ref = binding_ref

            # Extract help text
            help_text = self.extract_help_text(field_elem)
            if help_text:
                field.help_text = help_text

            # ENHANCEMENT: Add rich metadata
            field.additional_properties.update(self.extract_field_metadata(field_elem))

            # ENHANCEMENT: Use XDPParser's JS extraction for this field
            if self.xdp_parser:
                js = self.xdp_parser.extract_field_javascript(field_elem)
                if js:
                    field.javascript = js

            # Add the field to the subform
            field.parent = subform_field
            subform_field.children.append(field)

        # --- ENHANCEMENT: Process nested subforms and add them as children ---
        for nested_subform in subform_elem.findall(
            "./template:subform", self.namespaces
        ):
            # Extract nested subform fields and add them to the current subform
            nested_fields = self.extract_subform_fields(
                nested_subform, parent=subform_field, parent_path=current_path
            )
            # The nested fields are already added to subform_field through the parent parameter

        # --- ENHANCEMENT: Process exclGroup (radio button groups) ---
        for exclgroup_elem in subform_elem.findall(
            "./template:exclGroup", self.namespaces
        ):
            group_name = exclgroup_elem.get("name", f"radiogroup_{self.get_next_id()}")

            # Extract binding for the group
            binding_ref = self.extract_binding(exclgroup_elem)

            # Create radio group field
            radio_group_field = StructuredFormField(
                field_id=self.get_next_id(),
                field_name=group_name,
                field_type="radio",
                label="",
            )

            if binding_ref:
                radio_group_field.binding_ref = binding_ref

            # Extract options from child fields
            options = []
            for field_elem in exclgroup_elem.findall(
                "./template:field", self.namespaces
            ):
                # Get the caption text for the label
                caption_text = self.extract_label(field_elem)
                # Get the value from items
                items = field_elem.findall(
                    ".//template:items/template:text", self.namespaces
                )
                value = items[0].text.strip() if items and items[0].text else ""

                if caption_text and value:
                    options.append({"value": value, "label": caption_text})
                elif caption_text:
                    # If no explicit value, use index as value
                    options.append({"value": str(len(options)), "label": caption_text})

            radio_group_field.options = options

            # Debug logging
            logger.info(
                f"Created radio group '{group_name}' with {len(options)} options: {options}"
            )

            # Add JavaScript if present
            if self.xdp_parser:
                js = self.xdp_parser.extract_field_javascript(exclgroup_elem)
                if js:
                    radio_group_field.javascript = js

            radio_group_field.parent = subform_field
            subform_field.children.append(radio_group_field)

        result.append(subform_field)
        return result

    def extract(self) -> Dict[str, Any]:
        """Extract all form fields maintaining hierarchy"""
        # Initialize field context tracking
        self.field_context = {}

        # First extract all JavaScript
        self.extract_javascript()

        # Find the root subform
        root_subform = self.root.find(".//template:subform", self.namespaces)
        if not root_subform:
            logger.error("No root subform found in XDP file")
            return {"form_id": self.form_id, "fields": []}

        # Extract fields from the root subform with context tracking
        fields = self.extract_subform_fields(root_subform, parent=None, parent_path="")

        # Create the result object
        result = {
            "form_id": self.form_id,
            "extraction_date": datetime.now().isoformat(),
            "source_file": os.path.basename(self.xdp_file_path),
            "format": "xdp",
            "fields": self._fields_to_dict(fields),
        }

        return result

    def _fields_to_dict(self, fields):
        """Convert FormField objects to dictionaries for serialization"""
        result = []
        for field in fields:
            field_dict = {
                "id": field.id,
                "name": field.name,
                "type": field.type,
            }

            if field.label:
                field_dict["label"] = field.label

            if field.value is not None:
                field_dict["value"] = field.value

            if field.binding_ref:
                field_dict["binding_ref"] = field.binding_ref

            if field.help_text:
                field_dict["help_text"] = field.help_text

            if field.validation:
                field_dict["validation"] = field.validation

            if field.javascript:
                field_dict["javascript"] = field.javascript

            if field.options:
                field_dict["options"] = field.options

            if field.is_repeating:
                field_dict["is_repeating"] = True
                if field.max_items:
                    field_dict["max_items"] = field.max_items
                if field.min_items:
                    field_dict["min_items"] = field.min_items

            if field.presence != "visible":
                field_dict["presence"] = field.presence

            if field.children:
                field_dict["children"] = self._fields_to_dict(field.children)

            # Add any additional properties
            for key, value in field.additional_properties.items():
                field_dict[key] = value

            result.append(field_dict)

        return result

    def generate_semantic_field_name(
        self, field_elem, field_type: str, label: str = "", parent_path: str = ""
    ) -> str:
        """
        Generate a semantic field name based on label, type and context.

        This method prioritizes descriptive names derived from labels over generic names,
        and ensures that the resulting field name is human-readable and meaningful.
        """
        # ALWAYS prioritize using labels for field names when available
        if label:
            # Convert None to empty string if needed
            actual_label = label or ""

            # Check if we've already processed a similar label to maintain consistency
            normalized_label = actual_label.lower().strip()
            if normalized_label in self.processed_labels:
                # Return the previously used field name for consistency
                return self.processed_labels[normalized_label]

            # Generate a new field name from the label
            name = self._label_to_field_name(actual_label)

            # Store this mapping for future consistency
            self.processed_labels[normalized_label] = name

            # Add context from parent if available and meaningful
            if parent_path and parent_path not in [
                "ListOfDtFormInstanceLw",
                "page1",
                "form1",
                "Top",
                "Root",
            ]:
                parent_context = self._get_context_from_path(parent_path)
                # Only add parent context if it's not already in the name and adds meaning
                if parent_context and parent_context not in name:
                    # Check if parent context is meaningful enough to include
                    if len(parent_context) > 2 and not parent_context.isdigit():
                        name = f"{parent_context}_{name}"

            # Add field type suffix if needed for clarity
            if field_type == "checkbox" and not any(
                name.endswith(suffix)
                for suffix in [
                    "_is",
                    "_has",
                    "_flag",
                    "_indicator",
                    "_selected",
                    "_checked",
                ]
            ):
                name = f"{name}_flag"
            elif field_type == "date" and not any(
                name.endswith(suffix)
                for suffix in ["_date", "_time", "_day", "_month", "_year", "_dob"]
            ):
                name = f"{name}_date"
            elif field_type == "numeric" and not any(
                name.endswith(suffix)
                for suffix in [
                    "_amount",
                    "_number",
                    "_count",
                    "_total",
                    "_quantity",
                    "_value",
                    "_sum",
                ]
            ):
                name = f"{name}_amount"
            elif field_type == "dropdown" and not any(
                name.endswith(suffix)
                for suffix in ["_select", "_choice", "_option", "_list", "_selection"]
            ):
                name = f"{name}_selection"

            # Ensure uniqueness by adding a suffix if needed
            base_name = name
            counter = 1
            while name in self.field_names:
                name = f"{base_name}_{counter}"
                counter += 1

            # Add to our tracking set
            self.field_names.add(name)
            return name

        # Check if there's a non-generic explicit name in the element
        original_name = field_elem.get("name", "")
        if original_name and not self._is_generic_field_name(original_name, field_type):
            # Clean up the original name if needed
            cleaned_name = re.sub(r"[^\w_]", "", original_name)
            cleaned_name = re.sub(r"_{2,}", "_", cleaned_name)

            # Ensure the clean name is unique
            if cleaned_name not in self.field_names:
                self.field_names.add(cleaned_name)
                return cleaned_name

            # Make it unique if needed
            base_name = cleaned_name
            counter = 1
            while cleaned_name in self.field_names:
                cleaned_name = f"{base_name}_{counter}"
                counter += 1

            self.field_names.add(cleaned_name)
            return cleaned_name

        # If no label or usable name, try to get meaningful context
        if parent_path:
            parent_context = self._get_context_from_path(parent_path)
            if parent_context:
                # Try to get any caption or title from the parent element that might be descriptive
                parent_elem = (
                    field_elem.getparent() if hasattr(field_elem, "getparent") else None
                )
                parent_label = ""

                if parent_elem is not None:
                    parent_label = self.extract_label(parent_elem) or ""
                    if parent_label:
                        parent_label = self._label_to_field_name(parent_label)

                # Create a more contextual name with parent information
                if parent_label:
                    name = f"{parent_context}_{parent_label}_{field_type}"

                    # Ensure uniqueness
                    if name not in self.field_names:
                        self.field_names.add(name)
                        return name

                    base_name = name
                    counter = 1
                    while name in self.field_names:
                        name = f"{base_name}_{counter}"
                        counter += 1

                    self.field_names.add(name)
                    return name
                else:
                    # Use context with type
                    name = f"{parent_context}_{field_type}"

                    # Ensure uniqueness
                    if name not in self.field_names:
                        self.field_names.add(name)
                        return name

                    # Only add numerical suffix if needed for uniqueness
                    base_name = name
                    counter = 1
                    while name in self.field_names:
                        name = f"{base_name}_{counter}"
                        counter += 1

                    self.field_names.add(name)
                    return name

        # Last resort - create a generic but unique field type-based name
        type_name = field_type.replace("-", "_")
        name = f"{type_name}_field"

        # Ensure uniqueness
        if name not in self.field_names:
            self.field_names.add(name)
            return name

        # Add counter only if needed for uniqueness
        base_name = name
        counter = 1
        while name in self.field_names:
            name = f"{base_name}_{counter}"
            counter += 1

        self.field_names.add(name)
        return name

    def _is_generic_field_name(self, name: str, field_type: str) -> bool:
        """
        Check if a field name is generic or non-descriptive.

        This enhanced version aggressively identifies patterns like "SignField_123", "Address_21", etc.
        that should be replaced with more descriptive, label-based names.
        """
        # Check if it matches generic patterns like "TextField1" or "Checkbox_123"
        for type_name, pattern in self.generic_field_patterns.items():
            if pattern.match(name):
                return True

        # Check for completely numeric names
        if name.isdigit():
            return True

        # Check for names ending with numbers (e.g., "field123", "sign_475")
        if re.match(r"^[a-z_]+\d+$", name, re.IGNORECASE):
            return True

        # Check for field names with Field_NUMBER pattern (e.g., "SignField_475")
        if re.match(r"^[a-z]+Field_\d+$", name, re.IGNORECASE):
            return True

        # Check for names with numbers in the middle or separated by underscores
        if re.search(r"_\d+_", name) or re.search(
            r"[a-z]\d+[a-z]", name, re.IGNORECASE
        ):
            return True

        # Check for short, non-descriptive names (fewer than 3 chars)
        if len(name) < 3:
            return True

        # Check for common generic patterns
        generic_patterns = [
            re.compile(r"^field\d*(_\d+)?$", re.IGNORECASE),
            re.compile(r"^[a-z]+\d+$", re.IGNORECASE),  # Like "text1", "input2"
            re.compile(r"^[a-z]+_\d+$", re.IGNORECASE),  # Like "text_1", "input_2"
            re.compile(r"^(sub)?form\d*", re.IGNORECASE),  # Form patterns
            re.compile(r"^(xfa)?\d*", re.IGNORECASE),  # XFA patterns
            re.compile(r"^f\d+$", re.IGNORECASE),  # f1, f2, f3 patterns
            re.compile(
                r"^(control|ctrl|element|item|widget|component)\d*(_\d+)?$",
                re.IGNORECASE,
            ),  # UI control patterns
            re.compile(r"^(c|e|i|x)\d+$", re.IGNORECASE),  # c1, e2, i3 patterns
            re.compile(
                r"^(page|section|block|panel|group|container)\d*(_\d+)?$", re.IGNORECASE
            ),  # Layout patterns
            re.compile(
                r"^(tb|rb|cb|dd|btn)\d*(_\d+)?$", re.IGNORECASE
            ),  # Common abbreviated forms
        ]

        for pattern in generic_patterns:
            if pattern.match(name):
                return True

        # Check for names that only consist of a type identifier
        type_identifiers = [
            "text",
            "input",
            "field",
            "check",
            "box",
            "button",
            "sign",
            "signature",
            "date",
            "name",
            "address",
            "phone",
            "email",
            "fax",
            "zip",
            "city",
            "state",
            "select",
            "option",
            "radio",
            "toggle",
            "label",
            "value",
            "data",
            "checkbox",
            "dropdown",
            "image",
            "file",
            "attachment",
            "submit",
            "reset",
            "cancel",
            "street",
            "number",
            "country",
            "dob",
            "ssn",
            "amount",
            "total",
            "subtotal",
            "tax",
            "payment",
            "price",
            "cost",
            "fee",
            "barcode",
            "code",
            "item",
        ]
        if name.lower() in type_identifiers:
            return True

        # Check for auto-generated XFA field names (often capitalized acronyms followed by numbers)
        if re.match(r"^[A-Z]{2,5}\d+$", name):
            return True

        # Check for names that are just common abbreviations
        common_abbreviations = [
            "fn",
            "ln",
            "mn",
            "mi",
            "dob",
            "ssn",
            "ein",
            "ph",
            "tel",
            "addr",
            "str",
            "cty",
            "st",
            "zip",
            "amt",
            "qty",
            "sig",
            "dt",
            "fld",
            "btn",
            "chk",
            "opt",
        ]
        if name.lower() in common_abbreviations:
            return True

        # Check for very short names with numbers (like f1, t2, etc.)
        if re.match(r"^[a-z]{1,2}\d+$", name, re.IGNORECASE):
            return True

        return False

    def _label_to_field_name(self, label: str) -> str:
        """
        Convert a label to a semantic, descriptive snake_case field name.

        This enhanced version creates more meaningful field names by:
        1. Preserving the most descriptive words
        2. Intelligently handling questions and instructions
        3. Recognizing common field name patterns and standardizing them
        """
        if not label:
            return ""

        # Standardize common label patterns first
        label_lower = label.lower()

        # Map common field labels to standard names
        common_fields = {
            re.compile(r"first\s*name"): "first_name",
            re.compile(r"last\s*name"): "last_name",
            re.compile(r"full\s*name"): "full_name",
            re.compile(r"middle\s*(name|initial)"): "middle_name",
            re.compile(r"(email|e-mail)(\s*address)?"): "email_address",
            re.compile(r"phone\s*(number|no\.?)"): "phone_number",
            re.compile(r"cell\s*(phone|number)"): "mobile_number",
            re.compile(r"mobile\s*(phone|number)"): "mobile_number",
            re.compile(r"work\s*(phone|number)"): "work_phone",
            re.compile(r"home\s*(phone|number)"): "home_phone",
            re.compile(r"fax(\s*number)?"): "fax_number",
            re.compile(r"social\s*security(\s*number|\s*no\.?|\s*#)"): "ssn",
            re.compile(r"tax(\s*id|\s*identification|\s*number|\s*#)"): "tax_id_number",
            re.compile(r"employer\s*identification\s*number"): "ein",
            re.compile(r"date\s*of\s*birth"): "birth_date",
            re.compile(r"birth\s*date"): "birth_date",
            re.compile(r"(zip|postal)(\s*code)?"): "postal_code",
            re.compile(r"street\s*address"): "street_address",
            re.compile(r"address\s*(line)?\s*1"): "address_line1",
            re.compile(r"address\s*(line)?\s*2"): "address_line2",
            re.compile(r"(city|town)"): "city",
            re.compile(r"(state|province|territory)"): "state_province",
            re.compile(r"county"): "county",
            re.compile(r"country"): "country",
            re.compile(r"signature"): "signature",
            re.compile(r"date\s*signed"): "signature_date",
            re.compile(r"parent.*signature", re.IGNORECASE): "parent_signature",
            re.compile(r"employee\s*name"): "employee_name",
            re.compile(r"employee\s*id"): "employee_id",
            re.compile(r"employee\s*number"): "employee_id",
            re.compile(r"employer\s*name"): "employer_name",
            re.compile(r"company\s*name"): "company_name",
            re.compile(r"department"): "department",
            re.compile(r"job\s*title"): "job_title",
            re.compile(r"position"): "job_title",
            re.compile(r"salary"): "salary",
            re.compile(r"hire\s*date"): "hire_date",
            re.compile(r"termination\s*date"): "termination_date",
            re.compile(r"effective\s*date"): "effective_date",
            re.compile(r"payment\s*date"): "payment_date",
            re.compile(r"gender"): "gender",
            re.compile(r"marital\s*status"): "marital_status",
        }

        # Check if this is a common field pattern
        for pattern, replacement in common_fields.items():
            if pattern.search(label_lower):
                return replacement

        # Handle yes/no questions by focusing on the subject
        if re.search(
            r"^(are|is|do|does|did|have|has|can|could|would|will|should)\s", label_lower
        ):
            # Extract the meaningful part after question words
            question_match = re.search(
                r"^(?:are|is|do|does|did|have|has|can|could|would|will|should)\s+(.*?)(?:\?|\.|$)",
                label_lower,
            )
            if question_match:
                subject = question_match.group(1).strip()
                # Process the subject of the question
                subject_name = re.sub(r"[^\w\s]", "", subject).strip()
                subject_name = re.sub(r"\s+", "_", subject_name)

                # Remove pronouns and common words that don't add meaning
                subject_name = re.sub(
                    r"^(you|your|this|that|these|those|it|its|they|their|there|here)_",
                    "",
                    subject_name,
                )

                # Remove articles and prepositions that don't add meaning
                subject_name = re.sub(
                    r"^(a|an|the|to|for|in|on|at|by|with|from|of|about)_",
                    "",
                    subject_name,
                )

                # Handle common question patterns
                if "eligible" in subject_name or "qualify" in subject_name:
                    subject_name = re.sub(
                        r"_eligible_for_|_qualify_for_", "_eligibility_", subject_name
                    )

                if "currently" in subject_name:
                    subject_name = subject_name.replace("currently_", "")

                # If it's a yes/no question about approval, authorization, etc.
                if any(
                    word in subject_name
                    for word in ["approved", "authorized", "permitted", "allowed"]
                ):
                    subject_name = re.sub(
                        r"_(approved|authorized|permitted|allowed)$",
                        "_approval",
                        subject_name,
                    )

                if subject_name:
                    return f"{subject_name}_flag"

        # Normal processing for non-question labels
        # Remove special characters and convert to lowercase
        name = re.sub(r"[^\w\s]", "", label).lower()

        # Replace whitespace with underscores
        name = re.sub(r"\s+", "_", name)

        # Remove common articles and prepositions at the beginning
        name = re.sub(
            r"^(a|an|the|this|that|these|those|of|for|to|in|on|at|by|with|from|about)_",
            "",
            name,
        )

        # Remove common instructions like "enter", "provide", "select", etc.
        name = re.sub(
            r"^(enter|type|provide|input|specify|select|choose|indicate|list|give|write|insert|put|fill|click|check|tick)_",
            "",
            name,
        )

        # Remove common instructional suffixes
        name = re.sub(
            r"_(here|below|above|box|field)$",
            "",
            name,
        )

        # Handle common label formats like "Employee Name:" by creating standardized field names
        parts = name.split("_")
        if len(parts) >= 2:
            # If last word is a field type indicator, consider it carefully
            if parts[-1] in [
                "name",
                "address",
                "number",
                "date",
                "code",
                "amount",
                "total",
                "id",
                "email",
                "phone",
                "fax",
                "signature",
                "ssn",
                "title",
                "status",
            ]:
                # For common descriptive patterns like "employee_name", keep as is
                # because it's already a good descriptive name
                if parts[0] in [
                    "employee",
                    "employer",
                    "customer",
                    "client",
                    "vendor",
                    "patient",
                    "doctor",
                    "student",
                    "teacher",
                    "manager",
                    "supervisor",
                    "applicant",
                    "recipient",
                    "beneficiary",
                    "dependent",
                    "spouse",
                    "parent",
                    "child",
                    "contact",
                    "emergency",
                    "primary",
                    "secondary",
                    "billing",
                    "shipping",
                ]:
                    # Leave name as is - it's already descriptive
                    pass
                # For other cases, consider reversing to emphasize the type of field
                elif len(parts) >= 3 and parts[-1] in [
                    "date",
                    "amount",
                    "total",
                    "number",
                ]:
                    name = f"{parts[-1]}_of_{('_').join(parts[:-1])}"

        # Shorten very long names but try to preserve meaning and ensure they're still unique
        if len(name) > 60:
            words = name.split("_")

            # Try to keep the most meaningful parts
            important_words = [
                word
                for word in words
                if len(word) > 3
                and word
                not in [
                    "the",
                    "and",
                    "for",
                    "with",
                    "that",
                    "this",
                    "from",
                    "your",
                    "please",
                    "enter",
                    "select",
                    "choose",
                    "provide",
                ]
            ]

            # If we have enough important words, use those
            if len(important_words) >= 3:
                words = important_words[:6]
            else:
                # Otherwise, just take the first 6 words
                words = words[:6]

            name = "_".join(words)

        # Make sure the name doesn't start with a number
        if re.match(r"^\d", name):
            name = f"field_{name}"

        return name

    def _get_context_from_path(self, path: str) -> str:
        """Extract meaningful context from a path"""
        # Skip common non-semantic paths
        if path in ["ListOfDtFormInstanceLw", "page1", "Top", "form1"]:
            return ""

        # Convert camelCase to snake_case
        path_parts = re.findall(r"[A-Z][a-z]*|[a-z]+", path)
        if not path_parts:
            return ""

        # Filter out common non-semantic parts
        filtered_parts = [
            part.lower()
            for part in path_parts
            if part.lower()
            not in [
                "list",
                "of",
                "dt",
                "form",
                "instance",
                "lw",
                "page",
                "section",
                "subform",
                "top",
            ]
        ]

        if not filtered_parts:
            return ""

        return "_".join(filtered_parts)


class PDFFormExtractor:
    """Extract form fields from a PDF file"""

    def __init__(self, pdf_file_path: str):
        self.pdf_file_path = pdf_file_path
        self.next_id = 1
        self.form_id = os.path.basename(pdf_file_path).split(".")[0]
        self.field_names = set()
        # Track processed field labels to avoid duplication and maintain consistency
        self.processed_labels = {}
        # Store standardized names for consistent naming across different forms
        self.standardized_fields = {}
        self.field_context = {}

        # Patterns to identify generic field names
        self.generic_field_patterns = {
            "text-info": re.compile(
                r"^(TextField|Text|Input|String|Field|txt|entry|value|content)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "text-input": re.compile(
                r"^(TextField|Text|Input|String|Field|txt|entry|value|content)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "checkbox": re.compile(
                r"^(CheckBox|Check|chk|toggle|flag|indicator)\d*(_\d+)?$", re.IGNORECASE
            ),
            "radio": re.compile(
                r"^(Radio|RadioButton|option|choice|select)\d*(_\d+)?$", re.IGNORECASE
            ),
            "dropdown": re.compile(
                r"^(DropDown|Select|Choice|ComboBox|list|menu|options)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "date": re.compile(
                r"^(Date|DateField|DateTime|calendar|day|time)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "numeric": re.compile(
                r"^(NumericField|Number|Integer|Float|Decimal|amount|sum|total|count)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "signature": re.compile(
                r"^(SignField|Signature|Sign|esign|autograph)\d*(_\d+)?$", re.IGNORECASE
            ),
            "address": re.compile(
                r"^(Address|AddressField|location|place|residence)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
            "comment": re.compile(
                r"^(Comment|Comments|CommentField|note|feedback|message)\d*(_\d+)?$",
                re.IGNORECASE,
            ),
        }

        try:
            self.pdf = pypdf.PdfReader(pdf_file_path)
        except Exception as e:
            logger.error(f"Error reading PDF file: {e}")
            raise

    def get_next_id(self) -> str:
        """Get the next unique ID"""
        current_id = str(self.next_id)
        self.next_id += 1
        return current_id

    def determine_field_type(self, field_type: str) -> str:
        """Map PDF field types to our consistent field types"""
        type_mapping = {
            "/Tx": "text-input",
            "/Btn": "checkbox",  # May also be a button or radio
            "/Ch": "dropdown",
            "/Sig": "signature",
        }
        return type_mapping.get(field_type, "unknown")

    def extract_field_options(self, field) -> List[str]:
        """Extract options for dropdowns and radio buttons"""
        options = []
        if field.field_type == "/Ch" and hasattr(field, "/Opt"):
            options = field["/Opt"]
        return options

    def extract_field_value(self, field) -> Any:
        """Extract the current value of a field"""
        if hasattr(field, "value"):
            return field.value
        return None

    def is_generic_field_name(self, name: str, field_type: str) -> bool:
        """Check if a field name is generic"""
        # Check if it matches generic patterns like "TextField1" or "Checkbox_123"
        for type_name, pattern in self.generic_field_patterns.items():
            if pattern.match(name):
                return True

        # Check for completely numeric names
        if name.isdigit():
            return True

        # Check for common generic patterns
        generic_patterns = [
            re.compile(r"^field\d*(_\d+)?$", re.IGNORECASE),
            re.compile(r"^[a-z]+\d+$", re.IGNORECASE),  # Like "text1", "input2"
            re.compile(r"^[a-z]+_\d+$", re.IGNORECASE),  # Like "text_1", "input_2"
        ]

        for pattern in generic_patterns:
            if pattern.match(name):
                return True

        return False

    def generate_semantic_field_name(
        self,
        original_name: str,
        field_type: str,
        label: str = "",
        parent_path: str = "",
    ) -> str:
        """
        Generate a semantic field name based on label, type and context.

        This method prioritizes descriptive names derived from labels over generic names,
        and ensures that the resulting field name is human-readable and meaningful.
        """
        # If the original name is good (not generic and descriptive), keep it
        if original_name and not self.is_generic_field_name(original_name, field_type):
            return original_name

        # If we have a label, prioritize using that to generate a name (preferred approach)
        if label:
            # Clean up the label before converting to field name
            # Remove question marks and other punctuation that shouldn't be in a field name
            clean_label = re.sub(r"\?+$", "", label)
            clean_label = clean_label.strip()

            # Convert label to snake_case but preserve meaningful words
            name = self._label_to_field_name(clean_label)

            # Don't truncate unnecessarily - keep full descriptive names
            # Only shorten if extremely long (over 80 chars)
            if len(name) > 80:
                words = name.split("_")
                name = "_".join(words[:8])  # Keep first 8 words instead of just 5

            # Add field type suffix for clarity if needed and not already present
            if field_type == "checkbox" and not any(
                name.endswith(suffix)
                for suffix in [
                    "_is",
                    "_has",
                    "_flag",
                    "_indicator",
                    "_selected",
                    "_checked",
                ]
            ):
                name = f"{name}_flag"
            elif field_type == "date" and not any(
                name.endswith(suffix)
                for suffix in ["_date", "_time", "_day", "_month", "_year"]
            ):
                name = f"{name}_date"
            elif field_type == "numeric" and not any(
                name.endswith(suffix)
                for suffix in [
                    "_amount",
                    "_number",
                    "_count",
                    "_total",
                    "_quantity",
                    "_sum",
                    "_value",
                ]
            ):
                name = f"{name}_amount"
            elif field_type == "dropdown" and not any(
                name.endswith(suffix)
                for suffix in ["_select", "_choice", "_option", "_list"]
            ):
                name = f"{name}_selection"

            # Add context from parent if available and meaningful
            if parent_path and parent_path not in ["form1", "page1", "Root"]:
                parent_context = (
                    parent_path.split(".")[-1] if "." in parent_path else parent_path
                )
                # Only add parent context if it's not already in the name and adds meaning
                if parent_context and parent_context not in name:
                    # Check if parent context is meaningful enough to include
                    if len(parent_context) > 2 and not parent_context.isdigit():
                        name = f"{parent_context}_{name}"

            return name

        # If we don't have a label but have a name, try to make it more semantic
        if original_name:
            # Extract meaningful parts from camelCase, PascalCase or snake_case
            words = re.findall(r"[A-Z][a-z]+|[a-z]+|\d+", original_name)
            if words:
                # Filter out numeric identifiers and common generic prefixes/suffixes
                words = [
                    w
                    for w in words
                    if not (
                        w.isdigit()
                        or w.lower()
                        in [
                            "field",
                            "text",
                            "input",
                            "check",
                            "box",
                            "button",
                            "form",
                            "the",
                            "a",
                            "an",
                        ]
                    )
                ]

                if words:
                    # Create name from remaining meaningful parts
                    name = "_".join(w.lower() for w in words)

                    # Add type suffix if needed
                    if field_type == "checkbox" and not any(
                        name.endswith(suffix)
                        for suffix in [
                            "_is",
                            "_has",
                            "_flag",
                            "_indicator",
                            "_selected",
                            "_checked",
                        ]
                    ):
                        name = f"{name}_flag"
                    elif field_type == "date" and not any(
                        name.endswith(suffix)
                        for suffix in ["_date", "_time", "_day", "_month", "_year"]
                    ):
                        name = f"{name}_date"
                    elif field_type == "numeric" and not any(
                        name.endswith(suffix)
                        for suffix in [
                            "_amount",
                            "_number",
                            "_count",
                            "_total",
                            "_quantity",
                        ]
                    ):
                        name = f"{name}_amount"
                    elif field_type == "dropdown" and not any(
                        name.endswith(suffix)
                        for suffix in ["_select", "_choice", "_option", "_list"]
                    ):
                        name = f"{name}_selection"

                    return name

        # Last resort: generate a more descriptive generic name using field type and context
        type_prefix = field_type.replace("-", "_")

        # Try to get meaningful context from the parent path
        if parent_path:
            parent_context = (
                parent_path.split(".")[-1] if "." in parent_path else parent_path
            )

            # Only use parent context if it's meaningful
            if (
                parent_context
                and len(parent_context) > 2
                and not parent_context.isdigit()
            ):
                # Create descriptive name using parent context
                return f"{parent_context}_{type_prefix}"

        # Create a unique type-based name as last resort
        return f"{type_prefix}"

    def _label_to_field_name(self, label: str) -> str:
        """
        Convert a label to a semantic, descriptive snake_case field name.

        This enhanced version creates more meaningful field names by:
        1. Preserving the most descriptive words
        2. Intelligently handling questions and instructions
        3. Recognizing common field name patterns and standardizing them
        """
        if not label:
            return ""

        # Standardize common label patterns first
        label_lower = label.lower()

        # Map common field labels to standard names
        common_fields = {
            re.compile(r"first\s*name"): "first_name",
            re.compile(r"last\s*name"): "last_name",
            re.compile(r"full\s*name"): "full_name",
            re.compile(r"middle\s*(name|initial)"): "middle_name",
            re.compile(r"(email|e-mail)(\s*address)?"): "email_address",
            re.compile(r"phone\s*(number|no\.?)"): "phone_number",
            re.compile(r"cell\s*(phone|number)"): "mobile_number",
            re.compile(r"mobile\s*(phone|number)"): "mobile_number",
            re.compile(r"work\s*(phone|number)"): "work_phone",
            re.compile(r"home\s*(phone|number)"): "home_phone",
            re.compile(r"fax(\s*number)?"): "fax_number",
            re.compile(r"social\s*security(\s*number|\s*no\.?|\s*#)"): "ssn",
            re.compile(r"tax(\s*id|\s*identification|\s*number|\s*#)"): "tax_id_number",
            re.compile(r"employer\s*identification\s*number"): "ein",
            re.compile(r"date\s*of\s*birth"): "birth_date",
            re.compile(r"birth\s*date"): "birth_date",
            re.compile(r"(zip|postal)(\s*code)?"): "postal_code",
            re.compile(r"street\s*address"): "street_address",
            re.compile(r"address\s*(line)?\s*1"): "address_line1",
            re.compile(r"address\s*(line)?\s*2"): "address_line2",
            re.compile(r"(city|town)"): "city",
            re.compile(r"(state|province|territory)"): "state_province",
            re.compile(r"county"): "county",
            re.compile(r"country"): "country",
            re.compile(r"signature"): "signature",
            re.compile(r"date\s*signed"): "signature_date",
            re.compile(r"parent.*signature", re.IGNORECASE): "parent_signature",
            re.compile(r"employee\s*name"): "employee_name",
            re.compile(r"employee\s*id"): "employee_id",
            re.compile(r"employee\s*number"): "employee_id",
            re.compile(r"employer\s*name"): "employer_name",
            re.compile(r"company\s*name"): "company_name",
            re.compile(r"department"): "department",
            re.compile(r"job\s*title"): "job_title",
            re.compile(r"position"): "job_title",
            re.compile(r"salary"): "salary",
            re.compile(r"hire\s*date"): "hire_date",
            re.compile(r"termination\s*date"): "termination_date",
            re.compile(r"effective\s*date"): "effective_date",
            re.compile(r"payment\s*date"): "payment_date",
            re.compile(r"gender"): "gender",
            re.compile(r"marital\s*status"): "marital_status",
        }

        # Check if this is a common field pattern
        for pattern, replacement in common_fields.items():
            if pattern.search(label_lower):
                return replacement

        # Handle yes/no questions by focusing on the subject
        if re.search(
            r"^(are|is|do|does|did|have|has|can|could|would|will|should)\s", label_lower
        ):
            # Extract the meaningful part after question words
            question_match = re.search(
                r"^(?:are|is|do|does|did|have|has|can|could|would|will|should)\s+(.*?)(?:\?|\.|$)",
                label_lower,
            )
            if question_match:
                subject = question_match.group(1).strip()
                # Process the subject of the question
                subject_name = re.sub(r"[^\w\s]", "", subject).strip()
                subject_name = re.sub(r"\s+", "_", subject_name)

                # Remove pronouns and common words that don't add meaning
                subject_name = re.sub(
                    r"^(you|your|this|that|these|those|it|its|they|their|there|here)_",
                    "",
                    subject_name,
                )

                # Remove articles and prepositions that don't add meaning
                subject_name = re.sub(
                    r"^(a|an|the|to|for|in|on|at|by|with|from|of|about)_",
                    "",
                    subject_name,
                )

                # Handle common question patterns
                if "eligible" in subject_name or "qualify" in subject_name:
                    subject_name = re.sub(
                        r"_eligible_for_|_qualify_for_", "_eligibility_", subject_name
                    )

                if "currently" in subject_name:
                    subject_name = subject_name.replace("currently_", "")

                # If it's a yes/no question about approval, authorization, etc.
                if any(
                    word in subject_name
                    for word in ["approved", "authorized", "permitted", "allowed"]
                ):
                    subject_name = re.sub(
                        r"_(approved|authorized|permitted|allowed)$",
                        "_approval",
                        subject_name,
                    )

                if subject_name:
                    return f"{subject_name}_flag"

        # Normal processing for non-question labels
        # Remove special characters and convert to lowercase
        name = re.sub(r"[^\w\s]", "", label).lower()

        # Replace whitespace with underscores
        name = re.sub(r"\s+", "_", name)

        # Remove common articles and prepositions at the beginning
        name = re.sub(
            r"^(a|an|the|this|that|these|those|of|for|to|in|on|at|by|with|from|about)_",
            "",
            name,
        )

        # Remove common instructions like "enter", "provide", "select", etc.
        name = re.sub(
            r"^(enter|type|provide|input|specify|select|choose|indicate|list|give|write|insert|put|fill|click|check|tick)_",
            "",
            name,
        )

        # Remove common instructional suffixes
        name = re.sub(
            r"_(here|below|above|box|field)$",
            "",
            name,
        )

        # Handle common label formats like "Employee Name:" by creating standardized field names
        parts = name.split("_")
        if len(parts) >= 2:
            # If last word is a field type indicator, consider it carefully
            if parts[-1] in [
                "name",
                "address",
                "number",
                "date",
                "code",
                "amount",
                "total",
                "id",
                "email",
                "phone",
                "fax",
                "signature",
                "ssn",
                "title",
                "status",
            ]:
                # For common descriptive patterns like "employee_name", keep as is
                # because it's already a good descriptive name
                if parts[0] in [
                    "employee",
                    "employer",
                    "customer",
                    "client",
                    "vendor",
                    "patient",
                    "doctor",
                    "student",
                    "teacher",
                    "manager",
                    "supervisor",
                    "applicant",
                    "recipient",
                    "beneficiary",
                    "dependent",
                    "spouse",
                    "parent",
                    "child",
                    "contact",
                    "emergency",
                    "primary",
                    "secondary",
                    "billing",
                    "shipping",
                ]:
                    # Leave name as is - it's already descriptive
                    pass
                # For other cases, consider reversing to emphasize the type of field
                elif len(parts) >= 3 and parts[-1] in [
                    "date",
                    "amount",
                    "total",
                    "number",
                ]:
                    name = f"{parts[-1]}_of_{('_').join(parts[:-1])}"

        # Shorten very long names but try to preserve meaning and ensure they're still unique
        if len(name) > 60:
            words = name.split("_")

            # Try to keep the most meaningful parts
            important_words = [
                word
                for word in words
                if len(word) > 3
                and word
                not in [
                    "the",
                    "and",
                    "for",
                    "with",
                    "that",
                    "this",
                    "from",
                    "your",
                    "please",
                    "enter",
                    "select",
                    "choose",
                    "provide",
                ]
            ]

            # If we have enough important words, use those
            if len(important_words) >= 3:
                words = important_words[:6]
            else:
                # Otherwise, just take the first 6 words
                words = words[:6]

            name = "_".join(words)

        # Make sure the name doesn't start with a number
        if re.match(r"^\d", name):
            name = f"field_{name}"

        return name

    def extract(self) -> Dict[str, Any]:
        """Extract all form fields from the PDF"""
        fields = []

        # If there are no form fields, return empty result
        pdf_fields = self.pdf.get_fields()
        if not pdf_fields:
            logger.warning(f"No form fields found in PDF: {self.pdf_file_path}")
            return {
                "form_id": self.form_id,
                "extraction_date": datetime.now().isoformat(),
                "source_file": os.path.basename(self.pdf_file_path),
                "format": "pdf",
                "fields": [],
            }

        # Group fields by hierarchy using their names
        field_hierarchy = defaultdict(list)

        for field_name, field in pdf_fields.items():
            parts = field_name.split(".")

            # Set parent name or empty if no parent
            parent_name = ".".join(parts[:-1]) if len(parts) > 1 else ""

            # Determine field type
            field_type = self.determine_field_type(field.field_type)

            # Use last part of the name as a label if it looks like a label
            original_name = parts[-1]
            field_label = original_name

            # Generate semantic field name
            semantic_name = self.generate_semantic_field_name(
                original_name, field_type, field_label, parent_name
            )

            # Ensure uniqueness
            if semantic_name in self.field_names:
                semantic_name = f"{semantic_name}_{self.get_next_id()}"
            self.field_names.add(semantic_name)

            # Create field object
            field_obj = StructuredFormField(
                field_id=self.get_next_id(),
                field_name=semantic_name,
                field_type=field_type,
                label=field_label,
            )

            # Extract options and value
            field_obj.options = self.extract_field_options(field)
            field_obj.value = self.extract_field_value(field)

            # Store in hierarchy
            field_hierarchy[parent_name].append(field_obj)

        # Build the field hierarchy
        for parent_name, child_fields in field_hierarchy.items():
            if not parent_name:  # Root level fields
                fields.extend(child_fields)
            else:
                # Find parent field
                for field_list in field_hierarchy.values():
                    for field in field_list:
                        if field.name == parent_name.split(".")[-1]:
                            field.children.extend(child_fields)
                            for child in child_fields:
                                child.parent = field

        # Create the result object
        result = {
            "form_id": self.form_id,
            "extraction_date": datetime.now().isoformat(),
            "source_file": os.path.basename(self.pdf_file_path),
            "format": "pdf",
            "fields": self._fields_to_dict(fields),
        }

        return result

    def _fields_to_dict(self, fields):
        """Convert FormField objects to dictionaries for serialization"""
        result = []
        for field in fields:
            field_dict = {
                "id": field.id,
                "name": field.name,
                "type": field.type,
            }

            if field.label:
                field_dict["label"] = field.label

            if field.value is not None:
                field_dict["value"] = field.value

            if field.binding_ref:
                field_dict["binding_ref"] = field.binding_ref

            if field.help_text:
                field_dict["help_text"] = field.help_text

            if field.validation:
                field_dict["validation"] = field.validation

            if field.javascript:
                field_dict["javascript"] = field.javascript

            if field.options:
                field_dict["options"] = field.options

            if field.is_repeating:
                field_dict["is_repeating"] = True
                if field.max_items:
                    field_dict["max_items"] = field.max_items
                if field.min_items:
                    field_dict["min_items"] = field.min_items

            if field.presence != "visible":
                field_dict["presence"] = field.presence

            if field.children:
                field_dict["children"] = self._fields_to_dict(field.children)

            # Add any additional properties
            for key, value in field.additional_properties.items():
                field_dict[key] = value

            result.append(field_dict)

        return result


class FormAnalyzer:
    """
    Analyze extracted form fields to identify patterns, group fields,
    and provide insights about the form structure.
    """

    def __init__(self, extracted_data: Dict[str, Any]):
        self.data = extracted_data
        self.form_id = extracted_data.get("form_id", "unknown")
        self.fields_flat = []
        self.flatten_fields(extracted_data.get("fields", []))

    def flatten_fields(self, fields: List[Dict[str, Any]], parent_path: str = ""):
        """Flatten nested fields structure for analysis"""
        for field in fields:
            path = f"{parent_path}.{field['name']}" if parent_path else field["name"]
            flat_field = field.copy()
            flat_field["path"] = path

            # Remove children to avoid redundancy
            children = (
                flat_field.pop("children", []) if "children" in flat_field else []
            )

            # Add to flat list
            self.fields_flat.append(flat_field)

            # Process children
            if children:
                self.flatten_fields(children, path)

    def get_field_types_summary(self) -> Dict[str, int]:
        """Get summary of field types in the form"""
        result = defaultdict(int)
        for field in self.fields_flat:
            result[field.get("type", "unknown")] += 1
        return dict(result)

    def get_binding_summary(self) -> Dict[str, List[str]]:
        """Get summary of data bindings in the form"""
        result = defaultdict(list)
        for field in self.fields_flat:
            if "binding_ref" in field:
                binding = field["binding_ref"]
                result[binding].append(field["path"])
        return dict(result)

    def get_repeating_sections(self) -> List[Dict[str, Any]]:
        """Identify repeating sections in the form"""
        result = []
        for field in self.fields_flat:
            if field.get("is_repeating", False):
                result.append(
                    {
                        "name": field["name"],
                        "path": field["path"],
                        "min_items": field.get("min_items", 1),
                        "max_items": field.get("max_items", None),
                        "child_fields": len(
                            [
                                f
                                for f in self.fields_flat
                                if f["path"].startswith(field["path"] + ".")
                            ]
                        ),
                    }
                )
        return result

    def analyze(self) -> Dict[str, Any]:
        """Perform complete analysis of the form structure"""
        return {
            "form_id": self.form_id,
            "total_fields": len(self.fields_flat),
            "field_types": self.get_field_types_summary(),
            "data_bindings": self.get_binding_summary(),
            "repeating_sections": self.get_repeating_sections(),
            "analysis_date": datetime.now().isoformat(),
        }


def convert_to_structured_format(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert extracted form data to structured format using helper.py logic"""
    logger.info("Converting extracted form data to structured format")

    from helper import dict_to_form_field

    form_id = extracted_data.get("form_id", "unknown")

    # Process each field
    structured_fields = []
    for field_dict in extracted_data.get("fields", []):
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


def extract_form_fields(input_file: str, output_dir: str):
    """Extract form fields from either XDP or PDF file and convert to structured format"""
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for templates and working files
    templates_dir = output_dir_path / "templates"
    working_files_dir = output_dir_path / "working-files"
    templates_dir.mkdir(parents=True, exist_ok=True)
    working_files_dir.mkdir(parents=True, exist_ok=True)

    input_file_path = Path(input_file)
    if not input_file_path.exists():
        logger.error(f"Input file not found: {input_file}")
        return False

    # Determine file type and use appropriate extractor
    file_extension = input_file_path.suffix.lower()

    if file_extension == ".xdp":
        logger.info(f"Processing XDP file: {input_file}")
        extractor = XDPFormExtractor(str(input_file_path))
    elif file_extension == ".pdf":
        logger.info(f"Processing PDF file: {input_file}")
        extractor = PDFFormExtractor(str(input_file_path))
    else:
        logger.error(f"Unsupported file type: {file_extension}")
        return False

    # Extract form fields
    try:
        extracted_data = extractor.extract()
    except Exception as e:
        logger.error(f"Error extracting form fields: {e}")
        return False

    # Generate output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = input_file_path.stem
    form_id = extracted_data.get("form_id", base_name)

    # Generate intermediate output file (original format) in working-files directory
    intermediate_file = working_files_dir / f"{base_name}_fields_{timestamp}.json"

    # Write extracted data to intermediate file
    try:
        with open(intermediate_file, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=2)
        logger.info(f"Original form fields extracted to {intermediate_file}")
    except Exception as e:
        logger.error(f"Error writing intermediate file: {e}")
        return False

    # Convert to structured format
    try:
        # Convert the extracted data to the structured format
        structured_result = convert_to_structured_format(extracted_data)

        # Write structured output to file in templates directory
        structured_output_file = (
            templates_dir / f"{base_name}-form-template-v.2.0_{timestamp}.json"
        )
        with open(structured_output_file, "w", encoding="utf-8") as f:
            json.dump(structured_result, f, indent=2)
        logger.info(f"Structured form template written to {structured_output_file}")

    except Exception as e:
        logger.error(f"Error creating structured output: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return False

    # Analyze extracted data
    try:
        analyzer = FormAnalyzer(extracted_data)
        analysis = analyzer.analyze()

        # Write analysis to file in working-files directory
        analysis_file = working_files_dir / f"{base_name}_analysis_{timestamp}.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Form analysis written to {analysis_file}")
    except Exception as e:
        logger.error(f"Error analyzing form: {e}")

    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Extract form fields from XDP and PDF files"
    )
    parser.add_argument(
        "--input-file", required=True, help="Path to the input XDP or PDF file"
    )
    parser.add_argument(
        "--output-dir", default="./output", help="Directory for output files"
    )

    args = parser.parse_args()

    return extract_form_fields(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
