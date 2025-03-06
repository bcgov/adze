import argparse
import json
import os
import xml.etree.ElementTree as ET
import re
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class XDPToJSONConverter:
    """Converts XDP forms to JSON format based on mapping configuration."""
    
    def __init__(self, mapping_file: str):
        """
        Initialize the converter with mapping configuration.
        
        Args:
            mapping_file: Path to the JSON mapping file.
        """
        self.namespaces = {
            'xdp': 'http://ns.adobe.com/xdp/',
            'template': 'http://www.xfa.org/schema/xfa-template/3.0/'
        }
        # Register namespaces for proper XML parsing
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)
            
        # Load mapping configuration
        self.mapping = self._load_mapping(mapping_file)
    
    def _load_mapping(self, mapping_file: str) -> Dict[str, Any]:
        """
        Load the mapping configuration from a JSON file.
        
        Args:
            mapping_file: Path to the JSON mapping file.
            
        Returns:
            The mapping configuration as a dictionary.
        """
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load mapping file: {e}")
            raise
    
    def _get_value_by_xpath(self, root: ET.Element, xpath_expr: str) -> Optional[str]:
        """
        Get value from XML using XPath expression.
        
        Args:
            root: The root element of the XML.
            xpath_expr: XPath expression to locate the element.
            
        Returns:
            The text value of the element or None if not found.
        """
        try:
            elements = root.findall(xpath_expr, self.namespaces)
            if elements and len(elements) > 0:
                # For text elements, we need to look for the text child
                text_element = elements[0].find(".//template:text", self.namespaces)
                if text_element is not None and text_element.text:
                    return text_element.text
                    
                # If no text element, return the element's text or an empty string
                return elements[0].text or ""
            return None
        except Exception as e:
            logger.warning(f"Error getting value by XPath '{xpath_expr}': {e}")
            return None
    
    def _get_values_by_xpath(self, root: ET.Element, xpath_expr: str) -> List[str]:
        """
        Get multiple values from XML using XPath expression.
        
        Args:
            root: The root element of the XML.
            xpath_expr: XPath expression to locate the elements.
            
        Returns:
            List of text values from matching elements.
        """
        results = []
        try:
            elements = root.findall(xpath_expr, self.namespaces)
            for elem in elements:
                # For text elements, look for the text child
                text_element = elem.find(".//template:text", self.namespaces)
                if text_element is not None and text_element.text:
                    results.append(text_element.text)
                else:
                    # If no text element, use the element's text or an empty string
                    results.append(elem.text or "")
            return results
        except Exception as e:
            logger.warning(f"Error getting values by XPath '{xpath_expr}': {e}")
            return []
    
    def _apply_transformations(self, value: str, transforms: List[Dict[str, Any]]) -> Any:
        """
        Apply transformations to a value according to the mapping rules.
        
        Args:
            value: The input value to transform.
            transforms: List of transformation rules.
            
        Returns:
            The transformed value.
        """
        result = value
        
        for transform in transforms:
            transform_type = transform.get("type")
            
            if transform_type == "regex_extract":
                pattern = transform.get("pattern")
                group = transform.get("group", 1)
                if pattern:
                    match = re.search(pattern, result)
                    if match and len(match.groups()) >= group:
                        result = match.group(group)
            
            elif transform_type == "convert_type":
                target_type = transform.get("target_type")
                if target_type == "int":
                    try:
                        result = int(result)
                    except (ValueError, TypeError):
                        result = transform.get("default", 0)
                elif target_type == "float":
                    try:
                        result = float(result)
                    except (ValueError, TypeError):
                        result = transform.get("default", 0.0)
                elif target_type == "boolean":
                    if isinstance(result, str):
                        result = result.lower() in ("true", "yes", "1", "t", "y")
            
            elif transform_type == "default":
                if result is None or result == "":
                    result = transform.get("value")
            
            elif transform_type == "format_date":
                if isinstance(result, str) and result:
                    input_format = transform.get("input_format", "%Y-%m-%dT%H:%M:%SZ")
                    output_format = transform.get("output_format", "%Y-%m-%dT%H:%M:%S+00:00")
                    try:
                        dt = datetime.strptime(result, input_format)
                        result = dt.strftime(output_format)
                    except ValueError:
                        logger.warning(f"Failed to parse date '{result}' with format '{input_format}'")
            
            elif transform_type == "split":
                delimiter = transform.get("delimiter", ",")
                if isinstance(result, str):
                    result = result.split(delimiter)
            
            elif transform_type == "constant":
                result = transform.get("value")
                
            elif transform_type == "uuid":
                # Generate a UUID (either random or from input value as seed)
                if transform.get("random", True):
                    result = str(uuid.uuid4())
                else:
                    # Create a deterministic UUID using the input as a namespace
                    result = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(result)))
        
        return result
    
    def convert_xdp_to_json(self, xdp_file: str) -> Dict[str, Any]:
        """
        Convert XDP file to JSON format based on mapping.
        
        Args:
            xdp_file: Path to the XDP file to convert.
            
        Returns:
            JSON representation of the form data.
        """
        def element_to_dict(element: ET.Element) -> Dict[str, Any]:
            """
            Convert an XML element and its children to a dictionary.
            
            Args:
                element: The XML element to convert.
                
            Returns:
                A dictionary representation of the XML element.
            """
            node = {}
            if element.text and element.text.strip():
                node['text'] = element.text.strip()
            
            for key, value in element.attrib.items():
                node[key] = value
            
            for child in element:
                child_dict = element_to_dict(child)
                child_tag = child.tag.split('}')[-1]  # Remove namespace
                if child_tag not in node:
                    node[child_tag] = child_dict
                else:
                    if not isinstance(node[child_tag], list):
                        node[child_tag] = [node[child_tag]]
                    node[child_tag].append(child_dict)
            
            return node
        
        try:
            # Parse the XDP file
            tree = ET.parse(xdp_file)
            root = tree.getroot()
            
            # Convert the XML to a dictionary
            output_json = element_to_dict(root)
            
            # Apply mappings and transformations
            def apply_mappings(node: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
                result = {}
                for key, value in node.items():
                    if key.startswith('@'):
                        # Preserve attributes as they are
                        result[key] = value
                        continue
                    
                    if key in mapping.get("fields", {}):
                        field_config = mapping["fields"][key]
                        field_name = field_config.get("name", key)
                        if isinstance(value, dict):
                            value = apply_mappings(value, mapping)
                        elif isinstance(value, list):
                            value = [apply_mappings(v, mapping) if isinstance(v, dict) else v for v in value]
                        
                        # Apply transformations if specified in the mapping
                        if field_config.get("transforms"):
                            value = self._apply_transformations(value, field_config["transforms"])
                        
                        if value is None and "default" in field_config:
                            value = field_config["default"]
                        
                        result[field_name] = value
                    else:
                        result[key] = value
                
                # Add constant fields from the mapping
                for field_name, field_config in mapping.get("constants", {}).items():
                    result[field_name] = field_config.get("value")
                
                return result
            
            output_json = apply_mappings(output_json, self.mapping)
            
            return output_json
        except Exception as e:
            logger.error(f"❌ Error converting XDP to JSON: {e}")
            raise
    
    def process_items(self, subform_elem: ET.Element, id: int) -> Dict[str, Any]:
        items_array = []
        for elem in subform_elem.iter():
            element_dict = {}
            element_tag = elem.tag.split('}')[-1]
            if(element_tag == 'pageArea' or element_tag == 'draw'):
                element_dict['type'] = 'group'
                element_dict['label'] = elem.get('name')
                element_dict['id'] = id
                id += 1
                element_dict['groupId'] = '12'
                element_dict['repeater'] = False
                element_dict['codeContext'] = {
                    'name': elem.get('attrName'),
                }
                group_items_array, id = self.process_group_items(elem, id)
                element_dict['groupItems'] = group_items_array

            if element_dict:
                items_array.append(element_dict)
                
            

        return items_array, id

    def process_group_items(self, group_elem: ET.Element, id: int) -> List[Dict[str, Any]]:
        items_array = []
        for elem in group_elem.iter():
            element_dict = {}
            element_tag = elem.tag.split('}')[-1]
            
            if(element_tag == 'draw'):
                element_dict = self.process_draw(element_dict,elem,id)
                id += 1
            if(element_tag == 'field'):
                element_dict = self.process_field(element_dict,elem,id)
                id += 1
               
            if element_dict:
                items_array.append(element_dict)
        
        return items_array, id
    
    def process_field(self, element_dict: Dict[str, Any], elem: ET.Element, id: int) -> Dict[str, Any]:
        element_dict['type'] = 'field'
        element_dict['label'] = elem.get('name')
        element_dict['codeContext'] = {
            'name' :elem.get('id')
        }
        element_dict['repeater'] = 'false'
        element_dict['groupId'] = '12'
        element_dict['id'] = id

        return element_dict
    
    def process_draw(self, element_dict: Dict[str, Any], elem: ET.Element, id: int) -> Dict[str, Any]:
        element_dict['type'] = 'text-info'
        element_dict['label'] = elem.get('name')
        element_dict['codeContext'] = {
            'name' :elem.get('id')
        }
        element_dict['repeater'] = 'false'
        element_dict['groupId'] = '12'
        element_dict['id'] = id

        return element_dict

    def convert_xdp_to_json_custom(self, xdp_file: str) -> Dict[str, Any]:


        tree = ET.parse(xdp_file)
        root = tree.getroot()
        id = 1

        output_json = {}
        for elem in root.iter():
            element_tag = elem.tag.split('}')[-1]
            
            # Process element attributes
            for attr_name, attr_value in elem.attrib.items():
                if attr_name in self.mapping.get("fields", {}):
                    field_config = self.mapping["fields"][attr_name]
                    field_name = field_config.get("name", attr_name)
                    output_json[field_name] = attr_value

            # Process elements outside the <subform> tag
            if element_tag in self.mapping.get("fields", {}):
                field_config = self.mapping["fields"][element_tag]
                field_name = field_config.get("name", element_tag)
                output_json[field_name] = elem.text



            # Check if the element matches the desired <subform> tag with the specified attributes
            if (element_tag == 'subform'):        
                print("Found <subform> element!",elem)
                
                # Call another function to parse elements inside the <subform>
                items_dict, id = self.process_items(elem,id)
                # output_json['data'] = items_dict
                if('data' in output_json ):
                    print("if triggered once")
                    if(items_dict):
                        output_json['data']['items'].append(items_dict)
                else:
                    if(items_dict):
                        output_json['data'] = { 'items': items_dict }
                    
                # break  # Stop after finding and processing the first <subform> element
        return output_json

    
            
    
    def process_file(self, xdp_file: str, output_file: Optional[str] = None) -> None:
        """
        Process a single XDP file and output JSON.
        
        Args:
            xdp_file: Path to the XDP file.
            output_file: Optional path to the output JSON file. If None, uses the same base name.
        """
        if not os.path.exists(xdp_file):
            logger.error(f"❌ XDP file not found: {xdp_file}")
            return
        
        if output_file is None:
            output_file = os.path.splitext(xdp_file)[0] + '.json'
        
        try:
            # Convert the XDP to JSON
            json_data = self.convert_xdp_to_json_custom(xdp_file)
            
            # Write the JSON output to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"✅ Successfully converted {xdp_file} to {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to process {xdp_file}: {e}")
    
    def process_directory(self, input_dir: str, output_dir: str) -> None:
        """
        Process all XDP files in a directory.
        
        Args:
            input_dir: Directory containing XDP files.
            output_dir: Directory for output JSON files.
        """
        if not os.path.isdir(input_dir):
            logger.error(f"❌ Input directory not found: {input_dir}")
            return
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Process all XDP files in the input directory
        files_processed = 0
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.xdp'):
                input_file = os.path.join(input_dir, filename)
                output_file = os.path.join(output_dir, os.path.splitext(filename)[0] + '.json')
                
                self.process_file(input_file, output_file)
                files_processed += 1
        
        logger.info(f"Processed {files_processed} XDP files")


def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description='Convert XDP forms to JSON format using a mapping file')
    
    # Define command line arguments
    parser.add_argument('--mapping', '-m', required=True, 
                      help='Path to the JSON mapping file')
    parser.add_argument('--file', '-f', 
                      help='Path to a single XDP file to convert')
    parser.add_argument('--input-dir', '-i', 
                      help='Directory containing XDP files to convert')
    parser.add_argument('--output-dir', '-o', 
                      help='Directory for output JSON files')
    parser.add_argument('--output', 
                      help='Output file for single file conversion')
    parser.add_argument('--verbose', '-v', action='store_true', 
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate arguments
    if not args.mapping:
        logger.error("❌ Mapping file is required")
        return 1
    
    if not args.file and not args.input_dir:
        logger.error("❌ Either --file or --input-dir must be specified")
        parser.print_help()
        return 1
    
    if args.input_dir and not args.output_dir:
        logger.error("❌ Output directory is required when processing a directory")
        return 1
    
    # Initialize converter
    try:
        converter = XDPToJSONConverter(args.mapping)
    except Exception as e:
        logger.error(f"❌ Failed to initialize converter: {e}")
        return 1
    
    # Process files based on arguments
    try:
        if args.file:
            # Single file mode
            converter.process_file(args.file, args.output)
        else:
            # Directory mode
            converter.process_directory(args.input_dir, args.output_dir)
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())