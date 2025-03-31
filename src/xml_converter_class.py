import xml.etree.ElementTree as ET
import json
import os
import uuid
from datetime import datetime
from report import Report

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
    
    def add_breadcrumb(self, tag):
        try:
            """Add element tag to breadcrumb path"""
            self.breadcrumb += f"<{tag}>"
            if len(self.breadcrumb) > 200:
                self.breadcrumb = self.breadcrumb[-200:]
        except Exception as e:
            print(f"Error adding breadcrumb: {e}")
    
    def remove_breadcrumb(self, tag):
        try:
            """Remove the last element tag from breadcrumb"""
            tag_str = f"<{tag}>"
            index = self.breadcrumb.rfind(tag_str)
            if index != -1:
                self.breadcrumb = self.breadcrumb[:index]
        except Exception as e:
            print(f"Error removing breadcrumb: {e}")
    
    def get_breadcrumb(self):
        try:
            """Get current breadcrumb path"""
            return self.breadcrumb
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
    
    def find_mapping_for_path(self, path):
        try:
            """Find mapping configuration for given path"""
            for mapping in self.mapping.get("mappings", []):
                if path.endswith(mapping.get("xmlPath", "")):
                    return mapping
            return None
        except Exception as e:
            print(f"Error finding mapping for path: {e}")
            return None
    
    def create_output_structure(self):
        try:
            """Create the base output JSON structure"""
            # Extract form ID from filename or default
            form_id = os.path.splitext(os.path.basename(self.xml_filename))[0]  # Remove extension
            # Get form title if available
            form_title = "Work Search Activity Record"  # Default title
            
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
            return {
                "version": None,
                "ministry_id": "0",
                "id": None,
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": None,
                "form_id": "FORM0001",
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
                        "helpText": None,
                        "styles": None,
                        "mask": None,
                        "codeContext": {
                            "name": None
                        },
                        "value": text_value,
                        "helperText": None
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
                    "helpText": None,
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": None
                    },
                    "value": text_value,
                    "helperText": None
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
            """Process a draw element (usually text display)"""
            draw_name = draw.attrib.get("name", f"field_{self.id_counter}")
            
            # Track breadcrumb for mapping lookup
            self.add_breadcrumb(draw_name)
            current_path = self.get_breadcrumb()
            
            # Find mapping configuration for this draw element
            mapping = self.find_mapping_for_path(current_path)
            
            # Get text content if available
            text_value = None
            text_elem = draw.find(".//template:text", self.namespaces)
            if text_elem is not None and text_elem.text:
                text_value = text_elem.text
            
            # Check for HTML content in exData
            for exdata_elem in draw.findall(".//template:exData", self.namespaces):
                if exdata_elem.attrib.get("contentType") == "text/html":
                    html_text = self.extract_text_from_exdata(exdata_elem)
                    if html_text:
                        text_value = html_text
                        break
            
            # Determine field type - use mapping if available
            field_type = "generic_text_display"
            if mapping and mapping.get("fieldType"):
                field_type = mapping.get("fieldType")
            elif "foi" in draw_name.lower():
                field_type = "foi_statement"
            elif text_value:
                text_lower = text_value.lower()
                if "personal information" in text_lower or "freedom of information" in text_lower:
                    field_type = "foi_statement"
            
            # Create text-info field
            field_obj = {
                "type": "text-info",
                "id": self.next_id(),
                "label": mapping.get("label") if mapping else None,
                "helpText": mapping.get("helpText") if mapping else None,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": None
                },
                "value": text_value,
                "helperText": None
            }
            
            # Apply any additional mapping properties
            if mapping:
                if mapping.get("required"):
                    field_obj["required"] = mapping.get("required")
                if mapping.get("styles"):
                    field_obj["styles"] = mapping.get("styles")
                
            self.Report.report_success(draw_name, 'text-info', text_value)
            self.remove_breadcrumb(draw_name)
            return field_obj
        except Exception as e:
            print(f"Error processing draw element: {e}")
            self.Report.report_error(draw_name if 'draw_name' in locals() else "unknown_draw", 
                                    'text-info', 
                                    text_value if 'text_value' in locals() else "unknown_text")
            self.remove_breadcrumb(draw_name if 'draw_name' in locals() else "unknown")
            return None
    
    def process_field(self, field):
        try:
            """Process a field element"""
            field_name = field.attrib.get("name", f"field_{self.id_counter}")
            
            # Get current XML path for mapping lookup
            self.add_breadcrumb(field_name)
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

            # Get caption/label if available
            caption_text = None
            caption_elem = field.find("./template:caption/template:value/template:text", self.namespaces)
            if caption_elem is not None and caption_elem.text:
                caption_text = caption_elem.text
            
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
                    caption_text = mapping.get("label")
                if mapping.get("helpText"):
                    help_text = mapping.get("helpText")
            
            # Create field object based on UI type
            if ui_tag == "textEdit":
                field_obj = {
                    "type": field_type or "text-input",
                    "id": self.next_id(),
                    "label": caption_text,
                    "helpText": help_text,
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": None
                    },
                    "placeholder": None,
                    "helperText": None,
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
                    "label": caption_text,
                    "helpText": help_text,
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
                    "label": caption_text,
                    "id": self.next_id(),
                    "fieldId": str(self.next_id()),
                    "codeContext": {
                        "name": None
                    },
                    "label": caption_text,
                    "placeholder": None,
                    "mask": date_format,
                    "conditions": []
                }
            
            elif ui_tag == "button":
                field_obj = {
                    "type": "button",
                    "id": self.next_id(),
                    "label": caption_text,
                    "helpText": help_text,
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
                    "label": caption_text if caption_text else "Dropdown",
                    "styles": None,
                    "isMulti": False,
                    "helpText": None,
                    "isInline": False,
                    "direction": "bottom",
                    "listItems": [],  # List of dropdown options
                    "helperText": "",
                    "codeContext": {
                        "name": field_name
                    },
                    "placeholder": "",
                    "conditions": []
                }
                
                # Extract visible items from `<items>` tag
                visible_items = field.findall("./template:items/template:text", self.namespaces)
                saved_values = field.findall("./template:items[@save='1']/template:text", self.namespaces)

                # Ensure correct mapping of labels and values
                list_items = []
                for index, item in enumerate(visible_items):
                    value = saved_values[index].text if index < len(saved_values) else item.text
                    if item.text:
                        list_items.append({"text": item.text.strip(), "value": value.strip()})

                field_obj["listItems"] = list_items
            
            elif ui_tag == "checkButton":
                field_obj = {
                    "type": "checkbox",
                    "id": self.next_id(),
                    "label": caption_text if caption_text else "Checkbox",
                    "helperText": "",
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
                    "label": caption_text if caption_text else None,
                    "styles": None,
                    "helpText": help_text,
                    "inputType": "text",
                    "helperText": "",
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
            script_tags = field.findall(".//template:script", self.namespaces)
            field_id = field.attrib.get("name", f"field_{self.id_counter}")
            
            # Check if this is a group field
            is_group_field = False
            group_id = None
            parent = field.getparent() if hasattr(field, 'getparent') else None
            if parent is not None and 'subform' in parent.tag:
                is_group_field = True
                group_id = parent.attrib.get("name", "").split('_')[0]
                field_id = f"group_{group_id}_{field_id}"
            
            for script_tag in script_tags:
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
                        # Check if this is a calculated value
                        elif "value" in converted_script:
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
            
            # Create the JavaScript method
            js_method = f"""
function {method_name}(fieldId) {{
    const field = document.getElementById(fieldId);
    {script}
}}
"""
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
            
            # Process any scripts and get conditions
            conditions = []
            script_result = self.process_script(subform)
            if script_result:
                if script_result["type"] == "visibility":
                    conditions.append(script_result)
                elif script_result["type"] == "calculatedValue":
                    calculated_value = script_result["value"]
                elif script_result["type"] == "javascript":
                    if "validation" not in field_obj:
                        field_obj["validation"] = []
                    field_obj["validation"].append(script_result)

            # Process direct child fields in this subform (not descendants)
            for field in subform.findall("./template:field", self.namespaces):
                field_obj = self.process_field(field)
                if field_obj:
                    # Add conditions to each field
                    if conditions:
                        field_obj["conditions"] = conditions
                    # Add subform name to codeContext for field identification
                    field_obj["codeContext"]["name"] = f"{subform_name}_{field_obj['codeContext']['name']}" if field_obj['codeContext']['name'] else subform_name
                    self.all_items.append(field_obj)

            # Process direct child draw elements (not descendants)
            for draw in subform.findall("./template:draw", self.namespaces):
                draw_obj = self.process_draw(draw)
                if draw_obj:
                    # Add conditions to each draw element
                    if conditions:
                        draw_obj["conditions"] = conditions
                    # Add subform name to codeContext for draw identification
                    draw_obj["codeContext"]["name"] = f"{subform_name}_{draw_obj['codeContext']['name']}" if draw_obj['codeContext']['name'] else subform_name
                    self.all_items.append(draw_obj)

            # Process direct child subforms (not descendants)
            for nested_subform in subform.findall("./template:subform", self.namespaces):
                self.process_subform(nested_subform)

            return None  # No longer returning a group object
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
