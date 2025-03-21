import datetime
import os
from pathlib import PurePosixPath
# from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv()

# Resolve paths based on the script's actual location
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # Get project root

# Get directories from environment variables (fallback to absolute paths)
INPUT_DIR = os.getenv("INPUT_DIR", os.path.join(BASE_DIR, "data", "input"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "data", "output"))
REPORT_DIR = os.getenv("REPORT_DIR", os.path.join(BASE_DIR, "data", "report"))

def generate_filename(xml_filename, file_type):
    """
    Generate a unique filename with a timestamp and return the full file path.

    Args:
        xml_filename (str): The original XDP filename.
        file_type (str): Type of file ('report' or 'output').

    Returns:
        str: Full path to the generated file.
    """
    safe_filename = os.path.splitext(os.path.basename(xml_filename))[0]  # Remove extension
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # YYYYMMDD_HHMMSS

    if file_type == "report":
        directory = REPORT_DIR
    elif file_type == "output":
        directory = OUTPUT_DIR
    else:
        raise ValueError("Invalid file type. Must be 'report' or 'output'.")

    os.makedirs(directory, exist_ok=True)  # Ensure directory exists
    return str(PurePosixPath(directory, f"{safe_filename}_{file_type}_{timestamp}.json"))
