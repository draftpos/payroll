import frappe

def run():
    print("\n--- DUMPING HAVANO HISTORICAL PAYE FOR MISSING EMPLOYEES ---")
    names = ["Nyasha", "Tendai", "Tafadzwa", "Lambert", "Rumbidzai"]
    
    for name in names:
        res = frappe.db.sql("""
            SELECT name, employee, first_name, last_name, month_1_income_usd, month_2_income_usd 
            FROM `tabHavano Historical PAYE` 
            WHERE first_name LIKE %s OR last_name LIKE %s
        """, (f"%{name}%", f"%{name}%"), as_dict=True)
        print(f"\nSearching for {name}:")
        if not res:
            print("  NO RECORDS FOUND")
        for r in res:
            print(f"  Row Name: {r.name} | Employee: {r.employee} | First: '{r.first_name}' | Last: '{r.last_name}' | Jan: {r.month_1_income_usd} | Feb: {r.month_2_income_usd}")
            
    print("\n--- REPORT DUPLICATE CHECK ---")
    res = frappe.db.sql("""
        SELECT first_name, last_name, COUNT(*) as cnt
        FROM `tabHavano Historical PAYE`
        WHERE tax_year = 2026
        GROUP BY first_name, last_name
        HAVING cnt > 1
    """, as_dict=True)
    if not res:
        print("  NO DUPLICATES FOUND BY EXACT NAME!")
    for r in res:
        print(f"  Duplicate: '{r.first_name}' '{r.last_name}' - {r.cnt} times")
