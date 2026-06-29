import frappe

def execute():
    # 1. Rename the main Salary Component from PAYEE to PAYE (if it exists)
    if frappe.db.exists("havano_salary_component", "PAYEE"):
        try:
            frappe.rename_doc("havano_salary_component", "PAYEE", "PAYE", force=True, ignore_if_exists=True)
            print("Renamed Salary Component 'PAYEE' to 'PAYE'")
        except Exception as e:
            print(f"Error renaming component: {e}")

    # 2. Update all child tables (Earnings & Deductions) across the system
    # This covers Havano Employee and Havano Payroll Entry child tables
    tables = [
        "tabHavano Payroll Earnings",
        "tabHavano Payroll Deduction",
        "tabHavano Payroll Journal Detail"
    ]
    
    for table in tables:
        try:
            # Check if table exists first
            if frappe.db.sql(f"SHOW TABLES LIKE '{table}'"):
                # Check if it has a components column
                cols = [c[0] for c in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`")]
                if "components" in cols:
                    res = frappe.db.sql(f"UPDATE `{table}` SET components = 'PAYE' WHERE components = 'PAYEE'")
                    print(f"Updated {frappe.db.rowcount} rows in {table}")
        except Exception as e:
            print(f"Skipping {table}: {e}")

    frappe.db.commit()
    print("Database patch completed successfully.")
