import frappe

@frappe.whitelist()
def create_salary_component_types():
    """
    Inserts default salary component types into 'havano_salary_component_type' DocType
    if they do not already exist.
    """
    types = [
        "daily rate",
        "NSSA",
        "allowable_deduction"
    ]

    for t in types:
        if not frappe.db.exists("havano_salary_component_type", t):
            doc = frappe.get_doc({
                "doctype": "havano_salary_component_type",
                "type": t
            })
            doc.insert()
            frappe.db.commit()
            print(f"Created Salary Component Type: {t}")
        else:
            print(f"Salary Component Type already exists: {t}")
