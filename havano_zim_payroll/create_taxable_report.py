import frappe

def execute():
    report_name = "FDS Taxable Income Report"
    if not frappe.db.exists("Report", report_name):
        doc = frappe.get_doc({
            "doctype": "Report",
            "name": report_name,
            "report_name": report_name,
            "ref_doctype": "havano_employee",
            "report_type": "Script Report",
            "is_standard": "Yes",
            "module": "Havano Zim Payroll"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created Report {report_name}")
    else:
        print(f"Report {report_name} already exists")
