import frappe
from frappe import defaults

@frappe.whitelist()
def insert_payroll_accounts():
    # Get default company
    company = defaults.get_defaults().get("company")
    if not company:
        frappe.throw("Default company not set in site defaults.")

    accounts = [
        {"name": "Loan Interest", "parent_group": "Liabilities"},
        {"name": "Payee", "parent_group": "Liabilities"},
        {"name": "Aids Levy", "parent_group": "Liabilities"},
        {"name": "Salaries-Overtime-Finishing", "parent_group": "Expenses"},
        {"name": "Salaries & Wages", "parent_group": "Expenses"},
        {"name": "NSSA", "parent_group": "Liabilities"},
        {"name": "Salaries_Airtime & Data_Allowance", "parent_group": "Expenses"},
        {"name": "LAPF", "parent_group": "Liabilities"},
        {"name": "Salaries_Airtime & Data_Allowance", "parent_group": "Expenses"},
        {"name": "Salaries_Airtime & Data_Allowance", "parent_group": "Expenses"},
        {"name": "Acting Allowance", "parent_group": "Expenses"},
        {"name": "Salaries_Fuel & Mileage_Allowance", "parent_group": "Expenses"},
        {"name": "Salaries_Airtime & Data_Allowance", "parent_group": "Expenses"},
        {"name": "Housing Allowance", "parent_group": "Expenses"},
        {"name": "Cash in Lieu of Leave", "parent_group": "Expenses"},
        {"name": "Salaries_Fuel & Mileage_Allowance", "parent_group": "Expenses"},
        {"name": "UFAWUZ", "parent_group": "Liabilities"},
        {"name": "Salaries_Funeral", "parent_group": "Expenses"},
        {"name": "ZiBAWU", "parent_group": "Liabilities"},
        {"name": "Salaries_Airtime & Data_Allowance", "parent_group": "Expenses"}
    ]
    # Map expense/liability parent groups to actual parents if needed
    parent_for_group = {
        "Expenses": frappe.db.get_value("Account", {"account_name": ("like", "Indirect Expenses%"), "company": company}) or frappe.db.get_value("Account", {"account_name": ("like", "Expenses%"), "company": company}),
        "Liabilities": frappe.db.get_value("Account", {"account_name": ("like", "Indirect Expenses%"), "company": company})
    }

    for acc in accounts:
        acc_name = acc["name"].replace(" - ESH", "").strip()
        parent_group = parent_for_group.get(acc["parent_group"])
        if not parent_group:
            frappe.throw(f"No parent account found for group '{acc['parent_group']}'")

        root_type = "Expense" if acc["parent_group"] == "Expenses" else "Liability"

        if not frappe.db.exists("Account", {"account_name": acc_name, "company": company}):
            doc = frappe.get_doc({
                "doctype": "Account",
                "account_name": acc_name,
                "parent_account": parent_group,
                "company": company,
                "is_group": 0,
                "root_type": root_type
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Inserted account → {acc_name} under {parent_group}")
        else:
            print(f"Skipped (exists) → {acc_name}")

    return "All default payroll accounts inserted."
