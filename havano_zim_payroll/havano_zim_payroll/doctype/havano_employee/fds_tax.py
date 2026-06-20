import frappe
from frappe.utils import flt, getdate, cint

def get_annual_tax(forecasted_income, currency="USD"):
    """
    Calculates Annual Tax using the provided Annual Table.
    If currency is ZWG, the USD thresholds are converted using the current exchange rate.
    """
    income = flt(forecasted_income)
    
    # 1. Exchange Rate Handling for ZWG
    exchange_rate = 1.0
    if currency in ["ZWL", "ZWG"]:
        exchange_rate = flt(
            frappe.db.get_value(
                "Currency Exchange",
                {"from_currency": "USD", "to_currency": ["in", ["ZWG", "ZWL"]]},
                "exchange_rate"
            )
            or 1.0
        )
        
    # Annual Table rules (USD base):
    # 0 to 1,200: 0%, Deduct 0
    # 1,201 to 3,600: 20%, Deduct 240
    # 3,601 to 12,000: 25%, Deduct 420
    # 12,001 to 24,000: 30%, Deduct 1,020
    # 24,001 to 36,000: 35%, Deduct 2,220
    # 36,001 and above: 40%, Deduct 4,020
    
    thresholds = [
        {"limit": 1200 * exchange_rate, "rate": 0.00, "deduct": 0 * exchange_rate},
        {"limit": 3600 * exchange_rate, "rate": 0.20, "deduct": 240 * exchange_rate},
        {"limit": 12000 * exchange_rate, "rate": 0.25, "deduct": 420 * exchange_rate},
        {"limit": 24000 * exchange_rate, "rate": 0.30, "deduct": 1020 * exchange_rate},
        {"limit": 36000 * exchange_rate, "rate": 0.35, "deduct": 2220 * exchange_rate},
        {"limit": float('inf'), "rate": 0.40, "deduct": 4020 * exchange_rate}
    ]
    
    for slab in thresholds:
        if income <= slab["limit"]:
            return (income * slab["rate"]) - slab["deduct"]
            
    return 0.0


