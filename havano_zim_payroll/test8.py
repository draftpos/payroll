import frappe

def run():
    print("\n--- DB CHECK ---")
    res = frappe.db.sql("SELECT first_name, last_name, month_1_income_usd, month_2_income_usd, month_3_income_usd, month_4_income_usd, month_5_income_usd, month_6_income_usd FROM `tabHavano Historical PAYE` WHERE first_name = 'JUSA' AND last_name = 'NYAHODA'", as_dict=True)
    print("JUSA NYAHODA IN DB:", res)

    print("\n--- AGGREGATION CHECK FOR JUSA (MAY) ---")
    h_entries = frappe.db.sql("""
        SELECT name, first_name, last_name, date
        FROM `tabHavano Payroll Entry`
        WHERE docstatus < 2 AND first_name = 'JUSA' AND last_name = 'NYAHODA' AND YEAR(date) = 2026 AND MONTH(date) = 5
    """, as_dict=True)
    
    print("Havano Payroll Entries for Jusa in May:", h_entries)

    for h in h_entries:
        taxable_components = [c.name.strip() for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
        if not taxable_components:
            taxable_components = ['Basic Salary']
        taxable_format = ','.join(['%s'] * len(taxable_components))
        
        t_usd_query = frappe.db.sql(f"""
            SELECT SUM(amount_usd) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_earnings' AND TRIM(components) IN ({taxable_format})
        """, [h.name] + taxable_components)
        print("T_USD_QUERY:", t_usd_query)

        a_usd_query = frappe.db.sql("""
            SELECT SUM(amount_usd) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_deductions' 
              AND TRIM(UPPER(components)) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (h.name,))
        print("A_USD_QUERY:", a_usd_query)

    print("\n--- DONE ---")
