import frappe

def after_migrate():
    create_accounts_and_components()
    populate_settings()

def create_accounts_and_components():
    components = [
        "Medical Aid", "ZIMRA", "NSSA", "ZIBAWU", "UFAWUZ", 
        "NEC", "ZESCWU", "LAPF", "Funeral Policy"
    ]

    # Create Accounts for all companies
    companies = frappe.get_all("Company", fields=["name"])
    for company in companies:
        for comp in components:
            # Check if account exists
            filters = {"account_name": comp, "company": company.name}
            existing = frappe.get_all("Account", filters=filters, limit=1)
            
            if not existing:
                # Find parent account (Current Liability)
                parent_account = frappe.db.get_value("Account", 
                    {"account_type": "Current Liability", "is_group": 1, "company": company.name}, 
                    "name")
                if not parent_account:
                    # Fallback to any Liability root/group
                    parent_account = frappe.db.get_value("Account", 
                        {"root_type": "Liability", "is_group": 1, "company": company.name}, 
                        "name")
                
                if parent_account:
                    try:
                        acc = frappe.get_doc({
                            "doctype": "Account",
                            "account_name": comp,
                            "parent_account": parent_account,
                            "company": company.name,
                            "is_group": 0,
                            "account_type": "Current Liability"
                        })
                        acc.insert(ignore_permissions=True)
                    except Exception as e:
                        frappe.log_error(f"Failed {comp} - {company.name}"[:130], str(e))

def populate_settings():
    components = [
        "Medical Aid", "ZIMRA", "NSSA", "ZIBAWU", "UFAWUZ", 
        "NEC", "ZESCWU", "LAPF", "Funeral Policy"
    ]
    
    settings = frappe.get_single("Havano Payroll Settings")
    
    existing_components = [row.component for row in settings.get("payroll_journal_accounts", [])]
    
    added = False
    for comp in components:
        if comp not in existing_components:
            # Find the account for this component
            acc_name = frappe.db.get_value("Account", {"account_name": comp}, "name")
                
            if acc_name:
                settings.append("payroll_journal_accounts", {
                    "component": comp,
                    "account": acc_name
                })
                added = True
    
    if added:
        settings.save(ignore_permissions=True)
