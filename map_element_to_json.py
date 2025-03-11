class ElementToJSONMapper:
    def __init__(self, mapping_config):
        self.breadcrumbs = ""
        self.items = []
        self.id = 0
        self.mapping_config = mapping_config
        self.constants = mapping_config.get("constants", {})

    def fetch_id(self):
        self.id += 1
        return self.id

    def add_breadcrumb(self, element_tag):
        """Add breadcrumb"""
        self.breadcrumbs += f"<{element_tag}>"
        if len(self.breadcrumbs) > 200:
            self.breadcrumbs = self.breadcrumbs[-200:]
    
    def get_breadcrumb(self):
        """Get breadcrumb"""
        return self.breadcrumbs

    def get_items(self):
        """Get items"""
        return self.items
    
    def extract_json(self, input_string):
        # Split the input string by comma and strip whitespace
        parts = [part.strip() for part in input_string.split(',', 1)]
        if len(parts) != 2:
            return input_string, None
        
        outer_key, inner_value = parts
        return outer_key, inner_value
    
    def find_mapping_for_path(self, path):
        """Find matching mapping configuration for the given path"""
        for mapping in self.mapping_config.get("mappings", []):
            if mapping.get("xmlPath") == path:
                return mapping
        return None
    
    def get_value_from_element(self, element, method, attr_name=None):
        """Extract value based on translation method"""
        if method == "Tag Exists":
            return True
        elif method == "Value X Between Tags":
            return element.text if element.text else None
        elif method == "Value X in Attribute" and attr_name:
            return element.attrib.get(attr_name)
        return None
    
    def map_element_to_json(self, element, parent_context=None):
        """Map XML element to JSON structure based on mapping configuration"""
        element_tag = element.tag.split('}')[-1]
        self.add_breadcrumb(element_tag)
        
        current_path = self.get_breadcrumb()
        mapping_item = self.find_mapping_for_path(current_path)
        
        result = None
        
        # Check for element-specific mapping
        if mapping_item:
            object_type = mapping_item.get("objectType")
            translation_method = mapping_item.get("translationMethod")
            json_key = mapping_item.get("jsonKey")
            json_value = mapping_item.get("jsonValue")
            
            if object_type == "field":
                if element_tag == "textEdit" and json_value == "text-info":
                    result = self.create_text_info(element, mapping_item)
                elif element_tag == "textEdit" and json_value == "text-input":
                    result = self.create_text_input(element, mapping_item)
                elif element_tag == "numericEdit":
                    result = self.create_numeric_input(element, mapping_item)
                elif element_tag == "button":
                    result = self.create_button(element, mapping_item)
                elif element_tag == "dateTimeEdit":
                    result = self.create_date_input(element, mapping_item)
                elif element_tag == "checkButton" and json_value == "checkbox":
                    result = self.create_checkbox(element, mapping_item)
                elif element_tag == "checkButton" and json_value == "radio":
                    result = self.create_radio(element, mapping_item)
                elif element_tag == "choiceList":
                    result = self.create_dropdown(element, mapping_item)
                # Handle text fields, caption fields, assist fields
                elif "caption" in current_path or "assist" in current_path or "value" in current_path:
                    return self.process_field_property(element, mapping_item, parent_context)
                # Handle items (listItems)
                elif "items" in current_path:
                    return self.process_list_items(element, mapping_item, parent_context)
            elif object_type == "group":
                if element_tag == "pageSet":
                    result = self.create_master_page(mapping_item)
                elif element_tag == "exclGroup":
                    result = self.create_group(element, mapping_item)
                elif element_tag == "subform":
                    result = self.create_subform(element, mapping_item)
        
        # If we have a result, add it to items
        if result:
            self.items.append(result)
        
        # Process children recursively
        for child in element:
            child_result = self.map_element_to_json(child, result)
            # If child returns a direct property update (not a new item)
            if isinstance(child_result, dict) and parent_context:
                # Update parent with child properties
                for key, value in child_result.items():
                    parent_context[key] = value
        
        return result
    
    def create_master_page(self, mapping_item):
        """Create a master page group"""
        return {
            "type": mapping_item.get("objectType", "group"),
            "label": "Master Page",
            "id": self.fetch_id(),
            "groupId": str(self.constants.get("ministry_id", "")),
            "repeater": False,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "master_page")
            },
            "groupItems": []
        }
    
    def create_text_info(self, element, mapping_item):
        """Create a text info field"""
        return {
            "type": "text-info",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": None,
            "helperText": None
        }
    
    def create_text_input(self, element, mapping_item):
        """Create a text input field"""
        return {
            "type": "text-input",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "mask": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": None,
            "helperText": None,
            "databindings": {
                "path": None
            }
        }
    
    def create_numeric_input(self, element, mapping_item):
        """Create a numeric input field"""
        return {
            "type": "number-input",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": None,
            "databindings": {
                "path": None
            }
        }
    
    def create_button(self, element, mapping_item):
        """Create a button field"""
        return {
            "type": "button",
            "id": str(self.fetch_id()),
            "label": None,
            "styles": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            }
        }
    
    def create_date_input(self, element, mapping_item):
        """Create a date input field"""
        return {
            "type": "date",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": None,
            "databindings": {
                "path": None
            }
        }
    
    def create_checkbox(self, element, mapping_item):
        """Create a checkbox field"""
        return {
            "type": "checkbox",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": False,
            "databindings": {
                "path": None
            }
        }
    
    def create_radio(self, element, mapping_item):
        """Create a radio button field"""
        return {
            "type": "radio",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": False,
            "groupName": None,
            "databindings": {
                "path": None
            }
        }
    
    def create_dropdown(self, element, mapping_item):
        """Create a dropdown field"""
        return {
            "type": "dropdown",
            "id": str(self.fetch_id()),
            "label": None,
            "helpText": None,
            "styles": None,
            "codeContext": {
                "name": mapping_item.get("jsonKey", "")
            },
            "value": None,
            "listItems": [],
            "databindings": {
                "path": None
            }
        }
    
    def create_group(self, element, mapping_item):
        """Create a group container"""
        group_name = element.attrib.get("name", "")
        return {
            "type": "group",
            "id": str(self.fetch_id()),
            "label": None,
            "codeContext": {
                "name": group_name
            },
            "groupItems": []
        }
    
    def create_subform(self, element, mapping_item):
        """Create a subform container"""
        subform_name = element.attrib.get("name", "")
        has_occur = any(child.tag.endswith("occur") for child in element)
        
        return {
            "type": "group",
            "id": str(self.fetch_id()),
            "label": None,
            "repeater": has_occur,
            "codeContext": {
                "name": subform_name
            },
            "groupItems": []
        }
    
    def process_field_property(self, element, mapping_item, parent_context):
        """Process field properties like caption, assist, value"""
        if not parent_context:
            return None
            
        json_key = mapping_item.get("jsonKey")
        value = element.text if element.text else None
        
        if json_key == "label":
            return {"label": value}
        elif json_key == "helpText":
            return {"helpText": value}
        elif json_key == "value":
            return {"value": value}
        
        return None
    
    def process_list_items(self, element, mapping_item, parent_context):
        """Process list items for dropdowns"""
        if not parent_context or parent_context.get("type") != "dropdown":
            return None
            
        value = element.text if element.text else None
        if value and "listItems" in parent_context:
            if not isinstance(parent_context["listItems"], list):
                parent_context["listItems"] = []
                
            parent_context["listItems"].append({
                "label": value,
                "value": value
            })
            
        return None
    
    def process_bind_reference(self, element, mapping_item, parent_context):
        """Process binding references"""
        if not parent_context:
            return None
            
        ref_value = element.attrib.get("ref")
        if ref_value and "databindings" in parent_context:
            return {"databindings": {"path": ref_value}}
            
        return None