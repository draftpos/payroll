import frappe

def get_emp_by_name(surname, first_name):
    if not surname and not first_name: return None
    emps = frappe.get_all("havano_employee", filters={"last_name": surname, "first_name": first_name}, limit=1)
    if emps:
        return frappe.get_doc("havano_employee", emps[0].name)
    return None

def execute():
    # Update NSSA P4 Report Store
    nssa_records = frappe.get_all("NSSA P4 Report Store", fields=["name", "surname", "first_name", "payroll_period"])
    for rec in nssa_records:
        emp = get_emp_by_name(rec.surname, rec.first_name)
        if not emp: continue
        
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
    # Cannot be updated retroactively via employee because it lacks employee identifiers
    pass

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
        emp = get_emp_by_name(rec.surname, rec.first_name)
        if not emp: continue
        updates = {}
        if emp.department: updates["department"] = emp.department
        if updates:
            frappe.db.set_value("NEC Report", rec.name, updates)

    frappe.db.commit()
