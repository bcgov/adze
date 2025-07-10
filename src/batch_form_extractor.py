#!/usr/bin/env python3
"""
Batch Form Field Extractor

This script processes multiple XDP files in a directory or a list,
extracting form fields using the advanced_form_extractor module. It also
generates a consolidated report of all forms processed.

Usage:
    python batch_form_extractor.py --input-dir <directory_with_forms> --output-dir <output_directory>
    python batch_form_extractor.py --file-list <path_to_file_with_list_of_forms> --output-dir <output_directory>

"""

import os
import sys
import argparse
import json
import logging
import csv
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Any, Set

# Ensure the advanced_form_extractor module can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from advanced_form_extractor import extract_form_fields, FormAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("batch_form_extractor")


def process_single_file(file_path: str, output_dir: str) -> Dict[str, Any]:
    """Process a single form file and return status"""
    try:
        logger.info(f"Processing {file_path}")
        success = extract_form_fields(file_path, output_dir)
        return {
            "file": file_path,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return {
            "file": file_path,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def process_directory(
    input_dir: str, output_dir: str, max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Process all XDP and PDF files in a directory"""
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        logger.error(f"Input directory not found: {input_dir}")
        return []

    # Find all XDP and PDF files
    xdp_files = list(input_path.glob("**/*.xdp"))
    pdf_files = list(input_path.glob("**/*.pdf"))
    all_files = xdp_files + pdf_files

    if not all_files:
        logger.warning(f"No XDP or PDF files found in {input_dir}")
        return []

    logger.info(
        f"Found {len(xdp_files)} XDP files and {len(pdf_files)} PDF files to process"
    )

    # Process files in parallel
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, str(file_path), output_dir): file_path
            for file_path in all_files
        }

        for future in future_to_file:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                file_path = future_to_file[future]
                logger.error(f"Error in worker processing {file_path}: {e}")
                results.append(
                    {
                        "file": str(file_path),
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    return results


def process_file_list(
    file_list_path: str, output_dir: str, max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Process files listed in a file"""
    if not os.path.exists(file_list_path):
        logger.error(f"File list not found: {file_list_path}")
        return []

    # Read file list
    with open(file_list_path, "r") as f:
        file_paths = [line.strip() for line in f if line.strip()]

    if not file_paths:
        logger.warning(f"No files listed in {file_list_path}")
        return []

    # Filter only existing files with supported extensions
    valid_files = []
    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".xdp", ".pdf"]:
            logger.warning(f"Unsupported file type: {file_path}")
            continue

        valid_files.append(file_path)

    logger.info(f"Processing {len(valid_files)} valid files from list")

    # Process files in parallel
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, file_path, output_dir): file_path
            for file_path in valid_files
        }

        for future in future_to_file:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                file_path = future_to_file[future]
                logger.error(f"Error in worker processing {file_path}: {e}")
                results.append(
                    {
                        "file": file_path,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    return results


def create_consolidated_field_report(output_dir: str) -> bool:
    """Create a consolidated CSV report of all extracted fields"""
    try:
        output_path = Path(output_dir)
        working_files_dir = output_path / "working-files"
        templates_dir = output_path / "templates"

        # Check for working-files directory
        if working_files_dir.exists():
            field_files = list(working_files_dir.glob("*_fields_*.json"))
            logger.info(
                f"Looking for field files in working-files directory: found {len(field_files)}"
            )
        else:
            # Fallback to original location for backward compatibility
            field_files = list(output_path.glob("*_fields_*.json"))
            logger.info(
                f"working-files directory not found, checking root output directory: found {len(field_files)}"
            )

        # Look for structured output files
        if templates_dir.exists():
            template_files = list(templates_dir.glob("*-form-template-*.json"))
            logger.info(
                f"Looking for template files in templates directory: found {len(template_files)}"
            )
        else:
            # Fallback to original location
            template_files = list(output_dir.glob("*-form-template-*.json"))
            logger.info(
                f"templates directory not found, checking root output directory: found {len(template_files)}"
            )

        if not field_files and not template_files:
            logger.warning(
                f"No field extraction files or template files found in {output_dir}"
            )
            return False

        logger.info(
            f"Creating consolidated report from {len(field_files)} field extraction files and {len(template_files)} template files"
        )

        # Prepare consolidated data
        all_fields = []
        form_ids = set()

        # Process traditional field files
        for field_file in field_files:
            try:
                with open(field_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    form_id = data.get("form_id", "unknown")
                    form_ids.add(form_id)

                    # Flatten field hierarchy
                    analyzer = FormAnalyzer(data)

                    for field in analyzer.fields_flat:
                        field_record = {
                            "form_id": form_id,
                            "field_name": field.get("name", ""),
                            "field_path": field.get("path", ""),
                            "field_type": field.get("type", ""),
                            "field_label": field.get("label", ""),
                            "binding_ref": field.get("binding_ref", ""),
                            "is_repeating": field.get("is_repeating", False),
                            "has_options": len(field.get("options", [])) > 0,
                            "option_count": len(field.get("options", [])),
                            "options": ", ".join(
                                str(opt) for opt in field.get("options", [])
                            ),
                            "has_javascript": bool(field.get("javascript", "")),
                            "presence": field.get("presence", "visible"),
                            "source_file": data.get("source_file", ""),
                        }
                        all_fields.append(field_record)
            except Exception as e:
                logger.error(f"Error processing field file {field_file}: {e}")

        # Process structured template files
        for template_file in template_files:
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    form_id = data.get("id", data.get("form_id", "unknown"))
                    form_ids.add(form_id)

                    # Process fields from structured format
                    fields = data.get("fields", [])
                    for field in fields:
                        field_record = {
                            "form_id": form_id,
                            "field_name": field.get("name", ""),
                            "field_path": field.get("path", field.get("name", "")),
                            "field_type": field.get("type", ""),
                            "field_label": field.get("caption", ""),
                            "binding_ref": field.get("binding", ""),
                            "is_repeating": field.get("isRepeating", False),
                            "has_options": bool(field.get("options")),
                            "option_count": len(field.get("options", [])),
                            "options": ", ".join(
                                str(opt.get("value", opt))
                                for opt in field.get("options", [])
                            ),
                            "has_javascript": bool(field.get("script", "")),
                            "presence": field.get("visibility", "visible"),
                            "source_file": template_file.name,
                        }
                        all_fields.append(field_record)
            except Exception as e:
                logger.error(f"Error processing template file {template_file}: {e}")

        if not all_fields:
            logger.warning("No fields found in extraction files or template files")
            return False

        # Create DataFrame
        df = pd.DataFrame(all_fields)

        # Save consolidated CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = output_path / f"consolidated_fields_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Consolidated field report saved to {csv_path}")

        # Create Excel report with multiple sheets
        try:
            excel_path = output_path / f"consolidated_fields_{timestamp}.xlsx"
            with pd.ExcelWriter(excel_path) as writer:
                # Main sheet with all fields
                df.to_excel(writer, sheet_name="All Fields", index=False)

                # Summary sheet
                summary_data = {
                    "Form ID": list(form_ids),
                    "Field Count": [
                        len(df[df["form_id"] == form_id]) for form_id in form_ids
                    ],
                    "Unique Field Types": [
                        len(df[df["form_id"] == form_id]["field_type"].unique())
                        for form_id in form_ids
                    ],
                    "Fields with Data Binding": [
                        len(df[(df["form_id"] == form_id) & (df["binding_ref"] != "")])
                        for form_id in form_ids
                    ],
                    "Repeating Sections": [
                        len(df[(df["form_id"] == form_id) & df["is_repeating"]])
                        for form_id in form_ids
                    ],
                }
                pd.DataFrame(summary_data).to_excel(
                    writer, sheet_name="Summary", index=False
                )

                # Sheet per form
                for form_id in form_ids:
                    form_df = df[df["form_id"] == form_id]
                    if len(form_df) > 0:
                        sheet_name = form_id[
                            :31
                        ]  # Excel limits sheet names to 31 chars
                        form_df.to_excel(writer, sheet_name=sheet_name, index=False)

            logger.info(f"Consolidated Excel report saved to {excel_path}")
        except Exception as e:
            logger.error(f"Error creating Excel report: {e}")

        return True

    except Exception as e:
        logger.error(f"Error creating consolidated report: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Batch process XDP and PDF files to extract form fields"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-dir", help="Directory containing XDP and PDF files")
    group.add_argument(
        "--file-list", help="File containing list of XDP and PDF files to process"
    )
    parser.add_argument(
        "--output-dir", default="./output", help="Directory for output files"
    )
    parser.add_argument(
        "--max-workers", type=int, default=4, help="Maximum number of parallel workers"
    )

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process files
    start_time = time.time()
    if args.input_dir:
        results = process_directory(args.input_dir, args.output_dir, args.max_workers)
    else:
        results = process_file_list(args.file_list, args.output_dir, args.max_workers)

    # Write processing summary
    summary = {
        "total_files": len(results),
        "successful": sum(1 for r in results if r.get("success", False)),
        "failed": sum(1 for r in results if not r.get("success", False)),
        "processing_time": time.time() - start_time,
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }

    summary_file = (
        output_dir
        / f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(
        f"Processing complete. Processed {len(results)} files "
        f"({summary['successful']} successful, {summary['failed']} failed)."
    )
    logger.info(f"Summary saved to {summary_file}")

    # Create consolidated report
    if create_consolidated_field_report(args.output_dir):
        logger.info("Consolidated field report created successfully")

    return 0


if __name__ == "__main__":
    sys.exit(main())
