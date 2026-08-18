import frappe

def run():
    print("\n--- CHECKING WENGAI MAKAZA IN HISTORICAL TABLE ---")
    res = frappe.db.sql("""
        SELECT name, employee, first_name, last_name, month_1_income_usd, month_2_income_usd, month_3_income_usd
        FROM `tabHavano Historical PAYE`
        WHERE first_name LIKE '%Wengai%' OR last_name LIKE '%Makaza%'
    """, as_dict=True)
    
    for r in res:
        print(f"Row: {r.name} | EmpID: {r.employee} | Name: {r.first_name} {r.last_name} | Jan: {r.month_1_income_usd} | Feb: {r.month_2_income_usd} | Mar: {r.month_3_income_usd}")
        
    print("\n--- CHECKING WENGAI MAKAZA IN SALARY SLIPS ---")
    res = frappe.db.sql("""
        SELECT name, employee, employee_name, start_date, docstatus
        FROM `tabSalary Slip`
        WHERE employee_name LIKE '%Wengai%' OR employee_name LIKE '%Makaza%'
    """, as_dict=True)
    for r in res:
        print(f"Slip: {r.name} | EmpID: {r.employee} | Name: {r.employee_name} | Date: {r.start_date} | Status: {r.docstatus}")
