import frappe

def run():
    slip_name = "Sal Slip/HR-EMP-00005/00012"
    
    print(f"\n--- DIAGNOSTICS FOR SLIP {slip_name} ---")
    slip = frappe.get_all("Salary Slip", filters={"name": slip_name}, fields=["name", "employee", "employee_name", "start_date", "docstatus"])
    if not slip:
        print("SLIP NOT FOUND!")
        return
        
    s = slip[0]
    print(f"Employee: {s.employee} - {s.employee_name}")
    print(f"Month: {s.start_date.month}")
    print(f"DocStatus: {s.docstatus}")
    
    print("\nEARNINGS:")
    earnings = frappe.db.sql("SELECT salary_component, amount FROM `tabSalary Detail` WHERE parent = %s AND parentfield = 'earnings'", (slip_name,), as_dict=True)
    for e in earnings:
        print(f"  {e.salary_component}: {e.amount}")
        
    print("\nDEDUCTIONS:")
    deductions = frappe.db.sql("SELECT salary_component, amount FROM `tabSalary Detail` WHERE parent = %s AND parentfield = 'deductions'", (slip_name,), as_dict=True)
    for d in deductions:
        print(f"  {d.salary_component}: {d.amount}")
        
    taxable_components = [c.name.strip() for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
    if not taxable_components:
        taxable_components = ['Basic Salary']
    taxable_format = ','.join(['%s'] * len(taxable_components))
    
    t_query = frappe.db.sql(f"""
        SELECT SUM(amount) FROM `tabSalary Detail`
        WHERE parent = %s AND TRIM(salary_component) IN ({taxable_format})
    """, [s.name] + taxable_components)
    t_amount = float(t_query[0][0] or 0)
    
    a_query = frappe.db.sql("""
        SELECT SUM(amount) FROM `tabSalary Detail`
        WHERE parent = %s AND TRIM(UPPER(salary_component)) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
    """, (s.name,))
    a_amount = float(a_query[0][0] or 0)
    
    taxable = max(0, t_amount - a_amount)
    
    print("\n--- SCRIPT CALCULATION ---")
    print(f"Taxable Components Considered: {taxable_components}")
    print(f"Total Taxable Earnings Found: {t_amount}")
    print(f"Total Allowable Deductions Found (NSSA, CIMAS, etc): {a_amount}")
    print(f"FINAL CALCULATED TAXABLE INCOME: {taxable}")
    
    print("\n--- CURRENT REPORT DB ---")
    emp_name_query = " ".join(s.employee_name.split())
    # Try to find them in the DB
    db_res = frappe.db.sql(f"""
        SELECT first_name, last_name, month_{s.start_date.month}_income_usd as db_balance
        FROM `tabHavano Historical PAYE`
        WHERE CONCAT(first_name, ' ', last_name) LIKE %s
    """, (f"%{emp_name_query}%",), as_dict=True)
    
    if db_res:
        print(f"Database currently holds: {db_res[0].db_balance}")
    else:
        print("Employee not found in Historical table.")
