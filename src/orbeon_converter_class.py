import xml.etree.ElementTree as ET
import json
import os
import uuid
from datetime import datetime
from src.report import Report

class OrbeonParser:
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
            self.namespaces = {
                'xh': 'http://www.w3.org/1999/xhtml',
                'xf': 'http://www.w3.org/2002/xforms',
                'fr': 'http://orbeon.org/oxf/xml/form-runner',
                'fb': 'http://orbeon.org/oxf/xml/form-builder',
                'xxf': 'http://orbeon.org/oxf/xml/xforms'
            }

            # Parse the XML file
            self.tree = ET.parse(xml_filename)
            self.root = self.tree.getroot()
            
            # Get form instance - the main data container in Orbeon
            self.form_instance = self.root.find(".//xf:instance[@id='fr-form-instance']", self.namespaces)
            if self.form_instance is None:
                raise ValueError("Form instance not found in Orbeon XML")
                
            self.form_data = self.form_instance.find(".//form", self.namespaces)
            if self.form_data is None:
                raise ValueError("Form data not found in Orbeon XML")

            # Find bind elements for additional metadata
            self.form_binds = self.root.find(".//xf:bind[@id='fr-form-binds']", self.namespaces)
            self.binds_map = {}
            if self.form_binds is not None:
                self.extract_binds(self.form_binds)

            # Get form resources for labels
            self.form_resources = self.root.find(".//xf:instance[@id='fr-form-resources']", self.namespaces)
            if self.form_resources is None:
                raise ValueError("Form resources not found in Orbeon XML")

            # Output JSON structure
            self.output_json = self.create_output_structure()
            self.all_items = []
            self.Report = Report(xml_filename)
        except Exception as e:
            print(f"Error initializing OrbeonParser: {e}")
            raise
    
    def extract_binds(self, bind_element, parent_path=""):
        """Extract bind information from the form to get metadata"""
        try:
            for bind in bind_element:
                if 'id' in bind.attrib and 'ref' in bind.attrib:
                    bind_id = bind.attrib['id']
                    ref = bind.attrib['ref']
                    name = bind.attrib.get('name', '')
                    
                    # Build path
                    path = f"{parent_path}/{ref}" if parent_path else ref
                    
                    # Store bind information
                    self.binds_map[path] = {
                        'id': bind_id,
                        'name': name,
                        'attributes': {k: v for k, v in bind.attrib.items() if k not in ['id', 'ref', 'name']}
                    }
                    
                    # Process nested binds
                    self.extract_binds(bind, path)
        except Exception as e:
            print(f"Error extracting binds: {e}")
    
    def get_bind_info(self, field_name, section_path=""):
        """Get bind information for a field"""
        try:
            path = f"{section_path}/{field_name}" if section_path else field_name
            return self.binds_map.get(path)
        except Exception as e:
            print(f"Error getting bind info: {e}")
            return None
    
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

            form_id = os.path.splitext(os.path.basename(self.xml_filename))[0]

            
            return {
                "version": None,
                "ministry_id": self.mapping["constants"]["ministry_id"],
                "id": None,
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": None,
                "form_id": form_id,
                "deployed_to": None,
                "dataSources": []
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
                "form_id": "FORM0001",
                "deployed_to": None,
                "dataSources": []
            }
    
    def parse(self):
        try:
            """Main parsing method"""
            # Process all sections
            self.process_form_sections()
            
            # Add items to output JSON
            self.output_json["data"] = {"items": self.all_items}
            
            # Once all fields are processed, save the report
            self.Report.save_report()
            return self.output_json
        except Exception as e:
            print(f"Error in main parse method: {e}")
            return None
    
    def process_form_sections(self):
        try:
            """Process all sections in the form"""
            # Find all sections in the form
            for section in self.form_data:
                self.process_section(section)
                
        except Exception as e:
            print(f"Error processing form sections: {e}")
    
    def process_section(self, section):
        try:
            """Process a section in the form"""
            section_name = section.tag
            self.add_breadcrumb(section_name)
            
            # Process each grid in the section
            for grid in section:
                grid_name = grid.tag
                self.add_breadcrumb(grid_name)
                
                # Handle grid iterations differently (they can contain repeating fields)
                iteration_tag = f"{grid_name}-iteration"
                iterations = grid.findall(f"./{iteration_tag}", self.namespaces)
                
                if iterations:
                    # This is a repeating grid
                    for iteration in iterations:
                        self.process_grid_iteration(iteration)
                else:
                    # Regular grid with fields
                    for field_elem in grid:
                        field_obj = self.process_field(field_elem)
                        if field_obj:
                            self.all_items.append(field_obj)
                
                self.remove_breadcrumb(grid_name)
            
            # Check if there are nested sections (like section-child-information within section-a)
            nested_sections = False
            for item in section:
                if item.tag.startswith("section-"):
                    nested_sections = True
                    break
            
            # If this section has nested sections, process them separately
            if nested_sections:
                for nested_section in section:
                    if nested_section.tag.startswith("section-"):
                        self.process_section(nested_section)
            
            self.remove_breadcrumb(section_name)
        except Exception as e:
            print(f"Error processing section {section.tag if hasattr(section, 'tag') else 'unknown'}: {e}")
    
    def process_grid_iteration(self, iteration):
        try:
            """Process a grid iteration (repeating fields)"""
            for field_elem in iteration:
                field_obj = self.process_field(field_elem)
                if field_obj:
                    self.all_items.append(field_obj)
        except Exception as e:
            print(f"Error processing grid iteration: {e}")
    
    def process_field(self, field_elem):
        try:
            """Process a field element"""
            field_name = field_elem.tag
            field_value = None
            
            # For text-info fields, first check form instance for text content
            form_instance_elem = self.form_instance.find(f".//{field_name}/text", self.namespaces)
            if form_instance_elem is not None:
                field_value = form_instance_elem.text
            else:
                # Then check the field element itself
                text_elem = field_elem.find(".//text", self.namespaces)
                if text_elem is not None:
                    field_value = text_elem.text
                else:
                    field_value = field_elem.text
            
            # Track breadcrumb for mapping lookup
            self.add_breadcrumb(field_name)
            current_path = self.get_breadcrumb()
            
            # Process any attributes the field might have
            field_attributes = {}
            if field_elem.attrib:
                field_attributes = {k: v for k, v in field_elem.attrib.items()}
            
            # Find mapping for this field
            mapping = self.find_mapping_for_path(current_path)
            
            # Check if field is bound to an input
            field_type = self.determine_field_type(field_name, field_value, field_attributes, mapping)
            
            # Special handling for control elements with text content
            if field_name.startswith("control-"):
                # Check if it's an explanation element
                explanation_elem = self.root.find(f".//fr:explanation[@bind='{field_name}-bind']", self.namespaces)
                if explanation_elem is not None:
                    field_type = "text-info"
                    # Get text content from form resources
                    text_ref = explanation_elem.find(".//fr:text", self.namespaces)
                    if text_ref is not None:
                        # Extract the reference path
                        ref_path = text_ref.get("ref")
                        if ref_path and ref_path.startswith("$form-resources/"):
                            # Remove the $form-resources/ prefix
                            ref_path = ref_path[len("$form-resources/"):]
                            # Find the text in form resources
                            resource_text = self.form_resources.find(f".//resource/{ref_path}", self.namespaces)
                            if resource_text is not None:
                                field_value = resource_text.text
                elif form_instance_elem is not None or text_elem is not None:
                    field_type = "text-info"
                    field_value = form_instance_elem.text if form_instance_elem is not None else text_elem.text
            
            # Create the field object based on type
            field_obj = self.create_field_object(field_type, field_name, field_value, field_attributes, mapping)
            
            # Process dropdown options if needed
            if field_type == "dropdown":
                options = self.extract_dropdown_options(field_elem)
                if options:
                    field_obj["listItems"] = options
            
            # Process checkbox value
            if field_type == "checkbox":
                # Check for explicit value in XML
                value_elem = field_elem.find(".//value", self.namespaces)
                if value_elem is not None and value_elem.text:
                    field_obj["value"] = value_elem.text.lower() == "true"
                else:
                    # Default to false if no value specified
                    field_obj["value"] = False
            
            # Process date validation
            if field_type == "date":
                # Add specific validation rules based on field name
                if "birth" in field_name.lower():
                    field_obj["validation"].extend([
                        {
                            "type": "maxDate",
                            "value": "2024-09-01",
                            "errorMessage": "Date should be less than September 1st 2024 due to legislation"
                        },
                        {
                            "type": "minDate",
                            "value": "2000-01-01",
                            "errorMessage": "Date should be greater than January 1st 2000 due to legislations"
                        }
                    ])
                elif "signed" in field_name.lower():
                    field_obj["validation"].extend([
                        {
                            "type": "maxDate",
                            "value": datetime.now().strftime("%Y-%m-%d"),
                            "errorMessage": "Date cannot be in the future"
                        }
                    ])
            
            self.remove_breadcrumb(field_name)
            
            if field_obj is not None:
                self.Report.report_success(field_name, field_type, field_obj.get("label", ""))
            
            return field_obj
        except Exception as e:
            print(f"Error processing field {field_elem.tag if hasattr(field_elem, 'tag') else 'unknown'}: {e}")
            self.Report.report_error(field_elem.tag if hasattr(field_elem, 'tag') else "unknown", 
                                    "unknown", 
                                    "Error processing field")
            return None
    
    def determine_field_type(self, field_name, field_value, field_attributes, mapping):
        """Determine the type of field based on its attributes and mapping"""
        try:
            # Check mapping first
            if mapping and mapping.get("fieldType"):
                return mapping.get("fieldType")
            
            # Check for file upload fields
            if field_attributes.get('filename') or field_attributes.get('mediatype'):
                return "file"
            
            # Check if field is a control with text tag
            if field_name.startswith("control-"):
                # First check if it's an explanation element
                explanation_elem = self.root.find(f".//fr:explanation[@bind='{field_name}-bind']", self.namespaces)
                if explanation_elem is not None:
                    return "text-info"
                
                # Then check directly in the field element
                text_elem = self.form_instance.find(f".//{field_name}/text", self.namespaces)
                if text_elem is not None:
                    return "text-info"
            
            # Check if field is bound to an input
            bind_elem = self.root.find(f".//xf:bind[@ref='{field_name}']", self.namespaces)
            if bind_elem is not None:
                # Check for checkbox-input elements first
                checkbox_input_elem = self.root.find(f".//fr:checkbox-input[@bind='{field_name}-bind']", self.namespaces)
                if checkbox_input_elem is not None:
                    return "checkbox"
                
                # Check for select1 elements (dropdowns or radio buttons)
                select1_elem = self.root.find(f".//xf:select1[@bind='{field_name}-bind']", self.namespaces)
                if select1_elem is not None:
                    # Check if it's a radio button group
                    appearance = select1_elem.get("appearance", "")
                    if appearance == "full":
                        return "radio"
                    return "dropdown"
                
                # Check for textarea elements
                textarea_elem = self.root.find(f".//xf:textarea[@bind='{field_name}-bind']", self.namespaces)
                if textarea_elem is not None:
                    return "text-area"
                
                # Check for date elements
                date_elem = self.root.find(f".//fr:date[@bind='{field_name}-bind']", self.namespaces)
                if date_elem is not None:
                    return "date"
                
                # Check for currency elements
                currency_elem = self.root.find(f".//fr:currency[@bind='{field_name}-bind']", self.namespaces)
                if currency_elem is not None:
                    return "currency"
                
                # Check for checkbox elements - look for both input and checkbox elements
                checkbox_elem = self.root.find(f".//xf:input[@bind='{field_name}-bind']", self.namespaces)
                if checkbox_elem is not None:
                    # Check if it's a checkbox by looking at type or appearance
                    if checkbox_elem.get("type") == "checkbox" or checkbox_elem.get("appearance") == "checkbox":
                        return "checkbox"
                
                # Also check for checkbox elements in the form instance
                checkbox_instance = self.form_instance.find(f".//{field_name}", self.namespaces)
                if checkbox_instance is not None and checkbox_instance.get("type") == "checkbox":
                    return "checkbox"
            
            # Check if field is a resource
            if field_name.startswith("control-") and field_value is None:
                # Check if the resource has a text tag
                text_elem = self.form_instance.find(f".//form//{field_name}/text", self.namespaces)
                if text_elem is not None:
                    return "text-info"
                # If no text tag, treat as text-input
                return "text-input"
            
            # Check for date fields by name
            if any(date_indicator in field_name.lower() for date_indicator in ['date', 'birth', 'signed']):
                return "date"
            
            # Check for phone number fields
            if any(phone_indicator in field_name.lower() for phone_indicator in ['phone', 'tel', 'mobile', 'cell']):
                return "phone"
            
            # Check for email fields
            if any(email_indicator in field_name.lower() for email_indicator in ['email', 'mail', 'e-mail']):
                return "email"
            
            # Default to text input
            return "text-input"
        except Exception as e:
            print(f"Error determining field type for {field_name}: {e}")
            return "text-input"
    
    def create_field_object(self, field_type, field_name, field_value, field_attributes, mapping):
        """Create field object based on field type"""
        field_obj = None
        
        # Get bind information for validation and label
        bind_info = self.get_bind_info(field_name)
        validation_rules = []
        
        # Extract validation rules from bind info
        if bind_info and 'attributes' in bind_info:
            bind_attrs = bind_info['attributes']
            
            # Handle required validation
            if bind_attrs.get('required') == 'true()':
                validation_rules.append({
                    "type": "required",
                    "value": True,
                    "errorMessage": bind_attrs.get('xxf:required-message', "This field is required")
                })
            
            # Handle pattern validation
            if 'pattern' in bind_attrs:
                validation_rules.append({
                    "type": "pattern",
                    "value": bind_attrs['pattern'],
                    "errorMessage": bind_attrs.get('xxf:pattern-message', "Invalid format")
                })
            
            # Handle min/max validation
            if 'min' in bind_attrs:
                validation_rules.append({
                    "type": "min",
                    "value": bind_attrs['min'],
                    "errorMessage": bind_attrs.get('xxf:min-message', f"Value must be at least {bind_attrs['min']}")
                })
            if 'max' in bind_attrs:
                validation_rules.append({
                    "type": "max",
                    "value": bind_attrs['max'],
                    "errorMessage": bind_attrs.get('xxf:max-message', f"Value must be at most {bind_attrs['max']}")
                })
        
        # Get label and hint from form resources
        label = self.get_field_label(field_name)
        hint = self.get_field_hint(field_name)
        
        # Fallback to bind info or formatted field name if no label found
        if not label:
            label = bind_info.get('name', '') if bind_info and bind_info.get('name') else self.format_field_name(field_name)
        
        if field_type == "text-info":
            field_obj = {
                "type": "text-info",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "value": field_value
            }
        elif field_type == "text-input":
            field_obj = {
                "type": "text-input",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": None,
                "inputType": "text"
            }
            if field_value:
                field_obj["value"] = field_value
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "text-area":
            field_obj = {
                "type": "text-area",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": None
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "date":
            field_obj = {
                "type": "date",
                "id": self.next_id(),
                "fieldId": self.next_id(),
                "label": label,
                "helpText": hint,
                "placeholder": None,
                "mask": "yyyy-MM-dd",
                "codeContext": {
                    "name": field_name
                },
                "validation": validation_rules
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        elif field_type == "checkbox":
            field_obj = {
                "type": "checkbox",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "webStyles": None,
                "pdfStyles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "value": field_value == "true" if field_value is not None else False
            }
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "radio":
            field_obj = {
                "type": "radio",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "codeContext": {
                    "name": field_name
                },
                "listItems": [],
                "direction": "vertical"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "dropdown":
            field_obj = {
                "id": self.next_id(),
                "mask": None,
                "size": "md",
                "type": "dropdown",
                "label": label,
                "helpText": hint,
                "styles": None,
                "isMulti": False,
                "isInline": False,
                "direction": "bottom",
                "listItems": [],
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "",
                "selectionFeedback": "top-after-reopen"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "signature":
            field_obj = {
                "type": "signature",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "codeContext": {
                    "name": field_name
                }
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "email":
            field_obj = {
                "type": "text-input",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "example@example.com",
                "inputType": "email"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "phone":
            field_obj = {
                "type": "text-input",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "mask": "(###) ###-####",
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "(123) 456-7890",
                "inputType": "tel"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "address":
            field_obj = {
                "type": "text-area",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "Street address"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
            if validation_rules:
                field_obj["validation"] = validation_rules
        elif field_type == "file":
            field_obj = {
                "type": "file",
                "id": self.next_id(),
                "label": label,
                "helpText": hint,
                "styles": None,
                "codeContext": {
                    "name": field_name
                },
                "accept": field_attributes.get('mediatype', '*/*'),
                "multiple": False,
                "maxSize": None,  # Can be set from mapping if needed
                "validation": validation_rules
            }
            if field_value:
                field_obj["value"] = field_value
            if field_attributes.get('filename'):
                field_obj["filename"] = field_attributes.get('filename')
            if field_attributes.get('size'):
                field_obj["size"] = field_attributes.get('size')
        
        # Apply any additional mappings
        if mapping:
            if mapping.get("required"):
                field_obj["required"] = mapping.get("required")
            if mapping.get("validation"):
                # Merge validation rules from mapping with existing ones
                if "validation" in field_obj:
                    field_obj["validation"].extend(mapping.get("validation", []))
                else:
                    field_obj["validation"] = mapping.get("validation", [])
            if mapping.get("label"):
                field_obj["label"] = mapping.get("label")
            if mapping.get("helpText"):
                field_obj["helpText"] = mapping.get("helpText")
        
        return field_obj
    
    def format_section_name(self, section_name):
        """Format section name for display"""
        # Remove 'section-' prefix if it exists
        if section_name.startswith("section-"):
            section_name = section_name[len("section-"):]
        
        # Replace hyphens with spaces and capitalize each word
        return " ".join(word.capitalize() for word in section_name.split("-"))
    
    def format_field_name(self, field_name):
        """Format field name for display"""
        # Replace hyphens with spaces and capitalize each word
        return " ".join(word.capitalize() for word in field_name.split("-"))

    def extract_dropdown_options(self, field_elem):
        """Extract dropdown options from field element"""
        try:
            options = []
            # Look for items in the resources instance
            resources = self.root.find(".//xf:instance[@id='fr-form-resources']", self.namespaces)
            if resources is not None:
                # Find the field's resource section
                field_resource = resources.find(f".//{field_elem.tag}", self.namespaces)
                if field_resource is not None:
                    # Look for items in the resource section
                    for item in field_resource.findall(".//item", self.namespaces):
                        label = item.find("label", self.namespaces)
                        value = item.find("value", self.namespaces)
                        if label is not None and label.text:
                            options.append({
                                "text": label.text.strip(),
                                "value": value.text.strip() if value is not None and value.text else label.text.strip(),
                                "name": value.text.strip() if value is not None and value.text else label.text.strip()
                            })
            return options
        except Exception as e:
            print(f"Error extracting dropdown options: {e}")
            return []

    def get_field_label(self, field_name):
        """Extract label from form resources"""
        try:
            # Find the field's resource section
            field_resource = self.form_resources.find(f".//{field_name}", self.namespaces)
            if field_resource is not None:
                # Look for label element
                label_elem = field_resource.find("label", self.namespaces)
                if label_elem is not None and label_elem.text:
                    # If label contains HTML, extract text content
                    if "<div>" in label_elem.text:
                        # Remove HTML tags and get text content
                        import re
                        text = re.sub('<[^<]+?>', '', label_elem.text)
                        return text.strip()
                    return label_elem.text.strip()
            return None
        except Exception as e:
            print(f"Error getting field label for {field_name}: {e}")
            return None

    def get_field_hint(self, field_name):
        """Extract hint from form resources"""
        try:
            field_resource = self.form_resources.find(f".//{field_name}", self.namespaces)
            if field_resource is not None:
                hint_elem = field_resource.find("hint", self.namespaces)
                if hint_elem is not None and hint_elem.text:
                    return hint_elem.text.strip()
            return None
        except Exception as e:
            print(f"Error getting field hint for {field_name}: {e}")
            return None 