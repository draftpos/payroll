import frappe

def run():
    print("\n--- CHECKING FOR MISSING EMPLOYEES IN HISTORICAL TABLE ---")
    missing_names = ["Nyasha", "Tendai", "Tafadzwa", "Lambert", "Rumbidzai", "Duncan", "Jabulani", "Maxwell", "Tanaka", "Tinotenda"]
    
    for name in missing_names:
        res = frappe.db.sql("""
            SELECT name, first_name, last_name FROM `tabHavano Historical PAYE` 
            WHERE first_name LIKE %s OR last_name LIKE %s
        """, (f"%{name}%", f"%{name}%"), as_dict=True)
        
        if not res:
            print(f"{name}: NOT FOUND in Historical PAYE table!")
        else:
            print(f"{name}: Found - {res[0].first_name} {res[0].last_name}")
            
    print("\n--- CHECKING IF THEY HAVE SLIPS ---")
    res = frappe.db.sql("""
        SELECT COUNT(name) as cnt FROM `tabSalary Slip`
        WHERE employee_name LIKE '%Nyasha%'
    """, as_dict=True)
    print(f"Nyasha has {res[0].cnt} Salary Slips.")
