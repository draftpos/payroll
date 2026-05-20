import frappe
from frappe.utils import flt

def run_test():
    # 1. Fetch an existing active employee
    emp_names = frappe.get_all("havano_employee", filters={"status": "Active"}, limit=1)
    if not emp_names:
        print("No active havano_employee found. Creating a temporary one...")
        return
        
    emp_name = emp_names[0].name
    emp_doc = frappe.get_doc("havano_employee", emp_name)
    
    print(f"Testing calculations on employee: {emp_doc.name}")
    print(f"Original Payslip Type: {emp_doc.payslip_type}")
    print(f"Original Allowable Deductions: {emp_doc.total_allowable_deductions_usd if emp_doc.payslip_type == 'Split Currency' else emp_doc.allowable_deductions}")

    # Ensure a NSSA deduction row exists and is calculated
    nssa_row = None
    for d in emp_doc.employee_deductions:
        if d.components.upper() == "NSSA":
            nssa_row = d
            break
    if not nssa_row:
        emp_doc.append("employee_deductions", {
            "components": "NSSA",
            "amount_usd": 0,
            "amount_zwg": 0
        })
    
    # 2. Get settings doc or create it
    settings = frappe.get_single("Havano Payroll Settings")
    
    # --- TEST 1: Exclude NSSA (default) ---
    print("\n--- Test Case 1: Exclude NSSA (default, Checkbox unchecked) ---")
    settings.include_nssa_in_taxable_income = 0
    settings.save()
    frappe.db.commit()
    
    # Run calculation
    emp_doc.calculate_totals()
    
    # Find NSSA deduction amount
    nssa_amt = 0
    for d in emp_doc.employee_deductions:
        if d.components.upper() == "NSSA":
            nssa_amt = flt(d.amount_usd) if emp_doc.payslip_type == "Split Currency" or emp_doc.salary_currency == "USD" else flt(d.amount_zwg)
            break
            
    allowable = flt(emp_doc.total_allowable_deductions_usd) if emp_doc.payslip_type == "Split Currency" else flt(emp_doc.allowable_deductions)
    print(f"Calculated NSSA amount: {nssa_amt}")
    print(f"Calculated Allowable Deductions: {allowable}")
    if nssa_amt > 0 and allowable >= nssa_amt:
        print("Success: NSSA is included in allowable deductions.")
    else:
        print("Verification pending/failed: NSSA amount is 0 or not in allowable deductions.")

    # --- TEST 2: Include NSSA ---
    print("\n--- Test Case 2: Include NSSA (Checkbox checked) ---")
    settings.include_nssa_in_taxable_income = 1
    settings.save()
    frappe.db.commit()
    
    # Run calculation
    emp_doc.calculate_totals()
    
    # Find NSSA deduction amount
    nssa_amt_2 = 0
    for d in emp_doc.employee_deductions:
        if d.components.upper() == "NSSA":
            nssa_amt_2 = flt(d.amount_usd) if emp_doc.payslip_type == "Split Currency" or emp_doc.salary_currency == "USD" else flt(d.amount_zwg)
            break
            
    allowable_2 = flt(emp_doc.total_allowable_deductions_usd) if emp_doc.payslip_type == "Split Currency" else flt(emp_doc.allowable_deductions)
    print(f"Calculated NSSA amount: {nssa_amt_2}")
    print(f"Calculated Allowable Deductions: {allowable_2}")
    
    # Allowable deductions must not contain NSSA
    if nssa_amt_2 > 0 and allowable_2 <= allowable - nssa_amt:
        print("Success: NSSA is NOT in allowable deductions when checkbox is checked.")
    else:
        print("Fail/Unexpected: Allowable deductions still contains NSSA.")

if __name__ == "__main__":
    run_test()
