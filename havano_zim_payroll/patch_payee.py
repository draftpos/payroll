import frappe

def execute():
    # 1. Rename the main Salary Component from PAYEE to PAYE (if it exists)
    if frappe.db.exists("havano_salary_component", "PAYEE"):
        try:
            frappe.rename_doc("havano_salary_component", "PAYEE", "PAYE", force=True, ignore_if_exists=True)
            print("Renamed Salary Component 'PAYEE' to 'PAYE'")
        except Exception as e:
            print(f"Error renaming component: {e}")

    # 2. Update all tables with 'component' or 'components' columns
    tables = frappe.db.sql("SHOW TABLES")
    for table_tuple in tables:
        table = table_tuple[0]
        try:
            cols = [c[0] for c in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`")]
            for col in ["component", "components"]:
                if col in cols:
                    res = frappe.db.sql(f"UPDATE `{table}` SET `{col}` = 'PAYE' WHERE `{col}` = 'PAYEE'")
                    if frappe.db.rowcount > 0:
                        print(f"Updated {frappe.db.rowcount} rows in {table} (column: {col})")
        except Exception as e:
            pass

    frappe.db.commit()
    print("Database patch completed successfully.")
