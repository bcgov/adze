import xml.etree.ElementTree as ET
import re
import json
import os
import uuid as uuid_lib
from datetime import datetime

global_id = 0

def get_id():
    global_id += 1
    return str(global_id)

def load_mapping_file(mapping_file):
    """Load the external mapping configuration"""
    if not os.path.exists(mapping_file):
        raise FileNotFoundError(f"Mapping file {mapping_file} not found")
    
    with open(mapping_file, 'r') as f:
        return json.load(f)

def load_xml(file_name, mapping_file='field_mappings.json'):
    try:
        # Load the mapping configuration
        mapping = load_mapping_file(mapping_file)
        namespaces = mapping["namespaces"]
        
        tree = ET.parse(file_name)
        root = tree.getroot()

        # Extract the UUID and timestamp from the root tag
        uuid, timestamp = get_root_attributes(root, namespaces)
        
        # Extract the form ID from the XML
        form_id = get_form_id(root, namespaces, mapping["form_id"])
        
        # Extract the form title from the XML
        form_title = get_form_title(root, namespaces, mapping["form_title"])
        
        # Generate items
        items = generate_form_items(root, namespaces, mapping)

        # Create the output JSON structure
        output_json = {
            'version': mapping["root_config"]["version"],
            'ministry_id': mapping["root_config"]["ministry_id"],
            'id': uuid,
            'lastModified': timestamp,
            'form_id': form_id,
            'title': form_title,
            'deployed_to': mapping["root_config"]["deployed_to"],
            'dataSources': mapping["root_config"]["dataSources"],
            'data': {
                'items': items
            }
        }

        # Write the output to a file
        with open('output.json', 'w') as json_file:
            json.dump(output_json, json_file, indent=4)

        return output_json
        
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None
    
def get_root_attributes(root, namespaces):
    """Extract UUID and timestamp from the root element"""
    # Check if the root tag is <xdp:xdp>
    if root.tag == '{' + namespaces['xdp'] + '}xdp':
        xdp_tag = root
    else:
        # Use find() to search for the <xdp:xdp> tag using the full namespace
        xdp_tag = root.find('.//xdp:xdp', namespaces)

    if xdp_tag is not None:
        if 'uuid' in xdp_tag.attrib and 'timeStamp' in xdp_tag.attrib:
            return xdp_tag.attrib['uuid'], xdp_tag.attrib['timeStamp']
        else:
            # Generate UUID and timestamp if not present
            return str(uuid_lib.uuid4()), datetime.now().isoformat()
    else:
        print("xdp:xdp tag not found, generating default values")
        return str(uuid_lib.uuid4()), datetime.now().isoformat()

def get_form_id(root, namespaces, mapping):
    """Extract form ID using the configured XPath and transformation"""
    form_id_tag = root.find(mapping["xpath"], namespaces)
    
    if form_id_tag is not None:
        # Find the text element using the configured XPath
        text_element = form_id_tag.find(mapping["text_xpath"], namespaces)
        
        if text_element is not None and text_element.text:
            # Apply transformation if configured
            if mapping.get("transform") == "regex" and "pattern" in mapping:
                match = re.search(mapping["pattern"], text_element.text)
                if match:
                    return match.group(1)
            else:
                return text_element.text
    
    print("Form ID not found")
    return None

def get_form_title(root, namespaces, mapping):
    """Extract form title using the configured XPath"""
    form_title_tag = root.find(mapping["xpath"], namespaces)
    
    if form_title_tag is not None:
        # Find the text element using the configured XPath
        text_element = form_title_tag.find(mapping["text_xpath"], namespaces)
        
        if text_element is not None and text_element.text:
            return text_element.text
    
    print("Form title not found")
    return None