def calculate_fds_tax(employee_id, first_name, last_name, current_taxable_income, currency, current_month_num, current_year):
    """
    FDS Method calculation:
    1. YTD Taxable Income = Sum(previous months taxable income)
    2. YTD PAYE = Sum(previous months PAYE)
    3. Forecasted Annual Income = YTD Taxable + current_taxable_income + (current_taxable_income * remaining_months)
    4. Annual Tax = get_annual_tax(Forecasted Annual Income)
    5. Total PAYE for remaining months = Annual Tax - YTD PAYE
    6. Current Month Base PAYE = Total PAYE for remaining months / (Remaining Months + 1)
    """
    if currency in ["ZWL", "ZWG"]:
        currency = "ZWG"

    remaining_months = 12 - cint(current_month_num)

    ytd_taxable_income = 0.0
    ytd_paye = 0.0

    # Fetch historical Havano Payroll Entry for this employee in the current year
    # We filter up to the previous month
    payroll_entries = frappe.get_all(
        "Havano Payroll Entry",
        filters={
            "first_name": first_name,
            "last_name": last_name,
            "date": ["between", [f"{current_year}-01-01", f"{current_year}-12-31"]]
        },
        fields=["name", "date"]
    )

    for pe in payroll_entries:
        pe_date = getdate(pe.date)
        if pe_date.month >= cint(current_month_num):
            continue # Only consider strict historical months!

        doc = frappe.get_doc("Havano Payroll Entry", pe.name)
        
        # Determine Taxable Earnings
        # In base_currency.py, they sum amounts where `is_tax_applicable` is true
        # Because we don't have that in the child table directly, we query the components
        taxable_components = [c.name for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
        
        entry_taxable = 0.0
        for e in doc.employee_earnings:
            if e.components in taxable_components:
                if currency == "USD":
                    entry_taxable += flt(e.amount_usd)
                else:
                    entry_taxable += flt(e.amount_zwg)
        
        # Determine Allowable Deductions
        allowable_components = []
        for c in frappe.get_all("havano_salary_component", filters={"type": "Deduction"}, fields=["name", "component_mode"]):
            if c.component_mode and "allowable" in c.component_mode.lower():
                allowable_components.append(c.name)
                
        if not frappe.db.get_single_value("Havano Payroll Settings", "include_nssa_in_taxable_income"):
            allowable_components.append("NSSA")
            
        entry_allowable = 0.0
        for d in doc.employee_deductions:
            if d.components in allowable_components:
                if currency == "USD":
                    entry_allowable += flt(d.amount_usd)
                else:
                    entry_allowable += flt(d.amount_zwg)
                    
        # YTD Taxable = Taxable Earnings - Allowable Deductions
        ytd_taxable_income += max(entry_taxable - entry_allowable, 0.0)

        # YTD PAYE
        for d in doc.employee_deductions:
            if (d.components or "").upper() == "PAYEE":
                if currency == "USD":
                    ytd_paye += flt(d.amount_usd)
                else:
                    ytd_paye += flt(d.amount_zwg)

    # Now calculate FDS
    cumulative_taxable_income = ytd_taxable_income + current_taxable_income
    forecasted_annual_income = cumulative_taxable_income + (current_taxable_income * remaining_months)
    
    annual_tax = get_annual_tax(forecasted_annual_income, currency)
    
    total_paye_for_remaining_months = max(annual_tax - ytd_paye, 0.0)
    
    current_month_base_paye = total_paye_for_remaining_months / (remaining_months + 1)
    
    # Return Base PAYE before tax credits and aids levy are applied in base_currency.py
    return max(flt(current_month_base_paye), 0.0)

@frappe.whitelist()
def test_taxes():
    from havano_zim_payroll.havano_zim_payroll.doctype.havano_employee.base_currency import payee_against_slab
    from frappe.utils import nowdate
    
    current_year = int(nowdate().split("-")[0])
    current_month = int(nowdate().split("-")[1])
    
    print("\n=================================================")
    print("--- NON-FDS EMPLOYEE (Joined this year) ---")
    non_fds = frappe.get_all("havano_employee", filters={"date_of_joining": [">=", f"{current_year}-01-01"], "ensuarable_earnings": [">", 0]}, limit=1)
    if non_fds:
        emp = frappe.get_doc("havano_employee", non_fds[0].name)
        print(f"Name: {emp.first_name} {emp.last_name}")
        print(f"Date of Joining: {emp.date_of_joining} (Skips FDS)")
        print(f"Taxable Income: {emp.ensuarable_earnings} {emp.salary_currency}")
        slab_paye = payee_against_slab(emp.ensuarable_earnings, emp.payroll_frequency, emp.salary_currency)
        print(f"-> Base PAYE Calculated: {slab_paye}")
    else:
        print("No Non-FDS employee found with taxable earnings.")

    print("\n-------------------------------------------------")
    print("--- FDS EMPLOYEE (Joined before this year) ---")
    fds = frappe.get_all("havano_employee", filters={"date_of_joining": ["<", f"{current_year}-01-01"], "ensuarable_earnings": [">", 0]}, limit=1)
    if fds:
        emp = frappe.get_doc("havano_employee", fds[0].name)
        print(f"Name: {emp.first_name} {emp.last_name}")
        print(f"Date of Joining: {emp.date_of_joining} (FDS Eligible!)")
        print(f"Current Taxable Income: {emp.ensuarable_earnings} {emp.salary_currency}")
        
        # Calculate using both methods to compare
        slab_paye = payee_against_slab(emp.ensuarable_earnings, emp.payroll_frequency, emp.salary_currency)
        fds_paye = calculate_fds_tax(emp.name, emp.first_name, emp.last_name, emp.ensuarable_earnings, emp.salary_currency, current_month, str(current_year))
        
        print(f"-> Base PAYE (Old Slab Method): {slab_paye}")
        print(f"-> Base PAYE (New FDS Method):  {fds_paye}")
        
        if fds_paye != slab_paye:
            print("\n(Notice how the FDS method adjusted the tax based on forecasted annual income!)")
    else:
        print("No FDS employee found with taxable earnings.")
    print("=================================================\n")
