import xml.etree.ElementTree as ET
import json
import os
import uuid
from datetime import datetime
from report import Report

class OberonParser:
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
            
            # Get form instance - the main data container in Oberon
            self.form_instance = self.root.find(".//xf:instance[@id='fr-form-instance']", self.namespaces)
            if self.form_instance is None:
                raise ValueError("Form instance not found in Oberon XML")
                
            self.form_data = self.form_instance.find(".//form", self.namespaces)
            if self.form_data is None:
                raise ValueError("Form data not found in Oberon XML")

            # Find bind elements for additional metadata
            self.form_binds = self.root.find(".//xf:bind[@id='fr-form-binds']", self.namespaces)
            self.binds_map = {}
            if self.form_binds is not None:
                self.extract_binds(self.form_binds)

            # Output JSON structure
            self.output_json = self.create_output_structure()
            self.all_items = []
            self.Report = Report(xml_filename)
        except Exception as e:
            print(f"Error initializing OberonParser: {e}")
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
            # Extract form ID from filename or default
            form_id = os.path.splitext(os.path.basename(self.xml_filename))[0]  # Remove extension
            
            # Get form title if available
            form_title = "Form"  # Default title
            title_elem = self.root.find(".//xh:title", self.namespaces)
            if title_elem is not None and title_elem.text:
                form_title = title_elem.text
            
            return {
                "version": self.mapping["constants"]["version"],
                "ministry_id": self.mapping["constants"]["ministry_id"],
                "id": None,
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": form_title,
                "form_id": form_id,
                "deployed_to": None,
                "dataSources": []
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
            
            # Get section contents
            fields = []
            
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
                        self.process_grid_iteration(iteration, fields)
                else:
                    # Regular grid with fields
                    for field_elem in grid:
                        field_obj = self.process_field(field_elem)
                        if field_obj:
                            fields.append(field_obj)
                
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
            
            # Create a group for the section if it has fields
            if fields:
                group = {
                    "type": "group",
                    "label": self.format_section_name(section_name),
                    "id": self.next_id(),
                    "groupId": self.determine_group_id(section_name),
                    "repeater": False,
                    "codeContext": {
                        "name": section_name
                    },
                    "groupItems": [
                        {
                            "fields": fields
                        }
                    ]
                }
                self.all_items.append(group)
            
            self.remove_breadcrumb(section_name)
        except Exception as e:
            print(f"Error processing section {section.tag if hasattr(section, 'tag') else 'unknown'}: {e}")
    
    def determine_group_id(self, section_name):
        """Determine group ID based on section name"""
        if "child" in section_name.lower():
            return "20"  # Child section
        elif "parent" in section_name.lower() or "guardian" in section_name.lower():
            return "11"  # Parent/Guardian section 
        elif "household" in section_name.lower():
            return "30"  # Household section
        elif "confirmation" in section_name.lower() or "consent" in section_name.lower():
            return "50"  # Confirmations/Consent section
        elif "instruction" in section_name.lower():
            return "5"   # Instructions section
        elif "physician" in section_name.lower() or "practitioner" in section_name.lower():
            return "40"  # Medical practitioner section
        else:
            return "1"   # Default group ID
    
    def process_grid_iteration(self, iteration, fields):
        try:
            """Process a grid iteration (repeating fields)"""
            for field_elem in iteration:
                field_obj = self.process_field(field_elem)
                if field_obj:
                    fields.append(field_obj)
        except Exception as e:
            print(f"Error processing grid iteration: {e}")
    
    def process_field(self, field_elem):
        try:
            """Process a field element"""
            field_name = field_elem.tag
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
            
            # Create the field object based on type
            field_obj = self.create_field_object(field_type, field_name, field_value, field_attributes, mapping)
            
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
        """Determine field type based on naming conventions, attributes, and mapping"""
        # If mapping provides a specific field type, use it
        if mapping and mapping.get("fieldType"):
            return mapping.get("fieldType")
        
        # Check for resource type fields (images, etc.)
        if "filename" in field_attributes and "mediatype" in field_attributes:
            return "resource"
        
        # Check for boolean fields
        if field_value == "true" or field_value == "false":
            return "checkbox"
            
        # Check field name patterns
        if field_name.endswith("-label") or "label-" in field_name:
            return "text-info"
        elif "-date" in field_name:
            return "date"
        elif "confirmation" in field_name:
            return "checkbox"
        elif "checklist" in field_name:
            return "dropdown"
        elif "dropdown" in field_name or "list" in field_name:
            return "dropdown"
        elif "text-area" in field_name or "description" in field_name or field_name.endswith("-needs"):
            return "text-area"
        elif "signature" in field_name:
            return "signature"
        elif "email" in field_name:
            return "email"
        elif "phone" in field_name:
            return "phone"
        elif "address" in field_name:
            return "address"
        elif "city" in field_name or "postcode" in field_name:
            return "text-input"
        elif "name" in field_name:
            return "text-input"
        else:
            return "text-input"
    
    def create_field_object(self, field_type, field_name, field_value, field_attributes, mapping):
        """Create field object based on field type"""
        field_obj = None
        
        if field_type == "text-info":
            field_obj = {
                "type": "text-info",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "value": field_value,
                "helperText": None
            }
        elif field_type == "text-input":
            field_obj = {
                "type": "text-input",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": None,
                "helperText": None,
                "inputType": "text"
            }
            if field_value:
                field_obj["value"] = field_value
        elif field_type == "resource":
            field_obj = {
                "type": "resource",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "codeContext": {
                    "name": field_name
                },
                "filename": field_attributes.get("filename", ""),
                "mediatype": field_attributes.get("mediatype", ""),
                "size": field_attributes.get("size", ""),
                "value": field_value
            }
        elif field_type == "text-area":
            field_obj = {
                "type": "text-area",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": None,
                "helperText": None
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        elif field_type == "date":
            # Default date validation rules
            validation_rules = [
                {
                    "type": "required",
                    "value": True,
                    "errorMessage": "Date should be submitted"
                }
            ]
            
            field_obj = {
                "type": "date",
                "id": self.next_id(),
                "fieldId": self.next_id(),
                "label": self.format_field_name(field_name),
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
                "label": self.format_field_name(field_name),
                "helperText": "",
                "webStyles": None,
                "pdfStyles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "value": field_value == "true" if field_value is not None else False
            }
        elif field_type == "dropdown":
            field_obj = {
                "id": self.next_id(),
                "mask": None,
                "size": "md",
                "type": "dropdown",
                "label": self.format_field_name(field_name),
                "styles": None,
                "isMulti": False,
                "helpText": None,
                "isInline": False,
                "direction": "bottom",
                "listItems": [],
                "helperText": "",
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "",
                "selectionFeedback": "top-after-reopen"
            }
            
            # Add value if present
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        elif field_type == "signature":
            field_obj = {
                "type": "signature",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "codeContext": {
                    "name": field_name
                }
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        elif field_type == "email":
            field_obj = {
                "type": "text-input",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "example@example.com",
                "helperText": None,
                "inputType": "email"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        elif field_type == "phone":
            field_obj = {
                "type": "text-input",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "mask": "(###) ###-####",
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "(123) 456-7890",
                "helperText": None,
                "inputType": "tel"
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        elif field_type == "address":
            field_obj = {
                "type": "text-area",
                "id": self.next_id(),
                "label": self.format_field_name(field_name),
                "helpText": None,
                "styles": None,
                "codeContext": {
                    "name": field_name
                },
                "placeholder": "Street address",
                "helperText": None
            }
            if field_value and field_value.strip():
                field_obj["value"] = field_value.strip()
        
        # Apply any additional mappings
        if mapping:
            if mapping.get("required"):
                field_obj["required"] = mapping.get("required")
            if mapping.get("validation"):
                field_obj["validation"] = mapping.get("validation")
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