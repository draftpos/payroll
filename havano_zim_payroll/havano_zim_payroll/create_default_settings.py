import frappe

def set_havano_payroll_defaults():
    # get default company
    default_company = frappe.defaults.get_defaults().get("company")
    
    # find a cost center starting with "Main -" and is not a group
    cost_center = frappe.get_all(
        "Cost Center",
        filters={
            "company": default_company,
            "is_group": 0,
            "name": ["like", "Main -%"]
        },
        limit_page_length=1
    )
    
    if not cost_center:
        frappe.throw("No valid Cost Center found starting with 'Main -'")
    
    # get the single doc
    payroll_settings = frappe.get_single("Havano Payroll Settings")
    
    # set main fields
    payroll_settings.supplier = "SDL"
    payroll_settings.cost_center = cost_center[0].name
    
    # clear existing child table rows
    payroll_settings.components_for_reporting = []
    
    # define components
    components = [
        {"component": "CIMAS"},
        {"component": "NSSA"},
        {"component": "Aids Levy"},
        {"component": "Funeral Policy"},
        {"component": "PAYEE"},
        {"component": "UFAWUZ"},
        {"component": "ZIBAWU"},
        {"component": "LAPF"},
    ]
    
    # add them to child table
    for comp in components:
        payroll_settings.append("components_for_reporting", comp)
    
    # save
    payroll_settings.save()
    frappe.db.commit()
    frappe.msgprint("Havano Payroll Settings default values set successfully.")
