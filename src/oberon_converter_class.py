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
                'fb': 'http://orbeon.org/oxf/xml/form-builder'
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

            # Output JSON structure
            self.output_json = self.create_output_structure()
            self.all_items = []
            self.Report = Report(xml_filename)
        except Exception as e:
            print(f"Error initializing OberonParser: {e}")
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
                "version": None,
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
            
            # Create a group for the section if it has fields
            if fields:
                group = {
                    "type": "group",
                    "label": self.format_section_name(section_name),
                    "id": self.next_id(),
                    "groupId": "1",
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
            
            # Find mapping for this field
            mapping = self.find_mapping_for_path(current_path)
            
            # Check if field is bound to an input
            if mapping is None:
                # Try to determine field type based on naming conventions
                if field_name.endswith("-label") or "label-" in field_name:
                    field_type = "text-info"
                elif field_name.endswith("-date") or "date-" in field_name:
                    field_type = "date"
                elif field_name.endswith("-checkbox") or field_name.endswith("-confirmation"):
                    field_type = "checkbox"
                elif "dropdown" in field_name or "list" in field_name:
                    field_type = "dropdown"
                elif "text-area" in field_name:
                    field_type = "text-area"
                else:
                    field_type = "text-input"
            else:
                field_type = mapping.get("fieldType", "text-input")
            
            # Create the field object based on type
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
                if field_value:
                    field_obj["value"] = field_value
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
                if field_value:
                    field_obj["value"] = field_value
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
                if field_value:
                    field_obj["value"] = field_value
            
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