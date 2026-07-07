import frappe
import traceback
from havano_zim_payroll.api import run_payroll

def run_tests():
    print("\n--- Starting Unit Tests for run_payroll ---")
    test_month = "June"
    test_year = "2026"
    period_name = f"{test_month} {test_year}"
    
    try:
        # 1. Clean up existing records for the test month to ensure a fresh test
        entries = frappe.get_all("Havano Payroll Entry", filters={"payroll_period": period_name})
        for e in entries:
            frappe.delete_doc("Havano Payroll Entry", e.name, ignore_permissions=True)
            
        print(f"Cleaned up {len(entries)} old Payroll Entries for {period_name}.")
        
        # 2. Run the payroll script
        print(f"Running payroll for {period_name}...")
        res = run_payroll(test_month, test_year, None, 0)
        print("Payroll Run returned:", res)
        
        # 3. Assertions and Verifications
        
        # Verify Havano Payroll Entry
        new_entries = frappe.get_all("Havano Payroll Entry", filters={"payroll_period": period_name})
        if not new_entries:
            print(f"ERROR: No Havano Payroll Entry created for {period_name}.")
            frappe.throw("Unit Test Failed: No Payroll Entries created.")
        else:
            print(f"SUCCESS: Found {len(new_entries)} Havano Payroll Entries for {period_name}.")
            
        # Verify Havano Payroll Journal
        journals = frappe.get_all("Havano Payroll Journal", filters={"payroll_period": period_name})
        if not journals:
            print(f"WARNING: No Havano Payroll Journal found for {period_name}. (Could be intentional if create_journal_entry is off)")
        else:
            print(f"SUCCESS: Found {len(journals)} Havano Payroll Journals.")
            
        # Verify Havano Employer Contributions Journal
        ecj = frappe.get_all("Havano Employer Contributions Journal", filters={"payroll_period": period_name})
        if not ecj:
            print(f"WARNING: No Havano Employer Contributions Journal found for {period_name}.")
        else:
            print(f"SUCCESS: Found {len(ecj)} Havano Employer Contributions Journals.")
            
        # Verify standard Accounting Journal Entries
        je_remark = f"Payroll Journal Entry for {period_name}"
        jes = frappe.get_all("Journal Entry", filters={"user_remark": je_remark})
        if not jes:
            print(f"WARNING: No Accounting Journal Entries found for {period_name}.")
        else:
            print(f"SUCCESS: Found {len(jes)} Accounting Journal Entries created by payroll.")
            
        print("\n--- Unit Tests Completed Successfully ---")
        
    except frappe.exceptions.LinkValidationError as e:
        print("\nERROR: LinkValidationError caught! This is the exact error we are trying to prevent.")
        print(e)
        traceback.print_exc()
        raise
    except Exception as e:
        print("\nERROR during Unit Tests:", e)
        traceback.print_exc()
        raise
