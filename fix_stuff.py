import frappe
import os

def execute():
    # 1. Fix the fds_tax.py code NameError
    app_path = frappe.get_app_path('havano_zim_payroll')
    file_path = os.path.join(app_path, 'havano_zim_payroll', 'doctype', 'havano_employee', 'fds_tax.py')
    
    with open(file_path, 'r') as f:
        code = f.read()
        
    if 'frappe.get_doc("havano_employee", employee)' in code:
        code = code.replace('frappe.get_doc("havano_employee", employee)', 'frappe.get_doc("havano_employee", employee_id)')
        with open(file_path, 'w') as f:
            f.write(code)
        print("✅ Fixed NameError in fds_tax.py")
    else:
        print("✅ NameError already fixed in fds_tax.py")

    # 2. Unlock the Payroll Period
    try:
        # Usually it's either 'Payroll Period' or 'Havano Payroll Period'
        periods = frappe.get_all("Payroll Period", filters={"name": ["like", "%July%2026%"]})
        for p in periods:
            doc = frappe.get_doc("Payroll Period", p.name)
            if hasattr(doc, "status"):
                doc.status = "Draft"
            if hasattr(doc, "completed"):
                doc.completed = 0
            doc.flags.ignore_validate = True
            doc.save(ignore_permissions=True)
            print(f"✅ Unlocked Payroll Period: {p.name}")
    except Exception as e:
        print(f"Skipped standard Payroll Period unlock: {e}")

    try:
        periods = frappe.get_all("Havano Payroll Period", filters={"name": ["like", "%July%2026%"]})
        for p in periods:
            doc = frappe.get_doc("Havano Payroll Period", p.name)
            if hasattr(doc, "status"):
                doc.status = "Draft"
            if hasattr(doc, "completed"):
                doc.completed = 0
            if hasattr(doc, "is_completed"):
                doc.is_completed = 0
            if hasattr(doc, "is_closed"):
                doc.is_closed = 0
            doc.flags.ignore_validate = True
            doc.save(ignore_permissions=True)
            print(f"✅ Unlocked Havano Payroll Period: {p.name}")
    except Exception as e:
        pass
        
    frappe.db.commit()
