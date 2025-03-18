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
        #counters for summary
        self.total_success=0
        self.total_errors=0
        self.total_manual_intervention=0

    def _write_report(self):
        """Writes report data and summary statistics to a JSON file."""
        total_fields = self.total_success + self.total_errors + self.total_manual_intervention
        success_rate = (self.total_success / total_fields * 100) if total_fields > 0 else 0
        summary={
            "total_fields":total_fields,
            "total_success":self.total_success,
            "total_errors":self.total_errors,
            "total_manual_intervention": self.total_manual_intervention,
            "success_rate": f"{success_rate:.2f}%"

        }
        self.data["summary"] = summary
        with open(self.output_file, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4)
       # print(f"📄 New report created: {self.output_file}")

    def report_success(self, xml_field, json_field, value):
        """Log a successful conversion with file name included."""
        entry = {
            "field_in_original_form": xml_field,
            "converted_field": json_field,
            "value": value,
            "status": "Converted successfully"
        }
        self.data["success"].append(entry)
        self.total_success+=1
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
        self.total_errors+=1
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
        self.total_manual_intervention+=1
        self._write_report()