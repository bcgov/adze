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
            form_id = "HR0001"  # Default form ID
            if "HR" in self.xml_filename:
                parts = self.xml_filename.split("HR")
                if len(parts) > 1:
                    form_id_part = parts[1].split(".")[0]
                    if form_id_part:
                        form_id = f"HR{form_id_part}"
            
            # Get form title if available
            form_title = "Work Search Activity Record"  # Default title
            
            # Find title text manually since contains() is not supported in ElementTree XPath
            for text_elem in self.root.findall(".//template:text", self.namespaces):
                if text_elem.text and "Work Search" in text_elem.text:
                    form_title = text_elem.text
                    break
            
            return {
                "version": self.mapping["constants"]["version"],
                "ministry_id": self.mapping["constants"]["ministry_id"],
                "id": str(uuid.uuid4()),
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": form_title,
                "form_id": form_id,
                "deployed_to": None,
                "dataSources": []
            }
        except Exception as e:
            print(f"Error creating output structure: {e}")
            return {
                "version": "1.0",
                "ministry_id": "0",
                "id": str(uuid.uuid4()),
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": "Form",
                "form_id": "FORM0001",
                "deployed_to": None,
                "dataSources": []
            }
    
    def parse(self):
        try:
            """Main parsing method"""
            if self.root_subform is None:
                print("Root subform not found")
                return None
                
            # Process all sections
            self.process_master_pages()
            self.process_root_elements()
            
            # Add items to output JSON
            self.output_json["data"] = {"items": self.all_items}
            
            # # Write output
            # output_file = 'mapping_output.json'
            # with open(output_file, 'w') as json_file:
            #     json.dump(self.output_json, json_file, indent=4)
                
            # print(f"JSON output saved to {output_file}")
            
            # Once all fields are processed, save the report (instead of saving after every field)
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
                
                page_fields = self.process_page_fields(pageset)
                # Add master page group if we found any fields
                if page_fields:
                    master_page = {
                        "type": "group",
                        "label": "Master Page",
                        "id": self.next_id(),
                        "groupId": str(self.mapping["constants"]["ministry_id"]),
                        "repeater": False,
                        "codeContext": {
                            "name": "master_page"
                        },
                        "groupItems": [
                            {
                                "fields": page_fields
                            }
                        ]
                    }
                    self.all_items.append(master_page)
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
                        "name": draw_name
                    },
                    "value": text_value,
                    "helperText": " as it appears on official documents"
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
            for draw in self.root_subform.findall("./template:draw", self.namespaces):
                field = self.process_draw(draw)
                if field:
                    self.all_items.append(field)
            
            for field in self.root_subform.findall("./template:field", self.namespaces):
                field_obj = self.process_field(field)
                if field_obj:
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
            
            # Check for HTML content
            html_elem = None
            for elem in draw.findall(".//template:exData", self.namespaces):
                if elem.attrib.get("contentType") == "text/html":
                    html_elem = elem
                    break
                    
            if html_elem is not None and html_elem.text:
                text_value = html_elem.text
            
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
                    "name": field_type
                },
                "value": text_value,
                "helperText": " as it appears on official documents"
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
            
            if ui_tag == "textEdit":
                field_obj = {
                    "type": field_type or "text-input",
                    "id": self.next_id(),
                    "label": caption_text,
                    "helpText": help_text,
                    "styles": None,
                    "mask": None,
                    "codeContext": {
                        "name": field_name
                    },
                    "placeholder": "Enter your ",
                    "helperText": " as it appears on official documents",
                    "inputType": "text"
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
                        "name": field_name
                    },
                    "value": None,
                    "inputType": "number"
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

                # Define validation rules
                validation_rules = [
                    {
                        "type": "required",
                        "value": True,
                        "errorMessage": "Date of birth should be submitted"
                    },
                    {
                        "type": "maxDate",
                        "value": "2024-09-01",
                        "errorMessage": "Date should be less than September 1st 2024 due to legislation"
                    },
                    {
                        "type": "minDate",
                        "value": "2000-01-01",
                        "errorMessage": "Date should be greater than January 1st 2000 due to legislations"
                    },
                    {
                        "type": "javascript",
                        "value": "{ const birthDate = new Date(value); const today = new Date();"
                                " const age = today.getFullYear() - birthDate.getFullYear();"
                                " const monthDiff = today.getMonth() - birthDate.getMonth();"
                                " const dayDiff = today.getDate() - birthDate.getDate();"
                                " if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) { age--; }"
                                " return age >= 18; }",
                        "errorMessage": "You must be at least 18 years old."
                    }
                ]

                # Create the JSON structure for date-picker
                field_obj = {
                    "type": "date-picker",
                    "label": caption_text or "Date Field",
                    "id": self.next_id(),
                    "fieldId": str(self.next_id()),
                    "codeContext": {
                        "name": field_name
                    },
                    "labelText": caption_text or "Date Field",
                    "placeholder": "yyyy-MM-dd",
                    "mask": date_format,
                    "validation": validation_rules
                }
            elif ui_tag == "button":
                field_obj = {
                    "type": "button",
                    "id": self.next_id(),
                    "label": caption_text,
                    "helpText": help_text,
                    "styles": None,
                    "codeContext": {
                        "name": field_name
                    },
                    "buttonType": "submit"
                }
            
            # Rest of the method remains the same...
            # (Other field types like dateTimeEdit, checkButton, etc.)
            
            self.remove_breadcrumb(field_name)
            
            if field_obj is not None:
                self.Report.report_success(field_obj["type"], 'text-info', field_obj["label"])
                
                # Apply any additional mappings to field_obj
                if mapping:
                    if mapping.get("required"):
                        field_obj["required"] = mapping.get("required")
                    if mapping.get("validation"):
                        field_obj["validation"] = mapping.get("validation")
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
    
    def process_subform(self, subform):
        try:
            """Process a subform element (adds it as a top-level group)"""
            subform_name = subform.attrib.get("name", f"generic_subform_{self.id_counter}")

            # Check if this is a repeating subform
            has_occur = subform.find("./template:occur", self.namespaces) is not None

            # Determine group ID based on name
            group_id = "1"  # Default
            if "contact" in subform_name.lower():
                group_id = "11"
            elif "submit" in subform_name.lower():
                group_id = "6"

            # Group label - Capitalize words and add spaces
            label = " ".join(word.capitalize() for word in subform_name.split("_"))
            if has_occur:
                label = f"Table - {label}"

            # Create group for this subform
            subform_group = {
                "type": "group",
                "label": label,
                "id": self.next_id(),
                "groupId": group_id,
                "repeater": has_occur,
                "codeContext": {
                    "name": subform_name
                },
                "groupItems": [{"fields": []}]
            }

            # Process fields in this subform
            for field in subform.findall("./template:field", self.namespaces):
                field_obj = self.process_field(field)
                if field_obj:
                    subform_group["groupItems"][0]["fields"].append(field_obj)

            # Process draw elements (text display)
            for draw in subform.findall("./template:draw", self.namespaces):
                draw_obj = self.process_draw(draw)
                if draw_obj:
                    subform_group["groupItems"][0]["fields"].append(draw_obj)

            # If subform has fields, add it to top-level items
            if subform_group["groupItems"][0]["fields"]:
                self.all_items.append(subform_group)

            # Process nested subforms (add them at the top level, not under this subform)
            for nested_subform in subform.findall("./template:subform", self.namespaces):
                self.process_subform(nested_subform)

        except Exception as e:
            print(f"Error processing subform: {e}")



    def process_exclgroup(self, exclgroup):
        try:
            """Process an exclusion group (radio button group)"""
            group_name = exclgroup.attrib.get("name", f"exclgroup_{self.id_counter}")
            
            # Create group for this exclusion group
            group_obj = {
                "type": "group",
                "label": group_name,
                "id": self.next_id(),
                "groupId": "1",
                "repeater": False,
                "codeContext": {
                    "name": group_name
                },
                "groupItems": [
                    {
                        "fields": []
                    }
                ]
            }
            
            # Process fields (usually radio buttons) in this group
            fields = []
            for field in exclgroup.findall("./template:field", self.namespaces):
                radio_obj = self.process_field(field)
                if radio_obj:
                    # Make sure it's a radio button and set the group name
                    if radio_obj["type"] == "radio":
                        radio_obj["groupName"] = group_name
                    fields.append(radio_obj)
            
            # If we found fields, add them to the group
            if fields:
                group_obj["groupItems"][0]["fields"] = fields
                self.Report.report_success(group_name, 'group', "Exclusion Group")
                return group_obj
            
            return None
        except Exception as e:
            print(f"Error processing exclusion group: {e}")
            self.Report.report_error(group_name if 'group_name' in locals() else "unknown_exclgroup", 
                                    'group', 
                                    "Error processing exclusion group")
            return None