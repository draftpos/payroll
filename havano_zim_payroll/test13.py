import frappe

def run():
    slip_name = "Sal Slip/HR-EMP-00005/00012"
    
    taxable_components = [c.name.strip() for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
    if not taxable_components:
        taxable_components = ['Basic Salary']
    taxable_format = ','.join(['%s'] * len(taxable_components))
    
    t_query = frappe.db.sql(f"""
        SELECT SUM(amount) FROM `tabSalary Detail`
        WHERE parent = %s AND TRIM(salary_component) IN ({taxable_format})
    """, [slip_name] + taxable_components)
    t_amount = float(t_query[0][0] or 0)
    
    a_query = frappe.db.sql("""
        SELECT SUM(amount) FROM `tabSalary Detail`
        WHERE parent = %s AND TRIM(UPPER(salary_component)) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
    """, (slip_name,))
    a_amount = float(a_query[0][0] or 0)
    
    taxable = max(0, t_amount - a_amount)
    
    print("\n--- SCRIPT CALCULATION FOR PRINCE MAWAKA ---")
    print(f"Taxable Components configured in your system: {taxable_components}")
    print(f"Total Taxable Earnings Found by Script: {t_amount}")
    print(f"Total Allowable Deductions Found by Script: {a_amount}")
    print(f"FINAL CALCULATED TAXABLE INCOME: {taxable}")
    
    print("\nWHY IT'S DIFFERENT:")
    print("In the slip, the component is named 'Bonus Trip: 693.0'")
    print("But in your Tax Settings, the component is named 'Trip Bonus'!")
