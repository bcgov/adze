import json
import os
import datetime

class Report:
    def __init__(self, xml_filename):
        """Initialize report with a timestamped filename for every new run."""
        os.makedirs("Report", exist_ok=True)
        safe_filename = os.path.splitext(os.path.basename(xml_filename))[0]  # Remove directory path & extension
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # Get current date-time (YYYYMMDD_HHMMSS)
        self.report_file = f"{safe_filename}_report_{timestamp}.json"  # Create unique filename
        self.output_file = os.path.join("report", self.report_file)
        self.data = {"success": [], "errors": [], "manual_intervention_needed": []}

    def _write_report(self):
        """Writes the updated report data to a JSON file."""
        with open(self.report_file, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4)
        print(f"📄 New report created: {self.report_file}")

    def report_success(self, xml_field, json_field, value):
        """Log a successful conversion with file name included."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "status": "Converted successfully"
        }
        self.data["success"].append(entry)
        self._write_report()

    def report_error(self, xml_field, json_field, value, issue):
        """Log an error with file name included."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "issue": issue,
            "status": "Conversion failed"
        }
        self.data["errors"].append(entry)
        self._write_report()

    def report_manual_intervention(self, xml_field, json_field, value):
        """Log an entry that needs manual intervention."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "status": "Needs manual review"
        }
        self.data["manual_intervention_needed"].append(entry)
        self._write_report()
