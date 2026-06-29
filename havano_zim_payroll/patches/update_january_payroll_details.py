import frappe

def extract_emp_id(name, prefix):
    # e.g. name: "NSSA-P4-EMP-001-January-2025", prefix: "NSSA-P4-"
    # Remove prefix
    if name.startswith(prefix):
        rest = name[len(prefix):]
        # rest: "EMP-001-January-2025"
        parts = rest.split("-")
        if len(parts) >= 3:
            # month is parts[-2], year is parts[-1]
            return "-".join(parts[:-2])
    return None

def execute():
    # Update NSSA P4 Report Store
    nssa_records = frappe.get_all("NSSA P4 Report Store", fields=["name", "payroll_period"])
    for rec in nssa_records:
        emp_id = extract_emp_id(rec.name, "NSSA-P4-")
        if not emp_id: continue
        
        try:
            emp = frappe.get_doc("havano_employee", emp_id)
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
        except Exception:
            pass
            
    # Update ZIMRA P2FORM
    p2_records = frappe.get_all("ZIMRA P2FORM", fields=["name", "tax_period"])
    for rec in p2_records:
        emp_id = extract_emp_id(rec.name, "ZIMRA-P2-")
        if not emp_id: continue
        try:
            emp = frappe.get_doc("havano_employee", emp_id)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if updates:
                frappe.db.set_value("ZIMRA P2FORM", rec.name, updates)
        except Exception:
            pass

    # Update ZIMRA ITF16
    itf16_records = frappe.get_all("ZIMRA ITF16", fields=["name"])
    for rec in itf16_records:
        emp_id = extract_emp_id(rec.name, "ZIMRA-ITF16-")
        if not emp_id: continue
        try:
            emp = frappe.get_doc("havano_employee", emp_id)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if emp.national_id: updates["national_id"] = emp.national_id # If applicable
            if updates:
                frappe.db.set_value("ZIMRA ITF16", rec.name, updates)
        except Exception:
            pass

    # Update SDL Report
    sdl_records = frappe.get_all("SDL Report", fields=["name"])
    for rec in sdl_records:
        emp_id = extract_emp_id(rec.name, "SDL-")
        if not emp_id: continue
        try:
            emp = frappe.get_doc("havano_employee", emp_id)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if updates:
                frappe.db.set_value("SDL Report", rec.name, updates)
        except Exception:
            pass
            
    # Update NEC Report
    nec_records = frappe.get_all("NEC Report", fields=["name"])
    for rec in nec_records:
        emp_id = extract_emp_id(rec.name, "NEC-")
        if not emp_id: continue
        try:
            emp = frappe.get_doc("havano_employee", emp_id)
            updates = {}
            if emp.department: updates["department"] = emp.department
            if updates:
                frappe.db.set_value("NEC Report", rec.name, updates)
        except Exception:
            pass

    frappe.db.commit()
