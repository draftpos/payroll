import frappe

def execute():
    frappe.init(site="v15.local")
    frappe.connect()
    
    base_comp_name = frappe.db.get_value("havano_salary_component", {"salary_component": ["like", "CIMAS"]}, "name")
    if not base_comp_name:
        base_comp_name = frappe.db.get_value("havano_salary_component", {"salary_component": ["like", "MEDICAL AID%"]}, "name")
        
    print(f"Base comp: {base_comp_name}")
    
    if base_comp_name:
        base_doc = frappe.get_doc("havano_salary_component", base_comp_name)
        comp_doc = frappe.copy_doc(base_doc)
        comp_doc.salary_component = "First Mutual Test"
        comp_doc.code = ""
        comp_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()
        print(f"Created: {comp_doc.name}")
    else:
        print("No base comp found")
