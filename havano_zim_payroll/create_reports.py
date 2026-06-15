import frappe

def execute():
    reports = ["Salary Register", "NSSA Report", "SDL Report", "NEC Report"]
    for rep in reports:
        if not frappe.db.exists("Report", rep):
            doc = frappe.get_doc({
                "doctype": "Report",
                "report_name": rep,
                "ref_doctype": "havano_employee",
                "report_type": "Script Report",
                "is_standard": "Yes",
                "module": "Havano Zim Payroll"
            })
            doc.insert(ignore_permissions=True)
            print(f"Created {rep}")
        else:
            print(f"Report {rep} already exists")
