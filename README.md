## 🚀 Running the XML Converter

To run the converter script, follow these steps:

1. **Run the converter script**:
    ```sh
    python xml_converter.py -f=<path to input xml> -m=<path to mapping file>
    ```

2. **Check the generated json**:
    - The generated JSON will be saved in the same directory with the name `mapping_output.json`.

3. **Check the generated report**:
    - The report will be saved in the same directory with the name `conversion_report.json`.

---

# XML to JSON Converter - Reports & Error Handling

## 📖 Overview
This document explains the reporting and error-handling mechanisms in the **XML to JSON conversion tool**. It covers how errors are logged, how reports are generated, and the structure of reporting for both **single and batch processing**.

---

## 📂 Report Generation

### 📌 Purpose
The reporting system logs:
- ✅ **Successful conversions**
- ❌ **Errors encountered**
- ⚠️ **Cases requiring manual intervention**  

This helps in **debugging, tracking conversion accuracy, and identifying patterns** in failures.

---

### 📑 **Report Structure**
Each conversion generates a **JSON report** with the following format:
```json
{
    "success": [],
    "errors": [],
    "manual_intervention_needed": []
}

## 📄 Additional Documentation
For a detailed explanation of reports and error handling, refer to the full documentation.
