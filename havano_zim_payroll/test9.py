import frappe
from havano_zim_payroll.havano_zim_payroll.report.fds_taxable_income_report.fds_taxable_income_report import get_data

def run():
    print("\n--- RUNNING REPORT GET_DATA ---")
    filters = {"year": "2026"}
    data = get_data(filters)
    
    found = False
    for d in data:
        if d.get("first_name", "").upper() == "JUSA":
            print("JUSA IN REPORT DATA:", d)
            found = True
            
    if not found:
        print("JUSA NOT FOUND IN REPORT DATA!")
