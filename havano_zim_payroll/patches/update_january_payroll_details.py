import frappe
from frappe.utils import getdate

def execute():
    # Update NSSA P4 Report Store
    nssa_records = frappe.get_all("NSSA P4 Report Store", fields=["name", "employee", "payroll_period"])
    for rec in nssa_records:
        if not rec.employee: continue
        emp = frappe.get_doc("havano_employee", rec.employee)
        
        updates = {}
        if emp.national_id: updates["national_id"] = emp.national_id
        if emp.department: updates["department"] = emp.department
        
        if rec.payroll_period:
            try:
                pp = frappe.get_doc("Payroll Period", rec.payroll_period)
                updates["start_date"] = pp.start_date
                updates["end_date"] = pp.end_date
            except Exception:
                pass
                
        if updates:
            frappe.db.set_value("NSSA P4 Report Store", rec.name, updates)
            
    # Update ZIMRA P2FORM
    p2_records = frappe.get_all("ZIMRA P2FORM", fields=["name", "employee", "tax_period"])
    for rec in p2_records:
        if not rec.employee: continue
        emp = frappe.get_doc("havano_employee", rec.employee)
        updates = {}
        if emp.department: updates["department"] = emp.department
        
        if updates:
            frappe.db.set_value("ZIMRA P2FORM", rec.name, updates)

    # Update ZIMRA ITF16
    itf16_records = frappe.get_all("ZIMRA ITF16", fields=["name", "employee_id"])
    for rec in itf16_records:
        if not rec.employee_id: continue
        try:
            emp = frappe.get_doc("havano_employee", rec.employee_id)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if emp.national_id: updates["national_id"] = emp.national_id # If applicable
            if updates:
                frappe.db.set_value("ZIMRA ITF16", rec.name, updates)
        except Exception:
            pass

    # Update SDL Report
    sdl_records = frappe.get_all("SDL Report", fields=["name", "employee"])
    for rec in sdl_records:
        if not rec.employee: continue
        try:
            emp = frappe.get_doc("havano_employee", rec.employee)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if updates:
                frappe.db.set_value("SDL Report", rec.name, updates)
        except Exception:
            pass
            
    # Update NEC Report
    nec_records = frappe.get_all("NEC Report", fields=["name", "surname", "first_name"])
    for rec in nec_records:
        # NEC Report doesn't store employee ID directly by default, it uses surname/first_name
        # But maybe we can match it
        emps = frappe.get_all("havano_employee", filters={"last_name": rec.surname, "first_name": rec.first_name})
        if emps:
            emp = frappe.get_doc("havano_employee", emps[0].name)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if updates:
                frappe.db.set_value("NEC Report", rec.name, updates)

    frappe.db.commit()
