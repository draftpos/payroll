import frappe
def install_defaults():
    from .create_default_components import create_salary_components
    from .create_default_accounts import insert_payroll_accounts 
    from .create_default_items import insert_items
    from .create_default_supplier import insert_suppliers
    from .create_default_components_mode import create_salary_component_types
    from .create_default_leave_types import create_leave_types
    from .create_default_slabs import set_default_tax_slabs
    from .install_purchase_invoice_fields import add_payroll_fields_to_purchase_invoice
    from .create_default_settings import set_havano_payroll_defaults
    insert_items()
    insert_suppliers()
    create_salary_component_types()
    insert_payroll_accounts()
    create_salary_components()
    create_leave_types()
    set_default_tax_slabs()
    add_payroll_fields_to_purchase_invoice()
    set_havano_payroll_defaults()
    fix_leave_application_naming()

    frappe.msgprint("Default payroll items, suppliers, accounts, and salary components have been installed.")

def fix_leave_application_naming():
    """Ensure Leave Application doesn't overwrite records by fixing its naming rule."""
    try:
        if frappe.db.exists("DocType", "Leave Application"):
            doc = frappe.get_doc("DocType", "Leave Application")
            # If it's set to employee, it will overwrite. Change to hash for uniqueness.
            if doc.autoname == "field:employee" or not doc.autoname or doc.autoname == "Prompt":
                doc.autoname = "hash"
                doc.save(ignore_permissions=True)
                frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Fix Leave Application Naming Error")