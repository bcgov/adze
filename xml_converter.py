from xml_converter_class import XDPParser

def parse_xdp_to_json(file_path, mapping_file='xml_mapping.json'):
    """Main function to convert XDP to JSON"""
    try:
        parser = XDPParser(file_path, mapping_file)
        return parser.parse()
    except Exception as e:
        print(f"Error processing XDP: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # file_path = './sample_pdfs/eg medium-complexity-A HR0077.xdp'
    file_path = './sample_pdfs/eg medium-complexity-B HR0095.xdp'
    result = parse_xdp_to_json(file_path, 'xml_mapping.json')
    print("XML conversion", "successful" if result else "failed")