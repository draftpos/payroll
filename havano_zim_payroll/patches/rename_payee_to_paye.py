import frappe

def execute():
    """Rename Salary Component PAYEE to PAYE if it exists."""
    if frappe.db.exists("havano_salary_component", "PAYEE"):
        try:
            frappe.rename_doc("havano_salary_component", "PAYEE", "PAYE", ignore_if_exists=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to rename PAYEE to PAYE: {e}", "Rename PAYEE Patch")

    # Also check if any existing employee deductions still use "PAYEE" and update them directly if needed
    try:
        frappe.db.sql("""
            UPDATE `tabHavano Employee Deductions`
            SET components = 'PAYE'
            WHERE components = 'PAYEE'
        """)
        frappe.db.commit()
    except Exception:
        pass
