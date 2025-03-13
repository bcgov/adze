from xml_converter_class import XDPParser
import argparse

def parse_xdp_to_json(file_path, mapping_file='xml_mapping.json'):
    """Main function to convert XDP to JSON"""
    try:
        parser = XDPParser(file_path, mapping_file)
        return parser.parse()
    except Exception as e:
        print(f"Error processing XDP: {e}")


if __name__ == "__main__":
    # file_path = './sample_pdfs/eg medium-complexity-A HR0077.xdp'
    parser = argparse.ArgumentParser(description='Convert XDP to JSON.')
    parser.add_argument('-f', type=str, help='Path to the XDP file')
    parser.add_argument('-m', type=str, default='xml_mapping.json', help='Path to the XML mapping file')
    args = parser.parse_args()

    file_path = args.f
    mapping_file = args.m
    # file_path = './sample_pdfs/eg medium-complexity-B HR0095.xdp'
    result = parse_xdp_to_json(file_path, mapping_file)
    print("XML conversion", "successful" if result else "failed")