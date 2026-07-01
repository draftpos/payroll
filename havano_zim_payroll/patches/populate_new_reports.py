import frappe
from frappe.utils import flt
import re

def execute():
    entries = frappe.get_all("Havano Payroll Entry", fields=["name", "employee", "payroll_period"])
    count = 0
    
    for entry in entries:
        doc = frappe.get_doc("Havano Payroll Entry", entry.name)
        emp = frappe.db.get_value("havano_employee", doc.employee, ["department", "national_id", "first_name", "last_name"], as_dict=True)
            
        if not emp:
            continue
            
        items = []
        if hasattr(doc, "employee_earnings"):
            items.extend(doc.employee_earnings)
        if hasattr(doc, "employee_deductions"):
            items.extend(doc.employee_deductions)
            
        for item in items:
            if not item.components:
                continue
                
            amount = flt(item.amount_usd) + flt(item.amount_zwg)
            
            clean_comp = re.sub(r'[^a-zA-Z0-9 \-_]', '', item.components)
            dt_name = f"{clean_comp} Report Store"
            
            if frappe.db.exists("DocType", dt_name):
                # Avoid inserting duplicates if run multiple times
                if not frappe.db.exists(dt_name, {"employee": doc.employee, "payroll_period": doc.payroll_period}):
                    frappe.get_doc({
                        "doctype": dt_name,
                        "employee": doc.employee,
                        "first_name": emp.first_name,
                        "surname": emp.last_name,
                        "national_id": emp.national_id,
                        "department": emp.department,
                        "payroll_period": doc.payroll_period,
                        "amount": amount
                    }).insert(ignore_permissions=True)
                    count += 1

    frappe.db.commit()
    print(f"Successfully populated {count} records into the new Report Stores!")
