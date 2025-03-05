import xml.etree.ElementTree as ET
import re
import json

def load_xml(file_name):
    try:
        tree = ET.parse(file_name)
        root = tree.getroot()

        namespaces = {
            'xdp': 'http://ns.adobe.com/xdp/',
            'template': 'http://www.xfa.org/schema/xfa-template/3.0/'
        }

        # Extract the UUID and timestamp from the root tag
        uuid, timestamp = get_root_attributes(root,namespaces)
        # Extract the form ID from the XML
        form_id = get_form_id(root,namespaces)
        # Extract the form title from the XML
        form_title = get_form_title(root,namespaces)
        # Generate items
        items = generate_form_items(root,namespaces)

        output_json = {
            'version' : 8,
            'ministry_id' : 2,
            'id' : uuid,
            'lastModified' : timestamp,
            'form_id' : form_id,
            'title' : form_title,
            'deployed_to': None,
            'dataSources': [],
            'data' : {
                'items': items
            }
        }

        # print(f"Output JSON: {output_json}")

        with open('output.json', 'w') as json_file:
            json.dump(output_json, json_file, indent=4)

        return root
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None
    
def get_root_attributes(root, namespaces):
    # Check if the root tag is <xdp:xdp>
    if(root.tag == '{http://ns.adobe.com/xdp/}xdp'):
        xdp_tag = root
    else:
        # Use find() to search for the <xdp:xdp> tag using the full namespace
        xdp_tag = root.find('.//xdp:xdp', namespaces)

    if xdp_tag is not None:
        print(f"Found xdp:xdp tag with uuid: {xdp_tag.attrib['uuid']}")
    else:
        print("xdp:xdp tag not found")
    
    return xdp_tag.attrib['uuid'],xdp_tag.attrib['timeStamp']



def get_form_id(root, namespaces):

    form_id_tag = root.find('.//template:draw[@name="formnumber"]', namespaces)
    
    if form_id_tag is not None:
        if form_id_tag is not None:
            # Find the text element within the value element
            text_element = form_id_tag.find('.//template:text', namespaces)
            
            if text_element is not None and text_element.text:
                # Extract form number using regex
                match = re.search(r'([A-Z]+\d+)', text_element.text)
                if match:
                    return match.group(1)
        
        return None
    else:
        print("Form number not found")


def get_form_title(root, namespaces):

    form_id_tag = root.find('.//template:draw[@name="FormTitle"]', namespaces)
    
    if form_id_tag is not None:
        # Find the text element within the value element
        text_element = form_id_tag.find('.//template:text', namespaces)
        
        if text_element is not None and text_element.text:
            # Extract form number using regex
            return text_element.text
    
    else:
        return None
        print("Form number not found")

def generate_form_items(root,namespaces):
    items = []
    found_item = root.find('.//template:pageArea[@id="Page1"]', namespaces)
    if found_item is not None:
        converted_item = convert_item_to_json(found_item,namespaces)
        items.append(converted_item)
    return items

def convert_item_to_json(item,namespaces):
    item_json = {
        "type": "group",
        "label": "Master Page",
        "id": "1",
        "groupId": "12",
        "repeater": False,
        "codeContext": {
            "name": "master_page"
        },
        "groupItems": [ {"fields" : []}]
    }
    for child in item:
        if child is not None:
            converted_child_item = convert_child_item_to_json(child,namespaces)
            if converted_child_item is not None:
                item_json['groupItems'][0]['fields'].append(converted_child_item)

    return item_json

def convert_child_item_to_json(child,namespaces):
    child_tag = child.tag.split('}')[-1]
    match child_tag:
        case 'contentArea':
            return convert_content_area_to_json(child,namespaces)
        case 'draw':
            return convert_draw_to_json(child,namespaces)
        case 'field':
            return convert_field_to_json(child,namespaces)
        case _:
            return None

def convert_content_area_to_json(content_area,namespaces):
    content_area_json = {
        "type": "text-info",
        "id": "2",
        "label": None,
        "helpText": None,
        "styles": None,
        "mask": None,
        "codeContext": {
            "name": "generic_text_display"
        },
        "value": None,
        "helperText": " as it appears on official documents"
    }
    return content_area_json

def convert_draw_to_json(draw,namespaces):
    # print(f"Draw tag: {draw.attrib}")
    draw_text = draw.find('.//template:text',namespaces)
    if draw_text is not None:
        print(f"Draw text: {draw_text.text}")
    draw_json = {
        "type": "text-info",
        "id": "2",
        "label": None,
        "helpText": None,
        "styles": None,
        "mask": None,
        "codeContext": {
            "name": "form_title"
        },
        "value": draw_text.text if draw_text is not None else None,
        "helperText": " as it appears on official documents"
    }
    return draw_json

def convert_field_to_json(field,namespaces):
    field_json = {
        "type": "text-info",
        "id": "2",
        "label": None,
        "helpText": None,
        "styles": None,
        "mask": None,
        "codeContext": {
            "name": "form_title"
        },
        "value": field.text,
        "helperText": " as it appears on official documents"
    }
    return field_json

if __name__ == "__main__":
    file_path = './sample_pdfs/eg medium-complexity-A HR0077.xdp'
    root = load_xml(file_path)
    if root is not None:
        print("XML loaded successfully")
        # You can now work with the XML data
    else:
        print("Failed to load XML")