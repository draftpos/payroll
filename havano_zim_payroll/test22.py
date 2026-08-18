import frappe
def run():
    print("--- PRICHARD SLIPS ---")
    slips = frappe.db.sql("""
        SELECT name, employee, employee_name, start_date 
        FROM `tabSalary Slip` 
        WHERE employee = 'HR-EMP-00060' OR employee_name LIKE '%Prichard%' OR employee_name LIKE '%Simango%'
    """, as_dict=1)
    for s in slips:
        print(s)
