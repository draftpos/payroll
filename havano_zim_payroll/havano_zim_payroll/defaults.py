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


    frappe.msgprint("Default payroll items, suppliers, accounts, and salary components have been installed.")