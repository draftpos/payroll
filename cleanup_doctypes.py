import frappe

def cleanup():
    # Delete the DocTypes from the database to avoid conflict with the Report
    for doctype in ["Payroll Summary", "Payroll Summary Item"]:
        if frappe.db.exists("DocType", doctype):
            print(f"Deleting DocType: {doctype}")
            frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
            frappe.db.commit()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
