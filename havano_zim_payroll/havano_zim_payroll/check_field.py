import frappe
def execute():
    try:
        has_col = frappe.db.has_column("havano_employee", "cimas_amount")
        print(f"Database Column cimas_amount exists: {has_col}")
        
        meta = frappe.get_meta("havano_employee")
        field = meta.get_field("cimas_amount")
        if field:
            print(f"Meta Field exists! fieldtype={field.fieldtype}, hidden={field.hidden}")
        else:
            print("Meta Field DOES NOT EXIST!")
    except Exception as e:
        print(f"Error: {e}")
