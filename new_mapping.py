import xml.etree.ElementTree as ET
import json
import os
from functools import lru_cache
from map_element_to_json import ElementToJSONMapper

breadcrumb = ""

def add_breadcrumb(tag):
    global breadcrumb
    breadcrumb += f"<{tag}>"
    if len(breadcrumb) > 200:
        breadcrumb = breadcrumb[-200:]

def get_breadcrumb():
    global breadcrumb
    return breadcrumb

@lru_cache(maxsize=1)
def extract_namespaces(root):
    """Extract namespace mappings from XML document"""
    namespaces = {}
    
    for elem in root.iter():
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

def load_mapping_file(mapping_file):
    """Load field mapping configuration"""
    if not os.path.exists(mapping_file):
        raise FileNotFoundError(f"Mapping file {mapping_file} not found")
    
    with open(mapping_file, 'r') as f:
        return json.load(f)
    
def check_mappings(mapping):
    """Check if mappings match breadcrumbs"""
    breadcrumbs = get_breadcrumb()
    for mapping_item in mapping["mappings"]:
        if breadcrumbs.endswith(mapping_item['xmlPath']):
            return True, mapping_item
    return False, None

def process_children(child, namespaces, mapping):
    items = []
    element_tag = child.tag.split('}')[-1]
    print(f"Tag: {element_tag}")
    add_breadcrumb(element_tag)
    
    # check if mappings match breadcrumbs
    mapping_found, mapping_item = check_mappings(mapping)
    mapping_class = ElementToJSONMapper(mapping)

    # if mappings match, process children
    if(mapping_found):
        mapping_class.map_element_to_json(child, mapping_item)
        mapped_json = mapping_class.items
        items.append(mapped_json)

    return mapping_class.get_items()

# Load the xml file and convert it to json
def load_xml(file_name, mapping_file='field_mappings.json'):
    """Main function to convert XML to JSON"""
    try:
        # Parse XML and load mapping
        tree = ET.parse(file_name)
        root = tree.getroot()
        mapping = load_mapping_file(mapping_file)
        namespaces = extract_namespaces(root)
        output_json = {
            "version": mapping["constants"]["version"],
            "ministry_id": mapping["constants"]["ministry_id"],
        }
        root_subform = root.find(".//template:subform",namespaces)

        # Loop through and print each element in the XML
        # for elem in root_subform.iter():
        #     element_tag = elem.tag.split('}')[-1]
        #     breadcrumbs += f"<{element_tag}>"
        #     if len(breadcrumbs) > 200:
        #         breadcrumbs = breadcrumbs[-200:]
        #     print(f"Tag: {element_tag}, Attributes: {elem.attrib}, Text: {elem.text}")

        # root_subform is template > subform
        # root_children is the children of subform
        root_children = root_subform.findall("*",namespaces)
        # print(f"Root children: {root_children}")
        items = []
        for child in root_children:

            retuned_items = process_children(child, namespaces, mapping)
            if retuned_items:
                items.extend(retuned_items)

        output_json["items"] = items
        # Write output
        with open('mapping_output.json', 'w') as json_file:
            json.dump(output_json, json_file, indent=4)

        # if log true
            # compare
        print(f"items: {items}")
        return output_json
        
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None
if __name__ == "__main__":
    file_path = './sample_pdfs/eg medium-complexity-A HR0077.xdp'
    # file_path = './sample_pdfs/eg medium-complexity-B HR0095.xdp'
    result = load_xml(file_path, 'new_mapping.json')
    print("XML conversion", "successful" if result else "failed")