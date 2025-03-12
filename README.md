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
For a detailed explanation of reports and error handling, refer to the full documentation:  
[Reports and Error Handling Guide](https://drive.google.com/file/d/1sItOoXIiZpSOP4BZ4r5TiWC4zw9KYviW/view?usp=drive_link)
