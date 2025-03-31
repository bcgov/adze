import json
import logging
import os
from .filename_generator import generate_filename

# ✅ Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Report:
    def __init__(self, xml_filename):
        """Initialize report with a unique filename and correct path."""
        self.report_file = generate_filename(xml_filename, "report")  # ✅ Matches `xml_filename`
        self.data = {"success": [], "errors": [], "manual_intervention_needed": []}
        self.total_success = 0
        self.total_errors = 0
        self.total_manual_intervention = 0

        logger.info(f"📝 Report will be saved to: {self.report_file}")

    def report_success(self, xml_field, json_field, value):
        """Log a successful conversion without writing immediately."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "status": "Converted successfully"
        }
        self.data["success"].append(entry)
        self.total_success += 1

    def report_error(self, xml_field, json_field, value, issue):
        """Log an error without writing immediately."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "issue": issue,
            "status": "Conversion failed"
        }
        self.data["errors"].append(entry)
        self.total_errors += 1

    def report_manual_intervention(self, xml_field, json_field, value):
        """Log an entry that needs manual intervention without writing immediately."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "status": "Needs manual review"
        }
        self.data["manual_intervention_needed"].append(entry)
        self.total_manual_intervention += 1

    def save_report(self):
        """Writes the final report to a JSON file (only once)."""
        total_fields = self.total_success + self.total_errors + self.total_manual_intervention
        success_rate = (self.total_success / total_fields * 100) if total_fields > 0 else 0
        summary = {
            "total_fields": total_fields,
            "total_success": self.total_success,
            "total_errors": self.total_errors,
            "total_manual_intervention": self.total_manual_intervention,
            "success_rate": f"{success_rate:.2f}%"
        }

        # Create a ordered dictionary
        final_report = {
            "summary": summary,
            "success": self.data["success"],
            "errors": self.data["errors"],
            "manual_intervention_needed": self.data["manual_intervention_needed"]
        }

        with open(self.report_file, "w", encoding="utf-8") as file:
            json.dump(final_report, file, indent=4)

        logger.info(f"✅ Report successfully saved: {self.report_file}")

