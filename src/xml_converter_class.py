import xml.etree.ElementTree as ET
import json
import os
import uuid
from datetime import datetime
from src.report import Report

class XDPParser:
    def __init__(self, xml_filename, mapping_file=None):
        try:
            self.xml_filename = xml_filename
            
            # Dynamically resolve the mapping file path if not provided
            if mapping_file is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the current script's directory
                project_root = os.path.abspath(os.path.join(script_dir, ".."))  # Move up to project root
                mapping_file = os.path.join(project_root, "xml_mapping.json")  # Construct full path

            self.mapping_file = mapping_file
            self.breadcrumb = ""
            self.id_counter = 1
            self.mapping = self.load_mapping_file()
            self.namespaces = None
            self.javascript_section = {}  # Store JavaScript methods

            # Parse the XML file
            self.tree = ET.parse(xml_filename)
            self.root = self.tree.getroot()
            self.namespaces = self.extract_namespaces()

            # Find the root subform
            self.root_subform = self.root.find(".//template:subform", self.namespaces)

            # Output JSON structure
            self.output_json = self.create_output_structure()
            self.all_items = []
            self.Report = Report(xml_filename)
        except Exception as e:
            print(f"Error initializing XDPParser: {e}")
            raise
    
    def load_mapping_file(self):
        try:
            """Load field mapping configuration"""
            if not os.path.exists(self.mapping_file):
                raise FileNotFoundError(f"Mapping file {self.mapping_file} not found")
            
            with open(self.mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading mapping file: {e}")
            return None
    
    def extract_namespaces(self):
        try:
            """Extract namespace mappings from XML document"""
            namespaces = {}
            
            for elem in self.root.iter():
                if '}' in elem.tag:
                    uri = elem.tag.split('}')[0].strip('{')
                    for attr_name in elem.attrib:
                        if '}' in attr_name:
                            prefix = attr_name.split('}')[1].split(':')[0]
                            namespaces[prefix] = uri
                            break
                    else:
                        if 'adobe.com/xdp' in uri:
                            namespaces['xdp'] = uri
                        elif 'xfa-template' in uri:
                            namespaces['template'] = uri
            
            # Return default namespaces if none found
            if not namespaces:
                namespaces = {
                    'xdp': 'http://ns.adobe.com/xdp/',
                    'template': 'http://www.xfa.org/schema/xfa-template/3.0/'
                }
                
            return namespaces
        except Exception as e:
            print(f"Error extracting namespaces Using default Namespaces: {e}")
            namespaces = {
                'xdp': 'http://ns.adobe.com/xdp/',
                'template': 'http://www.xfa.org/schema/xfa-template/3.0/'
            }
            return namespaces
    
    def add_breadcrumb(self, tag, element=None):
        try:
            """Add element tag and attributes to breadcrumb path"""
            # Add basic tag
            tag_with_attrs = f"<{tag}"
            
            # Add relevant attributes if element is provided
            if element is not None and hasattr(element, 'attrib'):
                for key, value in element.attrib.items():
                    # Only include certain relevant attributes
                    if key in ['name', 'type', 'ref', 'shape', 'contentType']:
                        # Remove namespace prefix from attribute if present
                        key = key.split("}")[-1] if "}" in key else key
                        tag_with_attrs += f" {key}=\"{value}\""
            
            tag_with_attrs += ">"
            self.breadcrumb += tag_with_attrs
            
            # Keep breadcrumb from growing too large
            if len(self.breadcrumb) > 200:
                # Keep only the last 200 characters but ensure we don't break in middle of a tag
                truncated = self.breadcrumb[-200:]
                # Find first complete opening tag
                first_tag = truncated.find("<")
                if first_tag >= 0:
                    self.breadcrumb = truncated[first_tag:]
        except Exception as e:
            print(f"Error adding breadcrumb: {e}")
    
    def remove_breadcrumb(self, tag):
        try:
            """Remove the last element tag from breadcrumb"""
            # Find the last occurrence of a tag that starts with the given name
            last_index = -1
            tag_start = f"<{tag}"
            
            # Look for the tag with any attributes
            i = self.breadcrumb.rfind(tag_start)
            while i >= 0:
                tag_end = self.breadcrumb.find(">", i)
                if tag_end >= 0:
                    last_index = i
                    break
                i = self.breadcrumb.rfind(tag_start, 0, i)
            
            if last_index >= 0:
                self.breadcrumb = self.breadcrumb[:last_index]
        except Exception as e:
            print(f"Error removing breadcrumb: {e}")
    
    def get_breadcrumb(self):
        try:
            """Get current normalized breadcrumb path"""
            return self.normalize_path(self.breadcrumb)
        except Exception as e:
            print(f"Error getting breadcrumb: {e}")
            return ""
    
    def next_id(self):
        try:
            """Get next unique ID and increment counter"""
            current_id = str(self.id_counter)
            self.id_counter += 1
            return current_id
        except Exception as e:
            print(f"Error generating next ID: {e}")
            return str(uuid.uuid4())
    
    def normalize_path(self, path):
        """Normalize an XML path for comparison by removing extra spaces and normalizing separators"""
        try:
            # Remove extra whitespace
            path = " ".join(path.split())
            # Normalize separators to single angle brackets
            path = path.replace("//", "/")
            path = path.replace("><", ">/<")
            # Remove any leading/trailing separators
            path = path.strip("/<>")
            return path
        except Exception as e:
            print(f"Error normalizing path: {e}")
            return path

    def path_similarity(self, path1, path2):
        """Calculate similarity between two XML paths with improved hierarchy handling"""
        try:
            # Normalize both paths
            path1 = self.normalize_path(path1)
            path2 = self.normalize_path(path2)
            
            # Split paths into components
            parts1 = path1.split("/")
            parts2 = path2.split("/")
            
            # Calculate matching score with position weighting
            matches = 0
            total_weight = 0
            max_length = max(len(parts1), len(parts2))
            
            # Compare each part with position-based weighting
            for i in range(min(len(parts1), len(parts2))):
                # Calculate position weight (later positions matter more)
                position_weight = 1 + (i / max_length)
                total_weight += position_weight
                
                # Extract tag and attributes
                tag1, attrs1 = self.split_tag_and_attrs(parts1[i])
                tag2, attrs2 = self.split_tag_and_attrs(parts2[i])
                
                # Compare tags
                if tag1 == tag2:
                    matches += position_weight
                elif tag1.replace("template:", "") == tag2.replace("template:", ""):
                    # Match without namespace
                    matches += 0.9 * position_weight
                elif tag1.split("[")[0] == tag2.split("[")[0]:
                    # Match ignoring predicates
                    matches += 0.8 * position_weight
                
                # Compare attributes if both have them
                if attrs1 and attrs2:
                    attr_match = self.compare_attributes(attrs1, attrs2)
                    matches += 0.2 * position_weight * attr_match
            
            # Calculate final score
            return matches / (total_weight if total_weight > 0 else 1)
        except Exception as e:
            print(f"Error calculating path similarity: {e}")
            return 0

    def split_tag_and_attrs(self, part):
        """Split a path component into tag and attributes"""
        try:
            if " " not in part:
                return part, {}
            
            tag = part.split(" ")[0]
            attrs = {}
            
            # Extract attributes
            for attr in part.split(" ")[1:]:
                if "=" in attr:
                    key, value = attr.split("=", 1)
                    attrs[key] = value.strip('"\'')
            
            return tag, attrs
        except Exception as e:
            print(f"Error splitting tag and attributes: {e}")
            return part, {}

    def compare_attributes(self, attrs1, attrs2):
        """Compare two sets of attributes and return a similarity score"""
        try:
            if not attrs1 or not attrs2:
                return 0
            
            # Get all unique keys
            all_keys = set(attrs1.keys()) | set(attrs2.keys())
            if not all_keys:
                return 0
            
            matches = 0
            for key in all_keys:
                if key in attrs1 and key in attrs2:
                    if attrs1[key] == attrs2[key]:
                        matches += 1
                    elif attrs1[key].lower() == attrs2[key].lower():
                        matches += 0.9
            
            return matches / len(all_keys)
        except Exception as e:
            print(f"Error comparing attributes: {e}")
            return 0

    def find_mapping_for_path(self, path):
        """Find mapping configuration for given path using fuzzy matching"""
        try:
            best_match = None
            best_score = 0.7  # Minimum similarity threshold
            
            for mapping in self.mapping.get("mappings", []):
                xml_path = mapping.get("xmlPath", "")
                score = self.path_similarity(path, xml_path)
                
                if score > best_score:
                    best_score = score
                    best_match = mapping
            
            if best_match:
                # Log the fuzzy match for debugging
                if best_score < 1.0:
                    print(f"Fuzzy matched path '{path}' to mapping '{best_match['xmlPath']}' with score {best_score}")
                return best_match
                
            return None
        except Exception as e:
            print(f"Error finding mapping for path: {e}")
            return None
    
    def create_output_structure(self):
        try:
            """Create the base output JSON structure"""
            # Extract form ID from filename (e.g. CFL04511 from CFL04511.xml)
            form_id = os.path.splitext(os.path.basename(self.xml_filename))[0]

            
            # Find title text manually since contains() is not supported in ElementTree XPath
            for text_elem in self.root.findall(".//template:text", self.namespaces):
                if text_elem.text and "Work Search" in text_elem.text:
                    form_title = text_elem.text
                    break
            
            return {
                "version": None,
                "ministry_id": self.mapping["constants"]["ministry_id"],
                "id": None,
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": None,
                "form_id": form_id,
                "deployed_to": None,
                "dataSources": [],
                "javascript": self.javascript_section,  # Add JavaScript section
                "data": {"items": []}  # Initialize empty items array
            }
        except Exception as e:
            print(f"Error creating output structure: {e}")
                        # In case of error, try to get form_id from filename, otherwise use default
            try:
                form_id = os.path.splitext(os.path.basename(self.xml_filename))[0]
            except:
                form_id = "FORM0001"
                

            return {
                "version": None,
                "ministry_id": "0",
                "id": None,
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": None,
                "form_id": form_id,
                "deployed_to": None,
                "dataSources": [],
                "javascript": self.javascript_section,  # Add JavaScript section
                "data": {"items": []}  # Initialize empty items array
            }
    
    def parse(self):
        try:
            """Main parsing method"""
            if self.root_subform is None:
                print("Root subform not found")
                return None
                
            # Process global scripts first
            self.process_global_scripts()
            
            # Process all sections
            self.process_master_pages()
            self.process_root_elements()
            
            # Add items to output JSON
            self.output_json["data"] = {"items": self.all_items}
            
            # Ensure JavaScript section is properly formatted
            if not self.javascript_section:
                self.javascript_section = {}
            
            # Once all fields are processed, save the report
            self.Report.save_report()
            return self.output_json
        except Exception as e:
            print(f"Error in main parse method: {e}")
            return None
    
    def process_master_pages(self):
        try:
            """Process pageSet elements (master pages)"""
            pagesets = self.root.findall(".//template:pageSet", self.namespaces)
            
            for pageset in pagesets:
                # Find text elements in pageSet for header/footer info
                for draw in pageset.findall(".//template:draw", self.namespaces):
                    draw_name = draw.attrib.get("name", "generic_text_display")
                    
                    # Get the text value if available
                    text_value = None
                    text_elem = draw.find(".//template:text", self.namespaces)
                    if text_elem is not None and text_elem.text:
                        text_value = text_elem.text
                    
                    # Create text-info field
                    text_field = {
                        "type": "text-info",
                        "id": self.next_id(),
                        "label": None,
                        "styles": None,
                        "mask": None,
                        "codeContext": {
                            "name": None
                        },
                        "value": text_value,
                    }
                    self.all_items.append(text_field)
                    self.Report.report_success(draw_name, 'text-info', text_value)
        except Exception as e:
            print(f"Error processing master pages: {e}")
    
    def process_page_fields(self, pageset):
        try:
            page_fields = []
            # Find text elements in pageSet for header/footer info
            for draw in pageset.findall(".//template:draw", self.namespaces):
                draw_name = draw.attrib.get("name", "generic_text_display")
                
                # Get the text value if available
                text_value = None
                text_elem = draw.find(".//template:text", self.namespaces)
                if text_elem is not None and text_elem.text:
                    text_value = text_elem.text
                
                # Create text-info field
                text_field = {
                    "type": "text-info",
                    "id": self.next_id(),
                    "label": None,
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": None
                    },
                    "value": text_value,
                }
                page_fields.append(text_field)
                self.Report.report_success(draw_name, 'text-info', text_value)
            return page_fields
        except Exception as e:
            print(f"Error processing page fields: {e}")
            self.Report.report_error("page_field", 'text-info', "Error processing page fields")
            return []
    
    def process_root_elements(self):
        try:
            """Process top-level elements in the main subform"""
            # First, check for any direct field or draw elements
            for draw in self.root_subform.findall(".//template:draw", self.namespaces):
                field = self.process_draw(draw)
                if field:
                    self.all_items.append(field)
            
            for field in self.root_subform.findall("./template:field", self.namespaces):
                field_obj = self.process_field(field)
                if field_obj:
                    field_script = self.process_script(field)
                    if field_script:
                        if "validation" in field_obj:
                            field_obj["validation"].append(field_script)
                        else:
                            field_obj["validation"] = [field_script]
                    self.all_items.append(field_obj)
            
            # Then process subforms (which become groups)
            for subform in self.root_subform.findall("./template:subform", self.namespaces):
                group = self.process_subform(subform)
                if group:
                    self.all_items.append(group)
            
            # Process exclusion groups (radio button groups)
            for exclgroup in self.root_subform.findall("./template:exclGroup", self.namespaces):
                group = self.process_exclgroup(exclgroup)
                if group:
                    self.all_items.append(group)
        except Exception as e:
            print(f"Error processing root elements: {e}")
    
    def process_draw(self, draw):
        try:
            """Process a draw element (usually text display or image)"""
            draw_name = draw.attrib.get("name", f"field_{self.id_counter}")
            
            # Track breadcrumb for mapping lookup
            self.add_breadcrumb(draw_name, draw)
            current_path = self.get_breadcrumb()
            
            # Find mapping configuration for this draw element
            mapping = self.find_mapping_for_path(current_path)
            
            # Check for image content first
            image_elem = draw.find(".//template:value/template:image", self.namespaces)
            if image_elem is not None and image_elem.attrib.get("contentType", "").startswith("image/"):
                # Create image field object
                field_obj = {
                    "type": "image",
                    "id": self.next_id(),
                    "label": None,
                    "styles": None,
                    "codeContext": {
                        "name": None
                    },
                    "contentType": image_elem.attrib.get("contentType"),
                    "value": image_elem.text if image_elem.text else None
                }
                
                # Apply any additional mapping properties
                if mapping:
                    if mapping.get("styles"):
                        field_obj["styles"] = mapping.get("styles")
                
                self.Report.report_success(draw_name, 'image', None)
                self.remove_breadcrumb(draw_name)
                return field_obj
            
            # Get text content if available
            text_value = None
            
            # First check for direct text value in value/text element
            value_elem = draw.find(".//template:value/template:text", self.namespaces)
            if value_elem is not None and value_elem.text:
                text_value = value_elem.text
            
            # Then check for text in exData
            if not text_value:
                for exdata_elem in draw.findall(".//template:exData", self.namespaces):
                    if exdata_elem.attrib.get("contentType") == "text/html":
                        html_text = self.extract_text_from_exdata(exdata_elem)
                        if html_text:
                            text_value = html_text
                            break
            
            # Get label using enhanced extraction
            label = self.extract_label(draw)
            
            # If no label but we have text that looks like a label, use it
            if not label and text_value:
                # Check if text_value looks like a label
                if text_value.endswith(':') or text_value.isupper() or len(text_value.split()) <= 4:
                    label = text_value
                    text_value = None  # Don't use the same text as both label and value
            
            # Check if this is a textEdit field
            is_text_edit = False
            ui_elem = draw.find(".//template:ui", self.namespaces)
            if ui_elem is not None:
                text_edit_elem = ui_elem.find(".//template:textEdit", self.namespaces)
                if text_edit_elem is not None:
                    is_text_edit = True
            
            # Determine field type - use mapping if available
            field_type = "generic_text_display"
            if mapping and mapping.get("fieldType"):
                field_type = mapping.get("fieldType")
            elif is_text_edit:
                field_type = "text-input"
            elif "foi" in draw_name.lower():
                field_type = "foi_statement"
            elif text_value:
                text_lower = text_value.lower()
                if "personal information" in text_lower or "freedom of information" in text_lower:
                    field_type = "foi_statement"
                # Check if this should be a text input based on field name or text content
                elif any(indicator in draw_name.lower() for indicator in ["file", "program", "document", "reference", "number", "input", "field", "data"]):
                    field_type = "text-input"
            # Check if this field is part of a group or table structure
            elif self.is_part_of_group_or_table(draw):
                field_type = "text-input"
            
            # Create field object based on type
            if field_type == "text-input":
                field_obj = {
                    "type": "text-input",
                    "id": self.next_id(),
                    "label": text_value,  # Set text value as label
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": draw_name
                    },
                    "placeholder": None,
                    "inputType": "text",
                    "value": ""  # Ensure value is empty
                }
                
                # If this is a textEdit field with a default value, add it
                if is_text_edit and text_value:
                    field_obj["value"] = ""  # Keep value empty even for textEdit fields
            else:
                # Create text-info field
                field_obj = {
                    "type": "text-info",
                    "id": self.next_id(),
                    "label": label,
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": draw_name
                    },
                    "value": text_value,
                }
            
            # Apply any additional mapping properties
            if mapping:
                if mapping.get("required"):
                    field_obj["required"] = mapping.get("required")
                if mapping.get("styles"):
                    field_obj["styles"] = mapping.get("styles")
            
            self.Report.report_success(draw_name, field_type, label or text_value)
            self.remove_breadcrumb(draw_name)
            return field_obj
        except Exception as e:
            print(f"Error processing draw element: {e}")
            self.Report.report_error(draw_name if 'draw_name' in locals() else "unknown_draw", 
                                    'text-info', 
                                    text_value if 'text_value' in locals() else "unknown_text")
            self.remove_breadcrumb(draw_name if 'draw_name' in locals() else "unknown")
            return None
    
    def extract_label(self, field):
        """Extract label from field using multiple methods"""
        try:
            label = None
            
            # Method 1: Direct caption
            caption_elem = field.find(".//template:caption//template:text", self.namespaces)
            if caption_elem is not None and caption_elem.text:
                label = caption_elem.text.strip()
            
            # Method 2: Value text that looks like a label
            if not label:
                value_elem = field.find(".//template:value//template:text", self.namespaces)
                if value_elem is not None and value_elem.text:
                    text = value_elem.text.strip()
                    # Check if this looks like a label (ends with :, all caps, etc)
                    if text.endswith(':') or text.isupper() or len(text.split()) <= 4:
                        label = text
            
            # Method 3: Field name converted to label
            if not label:
                field_name = field.attrib.get("name", "")
                if field_name:
                    # Convert camelCase/snake_case to space-separated words
                    import re
                    label = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', field_name)).strip()
                    label = ' '.join(word.capitalize() for word in re.split('[-_]', label))
            
            return label
        except Exception as e:
            print(f"Error extracting label: {e}")
            return None

    def process_field(self, field):
        try:
            """Process a field element"""
            field_name = field.attrib.get("name", f"field_{self.id_counter}")
            
            # Get current XML path for mapping lookup
            self.add_breadcrumb(field_name, field)
            current_path = self.get_breadcrumb()
            
            # Find mapping configuration for this field path
            mapping = self.find_mapping_for_path(current_path)
            
            # Get UI element to determine field type
            ui_elem = field.find("./template:ui", self.namespaces)
            if ui_elem is None:
                self.remove_breadcrumb(field_name)
                return None
            
            # Determine field type based on UI element
            ui_children = list(ui_elem)
            if not ui_children:
                self.remove_breadcrumb(field_name)
                return None
            
            ui_child = ui_children[0]
            ui_tag = ui_child.tag.split('}')[-1] if '}' in ui_child.tag else ui_child.tag

            # Get label using enhanced extraction
            label = self.extract_label(field)
            
            # Get help text if available
            help_text = None
            help_elem = field.find("./template:assist/template:toolTip", self.namespaces)
            if help_elem is not None and help_elem.text:
                help_text = help_elem.text
            
            # Get binding reference if available
            binding_ref = None
            binding_elem = field.find("./template:bind", self.namespaces)
            if binding_elem is not None and 'ref' in binding_elem.attrib:
                binding_ref = binding_elem.attrib['ref']
            
            # Create appropriate field object based on UI type
            field_obj = None
            
            # Apply mapping overrides if available
            field_type = None
            if mapping:
                field_type = mapping.get("fieldType")
                # Apply other mapping configurations
                if mapping.get("label"):
                    label = mapping.get("label")
            
            # Create field object based on UI type
            if ui_tag == "fileSelect":
                field_obj = {
                    "type": "file",
                    "id": self.next_id(),
                    "label": label,
                    "styles": None,
                    "codeContext": {
                        "name": field_name
                    },
                    "accept": "*/*",
                    "multiple": False,
                    "maxSize": None,
                    "validation": []
                }
                
                # Add databinding if available
                if binding_ref:
                    field_obj["databindings"] = {"path": binding_ref}
                    
                    # Apply any dataSource mappings
                    if mapping and mapping.get("dataSource"):
                        field_obj["databindings"]["source"] = mapping.get("dataSource")
            
            elif ui_tag == "textEdit":
                field_obj = {
                    "type": field_type or "text-input",
                    "id": self.next_id(),
                    "label": label,
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": None
                    },
                    "placeholder": None,
                    "inputType": "text",
                    "conditions": []
                }
                
                # Check for special field types based on field name if no mapping found
                if not field_type and ("area" in field_name.lower() or 
                                    any(area in field_name.lower() for area in ["comment", "description", "notes"])):
                    field_obj["type"] = "text-area"
                
                # Add databinding if available
                if binding_ref:
                    source = None
                    if "Contact" in binding_ref:
                        source = "Contact"
                    elif "Service" in binding_ref:
                        source = "Service Request"
                        
                    if source:
                        field_obj["databindings"] = {
                            "source": source,
                            "path": binding_ref
                        }
                    else:
                        field_obj["databindings"] = {
                            "path": binding_ref
                        }
                        
                    # Apply any dataSource mappings from the mapping file if present
                    if mapping and mapping.get("dataSource"):
                        field_obj["databindings"]["source"] = mapping.get("dataSource")
            
            elif ui_tag == "numericEdit":
                field_obj = {
                    "type": field_type or "text-input",
                    "id": self.next_id(),
                    "label": label,
                    "styles": None,
                    "codeContext": {
                        "name": None
                    },
                    "value": None,
                    "inputType": "number",
                    "conditions": []
                }
                
                if binding_ref:
                    field_obj["databindings"] = {"path": binding_ref}
                    
                    # Apply any dataSource mappings
                    if mapping and mapping.get("dataSource"):
                        field_obj["databindings"]["source"] = mapping.get("dataSource")
            
            elif ui_tag == "dateTimeEdit":
                # Extract the date format if available
                date_format = "yyyy-MM-dd"  # Default format
                format_elem = field.find("./template:format/template:picture", self.namespaces)
                if format_elem is not None and format_elem.text:
                    date_format = format_elem.text.lower().replace("yyyy", "Y").replace("dd", "d").replace("mm", "m")

                field_obj = {
                    "type": "date",
                    "label": label,
                    "id": self.next_id(),
                    "fieldId": str(self.next_id()),
                    "codeContext": {
                        "name": None
                    },
                    "label": label,
                    "placeholder": None,
                    "mask": date_format,
                    "conditions": []
                }
            
            elif ui_tag == "button":
                field_obj = {
                    "type": "button",
                    "id": self.next_id(),
                    "label": label,
                    "styles": None,
                    "codeContext": {
                        "name": None
                    },
                    "buttonType": "submit",
                    "conditions": []
                }
            
            elif ui_tag == "choiceList":
                field_obj = {
                    "id": self.next_id(),
                    "mask": None,
                    "size": "md",
                    "type": "dropdown",
                    "label": label if label else "Dropdown",
                    "styles": None,
                    "isMulti": False,
                    "isInline": False,
                    "direction": "bottom",
                    "listItems": [],  # List of dropdown options
                    "codeContext": {
                        "name": field_name
                    },
                    "placeholder": "",
                    "conditions": []
                }
                
                # Extract items directly with their attributes using ElementTree's API
                visible_items = []
                saved_values = []
                
                # Get all items elements first
                items_elements = field.findall("./template:items", self.namespaces)
                for items_elem in items_elements:
                    is_hidden = items_elem.get("presence") == "hidden"
                    is_saved = items_elem.get("save") == "1"
                    
                    # Get text elements within this items element
                    for text_elem in items_elem.findall("./template:text", self.namespaces):
                        if is_saved:
                            saved_values.append(text_elem)
                        elif not is_hidden:
                            visible_items.append(text_elem)

                # Ensure correct mapping of labels and values
                list_items = []
                for index, item in enumerate(visible_items):
                    value = saved_values[index].text if index < len(saved_values) else item.text
                    if item.text:
                        list_items.append({
                            "text": item.text.strip(),
                            "value": value.strip(),
                            "name": value.strip()
                        })

                field_obj["listItems"] = list_items
            
            elif ui_tag == "checkButton":
                field_obj = {
                    "type": "checkbox",
                    "id": self.next_id(),
                    "label": label if label else "Checkbox",
                    "webStyles": None,
                    "pdfStyles": None,
                    "mask": None,
                    "codeContext": {
                        "name": field_name
                    },
                    "databindings": {},
                    "conditions": []
                }

                # Extract checkbox default value (1 = checked, 0 = unchecked)
                value_elem = field.find("./template:value/template:integer", self.namespaces)
                if value_elem is not None:
                    field_obj["value"] = value_elem.text.strip() == "1"
                    # Assign Data Bindings (source & path)
                    binding_elem = field.find("./template:bind", self.namespaces)
                    if binding_elem is not None and 'ref' in binding_elem.attrib:
                        binding_ref = binding_elem.attrib['ref']
                        field_obj["databindings"] = {
                            "source": None,  # Adjust this if needed
                            "path": binding_ref
                        }
            
            elif ui_tag == "signature":
                field_obj = {
                    "id": self.next_id(),
                    "mask": None,
                    "type": "text-input",  # Overriding from "signature" to "text-input"
                    "label": label if label else None,
                    "styles": None,
                    "inputType": "text",
                    "codeContext": {
                        "name": field_name.lower().replace(" ", "_")  # Ensuring name consistency
                    },
                    "customStyle": {
                        "printColumns": "2"
                    },
                    "placeholder": "",
                    "conditions": []
                }

            # Process any scripts and get conditions after field_obj is created
            if field_obj:
                script_result = self.process_script(field)
                if script_result:
                    if script_result["type"] == "visibility":
                        field_obj["conditions"].append(script_result)
                    elif script_result["type"] == "calculatedValue":
                        field_obj["calculatedValue"] = script_result["value"]
                    elif script_result["type"] == "javascript":
                        if "validation" not in field_obj:
                            field_obj["validation"] = []
                        field_obj["validation"].append(script_result)

            self.remove_breadcrumb(field_name)
            
            if field_obj is not None:
                self.Report.report_success(field_obj["type"], 'text-info', field_obj["label"])
                
                # Apply any additional mappings to field_obj
                if mapping:
                    if mapping.get("required"):
                        field_obj["required"] = mapping.get("required")
                    if mapping.get("validation"):
                        if "validation" not in field_obj:
                            field_obj["validation"] = []
                        field_obj["validation"].extend(mapping.get("validation", []))
            else:
                self.Report.report_error(field_name, 'text-info', field_name, "Error processing field element")
                
            return field_obj
        except Exception as e:
            print(f"Error processing field element: {e}")
            self.Report.report_error(field_name if 'field_name' in locals() else "unknown_field", 
                                    'text-info',
                                    field_name if 'field_name' in locals() else "unknown",
                                    "Error processing field element")
            return None
    
    def process_script(self, field, event_name="initialize"):
        """Process script tags and convert Adobe JavaScript to standard JavaScript"""
        try:
            # Look for direct script tags
            script_tags = field.findall(".//template:script", self.namespaces)
            
            # Also look for scripts within event tags
            event_tags = field.findall(".//template:event", self.namespaces)
            for event_tag in event_tags:
                event_name = event_tag.attrib.get("activity", "initialize")
                for script_tag in event_tag.findall(".//template:script", self.namespaces):
                    script_tags.append((script_tag, event_name))
            
            field_id = field.attrib.get("name", f"field_{self.id_counter}")
            
            # Check if this is a group field
            is_group_field = False
            group_id = None
            parent = field.getparent() if hasattr(field, 'getparent') else None
            if parent is not None and 'subform' in parent.tag:
                is_group_field = True
                group_id = parent.attrib.get("name", "").split('_')[0]
                field_id = f"group_{group_id}_{field_id}"
            
            for script_item in script_tags:
                # Handle both direct script tags and event script tuples
                if isinstance(script_item, tuple):
                    script_tag, event_name = script_item
                else:
                    script_tag = script_item
                
                script_text = script_tag.text
                if script_text:
                    # Convert the script
                    converted_script = self.convert_adobe_script(script_text, field_id, event_name)
                    if converted_script:
                        # Add to JavaScript section
                        self.javascript_section[field_id] = converted_script
                        
                        # Check if this is a visibility condition
                        if "style.display" in converted_script:
                            return {
                                "type": "visibility",
                                "value": converted_script
                            }
                        # Check if this is a docReady event
                        elif event_name == "docReady":
                            return {
                                "type": "javascript",
                                "value": converted_script,
                                "event": "docReady",
                                "errorMessage": None
                            }
                        # Check if this is a calculated value - look for direct value assignment
                        elif "document.getElementById" in converted_script and ".value =" in converted_script:
                            return {
                                "type": "calculatedValue",
                                "value": converted_script
                            }
                        else:
                            return {
                                "type": "javascript",
                                "value": converted_script,
                                "errorMessage": None
                            }
            return None
        except Exception as e:
            print(f"Error processing script: {e}")
            return None

    def convert_adobe_script(self, script_text, field_id, event_name, is_global=False):
        """Convert Adobe-specific JavaScript to standard JavaScript"""
        try:
            # Create method name based on field ID and event
            method_name = f"global_{event_name}" if is_global else f"{field_id}_{event_name}"
            
            # Replace Adobe-specific terms
            script = script_text.replace("this.rawValue", "document.getElementById('" + field_id + "').value")
            script = script.replace(".presence = 'hidden'", ".style.display = 'none'")
            script = script.replace(".presence = 'visible'", ".style.display = 'block'")
            
            # Handle field references
            # Replace direct field references with document.getElementById calls
            import re
            field_refs = re.findall(r'(\w+)\.', script)
            for ref in field_refs:
                if ref != 'document':
                    # Check if this is a group field reference
                    if ref.startswith('group_'):
                        # Handle group field reference
                        group_id = ref.split('_')[1]
                        script = script.replace(f"{ref}.", f"groupStates['{group_id}']?.[0]?.['{group_id}-0-{ref}'].")
                    else:
                        # Handle regular field reference
                        script = script.replace(f"{ref}.", f"formStates['{ref}']")
            
            # Create the JavaScript method as a single line
            js_method = f"function {method_name}(fieldId) {{ const field = document.getElementById(fieldId); {script} }}"
            return js_method
        except Exception as e:
            print(f"Error converting Adobe script: {e}")
            return None

    def process_global_scripts(self):
        """Process global scripts in the root subform"""
        try:
            # Look for script tags in the root subform
            script_tags = self.root_subform.findall(".//template:script", self.namespaces)
            
            for script_tag in script_tags:
                script_text = script_tag.text
                if script_text:
                    # Convert the script as a global script
                    converted_script = self.convert_adobe_script(script_text, "global", "initialize", True)
                    if converted_script:
                        # Add to JavaScript section
                        self.javascript_section["global"] = converted_script
        except Exception as e:
            print(f"Error processing global scripts: {e}")

    def process_subform(self, subform):
        try:
            """Process a subform element"""
            subform_name = subform.attrib.get("name", f"subform_{self.id_counter}")
            
            # Check if this is a repeating group (has occur element)
            occur_elem = subform.find("./template:occur", self.namespaces)
            is_repeating = occur_elem is not None
            
            # Process any scripts and get conditions
            conditions = []
            script_result = self.process_script(subform)
            if script_result:
                if script_result["type"] == "visibility":
                    conditions.append(script_result)
                elif script_result["type"] == "javascript":
                    conditions.append(script_result)

            # Create group object if this is a repeating group
            if is_repeating:
                group_obj = {
                    "type": "group",
                    "id": self.next_id(),
                    "label": None,
                    "styles": None,
                    "codeContext": {
                        "name": subform_name
                    },
                    "repeater": True,
                    "conditions": conditions,
                    "groupItems": [
                        {
                            "fields": []
                        }
                    ]
                }
                
                # Process direct child fields in this subform (not descendants)
                for field in subform.findall("./template:field", self.namespaces):
                    field_obj = self.process_field(field)
                    if field_obj:
                        # Add conditions to each field
                        if conditions:
                            field_obj["conditions"].extend(conditions)
                        # Add subform name to codeContext for field identification
                        field_obj["codeContext"]["name"] = f"{subform_name}_{field_obj['codeContext']['name']}" if field_obj['codeContext']['name'] else subform_name
                        group_obj["groupItems"][0]["fields"].append(field_obj)

                # Process direct child draw elements (not descendants)
                for draw in subform.findall("./template:draw", self.namespaces):
                    draw_obj = self.process_draw(draw)
                    if draw_obj:
                        # Add conditions to each draw element
                        if conditions:
                            if "conditions" not in draw_obj:
                                draw_obj["conditions"] = []
                            draw_obj["conditions"].extend(conditions)
                        # Add subform name to codeContext for draw identification
                        draw_obj["codeContext"]["name"] = f"{subform_name}_{draw_obj['codeContext']['name']}" if draw_obj['codeContext']['name'] else subform_name
                        group_obj["groupItems"][0]["fields"].append(draw_obj)

                # Process direct child subforms (not descendants)
                for nested_subform in subform.findall("./template:subform", self.namespaces):
                    nested_group = self.process_subform(nested_subform)
                    if nested_group:
                        # Add conditions to nested group if they exist
                        if conditions:
                            if "conditions" not in nested_group:
                                nested_group["conditions"] = []
                            nested_group["conditions"].extend(conditions)
                        group_obj["groupItems"][0]["fields"].append(nested_group)

                # Add the group to all_items and return it
                self.all_items.append(group_obj)
                return group_obj
            else:
                # Process non-repeating subform fields directly
                for field in subform.findall("./template:field", self.namespaces):
                    field_obj = self.process_field(field)
                    if field_obj:
                        # Add conditions to each field
                        if conditions:
                            field_obj["conditions"].extend(conditions)
                        # Add subform name to codeContext for field identification
                        field_obj["codeContext"]["name"] = f"{subform_name}_{field_obj['codeContext']['name']}" if field_obj['codeContext']['name'] else subform_name
                        self.all_items.append(field_obj)

                # Process direct child draw elements (not descendants)
                for draw in subform.findall("./template:draw", self.namespaces):
                    draw_obj = self.process_draw(draw)
                    if draw_obj:
                        # Add conditions to each draw element
                        if conditions:
                            if "conditions" not in draw_obj:
                                draw_obj["conditions"] = []
                            draw_obj["conditions"].extend(conditions)
                        # Add subform name to codeContext for draw identification
                        draw_obj["codeContext"]["name"] = f"{subform_name}_{draw_obj['codeContext']['name']}" if draw_obj['codeContext']['name'] else subform_name
                        self.all_items.append(draw_obj)

                # Process direct child subforms (not descendants)
                for nested_subform in subform.findall("./template:subform", self.namespaces):
                    nested_group = self.process_subform(nested_subform)
                    if nested_group:
                        # Add conditions to nested group if they exist
                        if conditions:
                            if "conditions" not in nested_group:
                                nested_group["conditions"] = []
                            nested_group["conditions"].extend(conditions)
                        self.all_items.append(nested_group)

                return None

        except Exception as e:
            print(f"Error processing subform: {e}")
            return None

    def process_exclgroup(self, exclgroup):
        try:
            """Process an exclusion group (radio button group)"""
            group_name = exclgroup.attrib.get("name", f"exclgroup_{self.id_counter}")
            
            # Process any scripts and get conditions
            conditions = []
            script_result = self.process_script(exclgroup)
            if script_result:
                if script_result["type"] == "visibility":
                    conditions.append(script_result)
                elif script_result["type"] == "calculatedValue":
                    calculated_value = script_result["value"]
                elif script_result["type"] == "javascript":
                    if "validation" not in field_obj:
                        field_obj["validation"] = []
                    field_obj["validation"].append(script_result)
            
            # Process fields (usually radio buttons) in this group
            for field in exclgroup.findall("./template:field", self.namespaces):
                radio_obj = self.process_field(field)
                if radio_obj:
                    # Make sure it's a radio button and set the group name
                    if radio_obj["type"] == "radio":
                        radio_obj["groupName"] = group_name
                        # Add conditions to each radio button
                        if conditions:
                            radio_obj["conditions"] = conditions
                        self.all_items.append(radio_obj)
                        self.Report.report_success(group_name, 'radio', "Radio Button")
            
            return None  # No longer returning a group object
        except Exception as e:
            print(f"Error processing exclusion group: {e}")
            self.Report.report_error(group_name if 'group_name' in locals() else "unknown_exclgroup", 
                                    'radio', 
                                    "Error processing exclusion group")
            return None
    
    def extract_text_from_exdata(self, exdata_elem):
        try:
            # Get all text content recursively
            all_text = []
            
            # Define function to extract text from element and its children
            def extract_text(element):
                if element.text and element.text.strip():
                    all_text.append(element.text.strip())
                
                for child in element:
                    if '}' in child.tag:
                        tag = child.tag.split('}')[1]
                    else:
                        tag = child.tag
                        
                    # Skip style-related tags
                    if tag in ['style', 'xfa-spacerun']:
                        continue
                        
                    extract_text(child)
                    
                if element.tail and element.tail.strip():
                    all_text.append(element.tail.strip())
            
            # Start extraction with the body element directly under exdata_elem
            for body_elem in exdata_elem.findall(".//{http://www.w3.org/1999/xhtml}body"):
                extract_text(body_elem)
            
            # If no text was found in body, try direct text content
            if not all_text:
                if exdata_elem.text and exdata_elem.text.strip():
                    all_text.append(exdata_elem.text.strip())
            
            # Join all text pieces with space
            return " ".join(all_text)
        except Exception as e:
            print(f"Error extracting text from exData: {e}")
            return None

    def is_part_of_group_or_table(self, element):
        """Check if an element is part of a group or table structure"""
        try:
            # Get the parent element
            parent = element.getparent()
            if parent is None:
                return False
                
            # Check if parent is a subform (group) or table
            parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
            if parent_tag in ['subform', 'table']:
                return True
                
            # Check if parent has a name that suggests it's a group or table
            parent_name = parent.attrib.get("name", "").lower()
            if any(indicator in parent_name for indicator in ["group", "table", "grid", "row", "column", "cell"]):
                return True
                
            # Recursively check parent's parent
            return self.is_part_of_group_or_table(parent)
        except Exception:
            return False
