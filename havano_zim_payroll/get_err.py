import frappe
import os

def run():
    print(f"Running on site: {frappe.local.site}")
    
    settings = frappe.get_single("Havano Payroll Settings")
    print(f"Supplier: {settings.get('supplier')}")
    print(f"Cost Center: {settings.get('cost_center')}")
    print(f"Create Journal Entry: {settings.get('create_journal_entry')}")
    print(f"Default Payroll Payable Account: {settings.get('default_payroll_payable_account')}")
    
    # Print latest error logs in case it's a silent failure
    logs = frappe.get_all("Error Log", fields=["name", "creation", "method", "error"], order_by="creation desc", limit=3)
    print("Latest Error Logs:")
    for log in logs:
        print(f"[{log.creation}] {log.method}")
        print(log.error[:300])
        print("...")