def generate_form_items(root, namespaces, mapping):
    """Generate the form items array based on mapping configuration"""
    items = []
    
    # Create the master page item (first item)
    master_page = {
        "type": "group",
        "label": "Master Page",
        "id": get_id(),
        "groupId": "12",
        "repeater": False,
        "codeContext": {
            "name": "master_page"
        },
        "groupItems": [{"fields": []}]
    }
    
    # Find the page area
    page_area = root.find(mapping["page_area"]["xpath"], namespaces)
    if page_area is None:
        print("Page area not found")
        return items
    
    # First, add a generic text-info field (id: 2)
    master_page["groupItems"][0]["fields"].append({
        "type": "text-info",
        "id": get_id(),
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
    
    # Process special elements
    for special_element in mapping["special_elements"]:
        # Try to find the element first
        element = root.find(special_element["xpath"], namespaces)
        
        # Create field with the configured or default values
        field = {
            "type": special_element["type"],
            "id": get_id(),
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": special_element["code_context"],
            "helperText": " as it appears on official documents"
        }
        
        # Set value from XML if element exists, otherwise use hardcoded value
        if element is not None and "text_xpath" in special_element:
            text_element = element.find(special_element["text_xpath"], namespaces)
            if text_element is not None and text_element.text:
                field["value"] = text_element.text
        
        # Use hardcoded value if no value found or element doesn't exist
        if "value" not in field or field["value"] is None:
            field["value"] = special_element.get("value")
        
        # Add to master page if ID is 3 or 5, otherwise add to items
        if special_element["id"] in ["3", "5"]:
            master_page["groupItems"][0]["fields"].append(field)
        else:
            items.append(field)
    
    # Add master page to items
    items.insert(0, master_page)
    
    # Process contact section
    contact_section = create_contact_section(root, namespaces, mapping["contact_section"])
    items.append(contact_section)
    
    # Process case info fields
    for case_field in mapping["case_info"]:
        field_element = root.find(case_field["xpath"], namespaces)
        if field_element is not None:
            items.append({
                "type": case_field["type"],
                "id": case_field["id"],
                "label": None,
                "helpText": None,
                "styles": None,
                "mask": None,
                "codeContext": case_field["code_context"],
                "placeholder": "Enter your ",
                "helperText": " as it appears on official documents",
                "inputType": "text"
            })
    
    # Add work search table
    work_search_table = create_work_search_table(mapping["work_search_table"])
    items.append(work_search_table)
    
    # Process no search checkboxes
    for checkbox in mapping["no_search_checkboxes"]:
        items.append({
            "type": checkbox["type"],
            "id": checkbox["id"],
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": checkbox["code_context"]
        })
    
    # Add reason text area
    items.append({
        "type": mapping["reason_text_area"]["type"],
        "id": mapping["reason_text_area"]["id"],
        "label": None,
        "helpText": None,
        "styles": None,
        "mask": None,
        "codeContext": mapping["reason_text_area"]["code_context"]
    })
    
    # Add portal declaration section
    portal_declaration = create_declaration_section(mapping["portal_declaration"])
    items.append(portal_declaration)
    
    # Add Siebel declaration section
    siebel_declaration = create_declaration_section(mapping["siebel_declaration"])
    items.append(siebel_declaration)
    
    # Add additional field
    items.append({
        "type": mapping["additional_field"]["type"],
        "id": mapping["additional_field"]["id"],
        "label": None,
        "helpText": None,
        "styles": None,
        "mask": None,
        "codeContext": mapping["additional_field"]["code_context"],
        "placeholder": "Enter your ",
        "helperText": " as it appears on official documents",
        "inputType": "text"
    })
    
    # Add submit form section
    submit_form = create_submit_form_section(mapping["submit_form"])
    items.append(submit_form)
    
    return items

def create_contact_section(root, namespaces, mapping):
    """Create the contact information section"""
    contact_section = {
        "type": mapping["type"],
        "label": mapping["label"],
        "id": mapping["id"],
        "groupId": "11",
        "repeater": mapping["repeater"],
        "codeContext": mapping["code_context"],
        "groupItems": [{"fields": []}]
    }
    
    for field in mapping["fields"]:
        field_obj = {
            "type": field["type"],
            "id": field["id"],
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": field["code_context"]
        }
        
        # Add databindings if present
        if "databindings" in field:
            field_obj["databindings"] = field["databindings"]
            
        # Add placeholder and helperText for text inputs
        if field["type"] == "text-input":
            field_obj["placeholder"] = "Enter your "
            field_obj["helperText"] = " as it appears on official documents"
            field_obj["inputType"] = "text"
            
        contact_section["groupItems"][0]["fields"].append(field_obj)
    
    return contact_section

def create_work_search_table(mapping):
    """Create the work search table section"""
    work_search_table = {
        "type": mapping["type"],
        "label": mapping["label"],
        "id": mapping["id"],
        "groupId": "1",
        "repeater": mapping["repeater"],
        "codeContext": mapping["code_context"],
        "groupItems": [{"fields": []}]
    }
    
    for field in mapping["fields"]:
        field_obj = {
            "type": field["type"],
            "id": field["id"],
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": field["code_context"]
        }
        
        # Add placeholder and helperText for text inputs
        if field["type"] == "text-input":
            field_obj["placeholder"] = "Enter your "
            field_obj["helperText"] = " as it appears on official documents"
            field_obj["inputType"] = "text"
            
        work_search_table["groupItems"][0]["fields"].append(field_obj)
    
    return work_search_table

def create_declaration_section(mapping):
    """Create a declaration section (Portal or Siebel)"""
    declaration = {
        "type": mapping["type"],
        "label": mapping["label"],
        "id": mapping["id"],
        "groupId": "1",
        "repeater": mapping["repeater"],
        "codeContext": mapping["code_context"],
        "groupItems": [{"fields": []}]
    }
    
    for field in mapping["fields"]:
        field_obj = {
            "type": field["type"],
            "id": field["id"],
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": field["code_context"]
        }
        
        # Add value for text-info
        if field["type"] == "text-info" and "value" in field:
            field_obj["value"] = field["value"]
            field_obj["helperText"] = " as it appears on official documents"
        
        # Add databindings if present
        if "databindings" in field:
            field_obj["databindings"] = field["databindings"]
            
        # Add placeholder and helperText for text inputs
        if field["type"] == "text-input":
            field_obj["placeholder"] = "Enter your "
            field_obj["helperText"] = " as it appears on official documents"
            field_obj["inputType"] = "text"
            
        declaration["groupItems"][0]["fields"].append(field_obj)
    
    return declaration

def create_submit_form_section(mapping):
    """Create the submit form section"""
    submit_form = {
        "type": mapping["type"],
        "label": mapping["label"],
        "id": mapping["id"],
        "groupId": "6",
        "repeater": mapping["repeater"],
        "codeContext": mapping["code_context"],
        "groupItems": [{"fields": []}]
    }
    
    for field in mapping["fields"]:
        field_obj = {
            "type": field["type"],
            "id": field["id"],
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": field["code_context"]
        }
        
        # Add placeholder and helperText for text inputs
        if field["type"] == "text-input":
            field_obj["placeholder"] = "Enter your "
            field_obj["helperText"] = " as it appears on official documents"
            field_obj["inputType"] = "text"
            
        submit_form["groupItems"][0]["fields"].append(field_obj)
    
    return submit_form

if __name__ == "__main__":
    file_path = './sample_pdfs/eg medium-complexity-A HR0077.xdp'
    result = load_xml(file_path, 'field_mappings.json')
    if result is not None:
        print("XML converted to JSON successfully")
    else:
        print("Failed to convert XML to JSON")