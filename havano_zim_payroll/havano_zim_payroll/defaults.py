import frappe
def install_defaults():
    from .create_default_components import create_salary_components
    from .create_default_accounts import insert_payroll_accounts 
    from .create_default_items import insert_items
    from .create_default_supplier import insert_suppliers
    from .create_default_components_mode import create_salary_component_types

    insert_items()
    insert_suppliers()
    create_salary_component_types()
    insert_payroll_accounts()
    create_salary_components()


    frappe.msgprint("Default payroll items, suppliers, accounts, and salary components have been installed.")