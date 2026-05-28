import frappe

def execute():
    frappe.init(site="v15.local")
    frappe.connect()
    
    medical_aid_label = "Pismas Test"
    
    try:
        if not frappe.db.exists("havano_salary_component", medical_aid_label):
            comp_doc = frappe.new_doc("havano_salary_component")
            comp_doc.salary_component = medical_aid_label
            comp_doc.type = "Deduction"
            comp_doc.always_calculate = 1
            comp_doc.code = "" 
            comp_doc.insert(ignore_permissions=True, ignore_mandatory=True)
            frappe.db.commit()
            print(f"SUCCESS! Created: {comp_doc.name}")
        else:
            print("Already exists")
    except Exception as e:
        import traceback
        print(f"FAILED TO INSERT: {e}")
        traceback.print_exc()

execute()
