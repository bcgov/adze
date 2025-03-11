import xml.etree.ElementTree as ET
import json
import re
import argparse
import os
from datetime import datetime
import uuid

class XMLToJSONConverter:
    def __init__(self, mapping_file=None):
        self.mapping = self.load_mapping(mapping_file) if mapping_file else {}
        self.field_counter = 1
        
    def load_mapping(self, mapping_file):
        """Load mapping configuration from a JSON file if provided"""
        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load mapping file: {e}")
            return {}
    
    def extract_form_id(self, xml_root):
        """Extract form ID from XML"""
        # Look for the form number in the XML
        for elem in xml_root.findall(".//draw"):
            if elem.get('name') == 'formnumber':
                for value in elem.findall(".//value"):
                    for text in value.findall(".//text"):
                        if text.text:
                            # Extract just the form ID part (e.g., "HR0077" from "HR0077(16/03/07)")
                            match = re.search(r'([A-Z0-9]+)', text.text)
                            if match:
                                return match.group(1)
        
        # If not found, try other methods
        for elem in xml_root.findall(".//text"):
            if elem.text and re.search(r'HR\d+', elem.text):
                match = re.search(r'(HR\d+)', elem.text)
                if match:
                    return match.group(1)
                
        return "UNKNOWN"
    
    def extract_form_title(self, xml_root):
        """Extract form title from XML"""
        # Look for the form title in the XML
        for elem in xml_root.findall(".//draw"):
            if elem.get('name') == 'FormTitle':
                for value in elem.findall(".//value"):
                    for text in value.findall(".//text"):
                        if text.text:
                            return text.text
        
        # If not found, try other methods
        for elem in xml_root.findall(".//text"):
            if elem.text and "WORK SEARCH ACTIVITIES RECORD" in elem.text:
                return "Work Search Activities Record"
                
        return "Unknown Form Title"
    
    def find_all_fields(self, xml_root):
        """Find all field elements in the XML"""
        fields = []
        
        # Extract all field elements
        fields.extend(xml_root.findall(".//field"))
        
        # Extract all draw elements that contain text (for text-info fields)
        for draw_elem in xml_root.findall(".//draw"):
            for value in draw_elem.findall(".//value"):
                for text in value.findall(".//text"):
                    if text.text:
                        fields.append(draw_elem)
                        break
                
        return fields
    
    def determine_field_type(self, field_elem):
        """Determine the type of field based on XML structure"""
        # Check for draw elements (text display)
        if field_elem.tag.endswith('draw'):
            return "text-info"
        
        # Check for different UI elements
        ui_elem = field_elem.find("./ui")
        if ui_elem is not None:
            if ui_elem.find("./checkButton") is not None:
                return "checkbox"
            elif ui_elem.find("./dateTimeEdit") is not None:
                return "date"
            elif ui_elem.find("./button") is not None:
                return "button"
            elif ui_elem.find("./textEdit") is not None:
                # Check if it's multiline
                text_edit = ui_elem.find("./textEdit")
                if text_edit is not None and text_edit.get('multiLine') == '1':
                    return "text-area"
                else:
                    return "text-input"
        
        # Default type
        return "text-input"
    
    def extract_label(self, field_elem):
        """Extract label from field element"""
        # For regular fields
        caption = field_elem.find("./caption/value/text")
        if caption is not None and hasattr(caption, 'text'):
            return caption.text.strip()
        
        # For draw elements with text
        if field_elem.tag.endswith('draw'):
            for value in field_elem.findall("./value"):
                for text in value.findall("./text"):
                    if text.text:
                        return text.text.strip()
        
        return None
    
    def extract_value(self, field_elem):
        """Extract value from field element"""
        # For draw elements
        if field_elem.tag.endswith('draw'):
            for value in field_elem.findall("./value"):
                for text in value.findall("./text"):
                    if text.text:
                        return text.text
                        
        # For regular fields
        value_elem = field_elem.find("./value")
        if value_elem is not None:
            text_elem = value_elem.find("./text")
            if text_elem is not None and hasattr(text_elem, 'text'):
                return text_elem.text
                
        return None
    
    def extract_help_text(self, field_elem):
        """Extract help text from field element"""
        assist = field_elem.find("./assist/speak")
        if assist is not None and hasattr(assist, 'text'):
            return assist.text
        return None
    
    def extract_bind_path(self, field_elem):
        """Extract binding path from field element"""
        bind = field_elem.find("./bind")
        if bind is not None:
            return bind.get('ref')
        return None
    
    def map_code_context(self, field_elem):
        """Map field to code context based on field name or other attributes"""
        field_name = field_elem.get('name', '')
        
        # Check mapping file first
        if field_name in self.mapping:
            return self.mapping[field_name]
        
        # For draw elements (text display)
        if field_elem.tag.endswith('draw'):
            return {"name": "generic_text_display"}
        
        # Default context
        context_map = {"name": "generic_text_input"}
        
        # Apply mappings based on field name patterns
        field_name_lower = field_name.lower()
        
        if "first" in field_name_lower and "name" in field_name_lower:
            context_map["name"] = "contact_first_name"
        elif "last" in field_name_lower and "name" in field_name_lower:
            context_map["name"] = "contact_last_name"
        elif "full" in field_name_lower and "name" in field_name_lower:
            context_map["name"] = "contact_full_name"
        elif "postal" in field_name_lower or "zip" in field_name_lower:
            context_map["name"] = "contact_postal"
        elif "phone" in field_name_lower or "telephone" in field_name_lower:
            context_map["name"] = "phone_number"
        elif "date" in field_name_lower:
            if "birth" in field_name_lower:
                context_map["name"] = "contact_date_of_birth"
            elif "sign" in field_name_lower:
                context_map["name"] = "signature_date"
            else:
                context_map["name"] = "generic_date"
        elif "case" in field_name_lower and "num" in field_name_lower:
            context_map["name"] = "case_number"
        elif "sr" in field_name_lower and "num" in field_name_lower:
            context_map["name"] = "sr_number"
        elif "check" in field_name_lower:
            context_map["name"] = "generic_checkbox"
        elif "button" in field_name_lower or "submit" in field_name_lower:
            if "submit" in field_name_lower:
                context_map["name"] = "submit"
            elif "cancel" in field_name_lower:
                context_map["name"] = "cancel"
            else:
                context_map["name"] = "generic_button"
        elif "addr" in field_name_lower:
            context_map["name"] = "contact_address"
        elif "agree" in field_name_lower:
            context_map["name"] = "agreement"
        elif "sign" in field_name_lower:
            context_map["name"] = "signature"
        
        return context_map
    
    def create_field_object(self, field_elem):
        """Create a field object from a field element"""
        field_type = self.determine_field_type(field_elem)
        field_name = field_elem.get('name', '')
        
        if not field_name and field_type == "text-info":
            # Generate a unique ID for text-info fields
            field_name = f"field{self.field_counter}"
            self.field_counter += 1
        
        field_data = {
            "id": field_name,
            "type": field_type,
            "label": self.extract_label(field_elem),
            "helpText": self.extract_help_text(field_elem),
            "styles": None,
            "mask": None,
            "codeContext": self.map_code_context(field_elem)
        }
        
        # Add value for text-info fields
        if field_type == "text-info":
            field_data["value"] = self.extract_value(field_elem)
            field_data["helperText"] = " as it appears on official documents"
        
        # Add databindings if available
        bind_path = self.extract_bind_path(field_elem)
        if bind_path:
            # Determine source type based on bind path
            source_type = "Generic"
            if "Contact" in bind_path:
                source_type = "Contact"
            elif "ServiceRequest" in bind_path:
                source_type = "Service Request"
            
            field_data["databindings"] = {
                "source": source_type,
                "path": bind_path
            }
        
        # Add additional fields for input types
        if field_type in ["text-input", "text-area"]:
            field_data["placeholder"] = "Enter your "
            field_data["helperText"] = " as it appears on official documents"
            if field_type == "text-input":
                field_data["inputType"] = "text"
        
        return field_data
    
    def extract_fields(self, xml_root):
        """Extract form fields from XML"""
        self.field_counter = 1  # Reset counter
        fields = []
        
        # Find all field elements
        field_elements = self.find_all_fields(xml_root)
        
        # Create field objects
        for field_elem in field_elements:
            field_data = self.create_field_object(field_elem)
            if field_data:
                fields.append(field_data)
        
        return fields
    
    def extract_foi_statement(self, fields):
        """Extract FOI statement from fields"""
        for field in fields:
            if field.get("type") == "text-info" and field.get("value"):
                value = field.get("value", "").lower()
                if "personal information" in value and "privacy" in value:
                    field_copy = field.copy()
                    field_copy["codeContext"] = {"name": "foi_statement"}
                    return field_copy
        return None
    
    def create_master_page_group(self, fields, form_title):
        """Create master page group from fields"""
        # Find form title field
        title_field = None
        for field in fields:
            if field.get("type") == "text-info" and field.get("value"):
                if form_title.lower() in field.get("value", "").lower():
                    title_field = field.copy()
                    title_field["codeContext"] = {"name": "form_title"}
                    break
        
        # Find mandatory statement
        mandatory_field = None
        for field in fields:
            if field.get("type") == "text-info" and field.get("value"):
                value = field.get("value", "").lower()
                if "mandatory" in value and "form" in value:
                    mandatory_field = field.copy()
                    break
        
        # Create master page items
        master_page_items = []
        
        # Add generic text display for form number
        master_page_items.append({
            "type": "text-info",
            "id": f"field{self.field_counter}",
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": {
                "name": "generic_text_display"
            },
            "value": None,
            "helperText": " as it appears on official documents"
        })
        self.field_counter += 1
        
        # Add form title
        if title_field:
            master_page_items.append(title_field)
        else:
            master_page_items.append({
                "type": "text-info",
                "id": f"field{self.field_counter}",
                "label": None,
                "helpText": None,
                "styles": None,
                "mask": None,
                "codeContext": {
                    "name": "form_title"
                },
                "value": form_title,
                "helperText": " as it appears on official documents"
            })
            self.field_counter += 1
        
        # Add form instance ID
        master_page_items.append({
            "type": "text-info",
            "id": f"field{self.field_counter}",
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": {
                "name": "form_instance_id"
            },
            "value": None,
            "helperText": " as it appears on official documents"
        })
        self.field_counter += 1
        
        # Add mandatory statement
        if mandatory_field:
            master_page_items.append(mandatory_field)
        
        # Create the group
        return {
            "type": "group",
            "label": "Master Page",
            "id": f"group{self.field_counter}",
            "groupId": "12",
            "repeater": False,
            "codeContext": {
                "name": "master_page"
            },
            "groupItems": [
                {
                    "fields": master_page_items
                }
            ]
        }
    
    def create_contact_info_group(self, fields):
        """Create contact information group"""
        contact_fields = []
        
        # Find contact fields based on codeContext
        for field in fields:
            context_name = field.get("codeContext", {}).get("name", "")
            if context_name.startswith("contact_"):
                contact_fields.append(field)
        
        # Add phone number if found
        phone_fields = [f for f in fields if f.get("codeContext", {}).get("name") == "phone_number"]
        if phone_fields:
            contact_fields.extend(phone_fields)
        
        if contact_fields:
            return {
                "type": "group",
                "label": "Contact Information",
                "id": f"group{self.field_counter}",
                "groupId": "11",
                "repeater": False,
                "codeContext": {
                    "name": "contact_information"
                },
                "groupItems": [
                    {
                        "fields": contact_fields
                    }
                ]
            }
        
        return None
    
    def find_section_header(self, fields, keywords):
        """Find a section header field that contains the specified keywords"""
        for field in fields:
            if field.get("type") == "text-info" and field.get("value"):
                value = field.get("value", "").lower()
                if all(keyword.lower() in value for keyword in keywords):
                    return field
        return None
    
    def create_work_search_group(self, fields):
        """Create work search activity group"""
        # Find date fields for the table
        date_fields = [f for f in fields if f.get("type") == "date"]
        
        # Find text fields for the table
        text_fields = [f for f in fields if f.get("type") in ["text-input", "text-area"]]
        
        if date_fields and text_fields:
            # Create a row with a date field and text fields
            row_fields = []
            
            # Add date field
            if date_fields:
                row_fields.append(date_fields[0])
            
            # Add text fields
            for i, field in enumerate(text_fields):
                if i < 5:  # Limit to 5 text fields per row
                    row_fields.append(field)
            
            if row_fields:
                return {
                    "type": "group",
                    "label": "Table - Work Search Activity",
                    "id": f"group{self.field_counter}",
                    "groupId": "1",
                    "repeater": True,
                    "codeContext": {
                        "name": "generic_group"
                    },
                    "groupItems": [
                        {
                            "fields": row_fields
                        }
                    ]
                }
        
        return None
    
    def create_not_looked_group(self, fields):
        """Create 'if you have not looked for work' section"""
        # Find the section header
        header = self.find_section_header(fields, ["not looked", "work"])
        if not header:
            return None
        
        section_items = [header]
        
        # Find checkboxes
        checkboxes = [f for f in fields if f.get("type") == "checkbox"]
        if checkboxes:
            section_items.extend(checkboxes[:5])  # Add up to 5 checkboxes
        
        # Find text area for "other"
        text_areas = [f for f in fields if f.get("type") == "text-area"]
        if text_areas:
            section_items.append(text_areas[0])
        
        return section_items
    
    def create_portal_group(self, fields):
        """Create portal group with declaration and signature"""
        # Find declaration header
        declaration_header = self.find_section_header(fields, ["declaration"])
        
        if not declaration_header:
            return None
        
        group_fields = [declaration_header]
        
        # Find signature fields
        signature_fields = [f for f in fields if 
                          f.get("codeContext", {}).get("name") in ["signature", "signature_date"]]
        
        group_fields.extend(signature_fields)
        
        # Find agreement checkbox
        agreement_fields = [f for f in fields if f.get("codeContext", {}).get("name") == "agreement"]
        if agreement_fields:
            group_fields.extend(agreement_fields)
        
        if group_fields:
            return {
                "type": "group",
                "label": "Portal",
                "id": f"group{self.field_counter}",
                "groupId": "1",
                "repeater": False,
                "codeContext": {
                    "name": "generic_group"
                },
                "groupItems": [
                    {
                        "fields": group_fields
                    }
                ]
            }
        
        return None
    
    def create_submit_group(self, fields):
        """Create submit form group"""
        # Find submit and cancel buttons
        submit_fields = [f for f in fields if 
                       f.get("codeContext", {}).get("name") in ["submit", "cancel", "generic_button"]]
        
        if submit_fields:
            return {
                "type": "group",
                "label": "Submit Form",
                "id": f"group{self.field_counter}",
                "groupId": "6",
                "repeater": False,
                "codeContext": {
                    "name": "submit_form"
                },
                "groupItems": [
                    {
                        "fields": submit_fields
                    }
                ]
            }
        
        return None
    
    def organize_fields(self, fields, form_title):
        """Organize fields into logical groups and sections"""
        organized_items = []
        
        # Create master page group
        master_page = self.create_master_page_group(fields, form_title)
        if master_page:
            organized_items.append(master_page)
            self.field_counter += 1
        
        # Add FOI statement
        foi_statement = self.extract_foi_statement(fields)
        if foi_statement:
            organized_items.append(foi_statement)
        
        # Create contact information group
        contact_group = self.create_contact_info_group(fields)
        if contact_group:
            organized_items.append(contact_group)
            self.field_counter += 1
        
        # Add work search activities header
        work_header = self.find_section_header(fields, ["work search activities"])
        if work_header:
            organized_items.append(work_header)
        
        # Add case number and SR number fields
        case_fields = [f for f in fields if 
                     f.get("codeContext", {}).get("name") in ["case_number", "sr_number"]]
        organized_items.extend(case_fields)
        
        # Add examples of work search activities
        examples = self.find_section_header(fields, ["examples", "work search"])
        if examples:
            organized_items.append(examples)
        
        # Add instructions
        instructions = self.find_section_header(fields, ["instructions"])
        if instructions:
            organized_items.append(instructions)
        
        # Add work search activity table
        work_group = self.create_work_search_group(fields)
        if work_group:
            organized_items.append(work_group)
            self.field_counter += 1
        
        # Add "add additional pages" text
        additional_pages = self.find_section_header(fields, ["additional pages"])
        if additional_pages:
            organized_items.append(additional_pages)
        
        # Add "if you have not looked for work" section
        not_looked_items = self.create_not_looked_group(fields)
        if not_looked_items:
            organized_items.extend(not_looked_items)
        
        # Add portal group
        portal_group = self.create_portal_group(fields)
        if portal_group:
            organized_items.append(portal_group)
            self.field_counter += 1
        
        # Add submit group
        submit_group = self.create_submit_group(fields)
        if submit_group:
            organized_items.append(submit_group)
            self.field_counter += 1
        
        return organized_items
    
    def convert(self, xml_file, output_file=None):
        """Convert XML form to JSON structure"""
        try:
            # Parse XML
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Extract form metadata
            form_id = self.extract_form_id(root)
            form_title = self.extract_form_title(root)
            
            # Extract fields
            fields = self.extract_fields(root)
            
            # Organize fields into logical groups
            organized_items = self.organize_fields(fields, form_title)
            
            # Create the final JSON structure
            json_data = {
                "version": 8,
                "ministry_id": 2,  # This could come from the mapping file
                "id": str(uuid.uuid4()),
                "lastModified": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "title": form_title,
                "form_id": form_id,
                "deployed_to": None,
                "dataSources": [],
                "data": {
                    "items": organized_items
                }
            }
            
            # Write to output file if specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)
                print(f"Output written to {output_file}")
            
            return json_data
            
        except Exception as e:
            print(f"Error converting XML to JSON: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    parser = argparse.ArgumentParser(description='Convert XML forms to JSON format')
    parser.add_argument('xml_file', help='Input XML file path')
    parser.add_argument('-o', '--output', help='Output JSON file path')
    parser.add_argument('-m', '--mapping', help='Mapping configuration file (JSON)')
    
    args = parser.parse_args()
    
    # Default output filename if not specified
    output_file = args.output
    if not output_file:
        base_name = os.path.splitext(os.path.basename(args.xml_file))[0]
        output_file = f"{base_name}.json"
    
    converter = XMLToJSONConverter(args.mapping)
    converter.convert(args.xml_file, output_file)

if __name__ == "__main__":
    main()