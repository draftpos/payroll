import frappe
from frappe.desk.query_report import run as run_report
import json

def run():
    print("\n--- API ENDPOINT CHECK ---")
    try:
        res = run_report("FDS Taxable Income Report", filters={"year": "2026"})
        
        data = res.get('result', [])
        found = False
        for d in data:
            if isinstance(d, dict) and d.get("first_name", "").upper() == "JUSA":
                print("JUSA RETURNED TO BROWSER:", d)
                found = True
                
        if not found:
            print("JUSA NOT FOUND IN API RESPONSE!")
    except Exception as e:
        print("ERROR RUNNING REPORT API:", e)
    print("--- DONE ---")
