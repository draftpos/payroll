import frappe

def execute():
    try:
        # Create a dummy company
        if not frappe.db.exists("Company", "Dummy Company"):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": "Dummy Company",
                "default_currency": "USD"
            }).insert(ignore_permissions=True)
        
        # Create a dummy employee
        if not frappe.db.exists("havano_employee", "EMP-001"):
            frappe.get_doc({
                "doctype": "havano_employee",
                "first_name": "John",
                "last_name": "Doe",
                "company": "Dummy Company",
                "status": "Active",
                "payroll_frequency": "Monthly",
                "salary_currency": "USD",
                "employee_earnings": [
                    {"components": "Basic Salary", "amount_usd": 1000}
                ],
                "employee_deductions": [
                    {"components": "PAYE", "amount_usd": 100},
                    {"components": "Medical Aid", "amount_usd": 50}
                ]
            }).insert(ignore_permissions=True)
        
        # Run payroll
        from havano_zim_payroll.havano_zim_payroll.api import run_payroll
        res = run_payroll(6, 2026, "2026-06-30", 0)
        print("Payroll result:", res)
        
        # Check journal
        journals = frappe.get_all("Havano Payroll Journal", fields=["name", "company", "payroll_period"])
        print("Journals found:", journals)
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
