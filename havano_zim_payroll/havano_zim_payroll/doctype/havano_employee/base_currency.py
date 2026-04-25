import frappe
from frappe.utils import flt, now_datetime, nowdate, cint
from frappe import _

def main(self):
    # Standardize currency and frequency
    default_currency = frappe.db.get_value("Company", self.company, "default_currency")
    self.salary_currency = default_currency
    
    # 1. INITIALIZE TOTALS
    total_income = 0.0
    total_allowable_deductions = 0.0
    tax_credits = 0.0
    total_deduction = 0.0

    # Get Exchange Rate (USD to ZWG/ZWL)
    exchange_rate = flt(
        frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": "USD", "to_currency": ["in", ["ZWG", "ZWL"]]},
            "exchange_rate",
        )
        or 1
    )

    # 2. CALCULATE EARNINGS (GROSS SALARY)
    basic_salary = 0
    taxable_earnings = 0.0
    for e in self.employee_earnings:
        # Check if amount is in USD or ZWG based on company default
        if default_currency == "USD":
            amount = flt(e.amount_usd)
        else:
            amount = flt(e.amount_zwg)
        
        total_income += amount
        
        component_doc = frappe.get_doc("havano_salary_component", e.components)
        if component_doc.is_tax_applicable:
            taxable_earnings += amount
            
        if e.components == "Basic Salary":
            basic_salary = amount

    self.total_income = round(total_income, 2)
    self.basic_salary_calculated = basic_salary

    # 3. CALCULATE TAX CREDITS
    if getattr(self, "is_elderly", 0):
        val = 75 if self.salary_currency == "USD" else 75 * exchange_rate
        tax_credits += val
        self.elderly = val
    else:
        self.elderly = 0

    if getattr(self, "is_blind", 0):
        val = 75 if self.salary_currency == "USD" else 75 * exchange_rate
        tax_credits += val
        self.blind = val
    else:
        self.blind = 0

    if getattr(self, "is_disabled", 0):
        val = 75 if self.salary_currency == "USD" else 75 * exchange_rate
        tax_credits += val
        self.disabled = val
    else:
        self.disabled = 0

    # Medical Aid Credit (50% of employee contribution)
    cimas_employee_credit = 0
    for d in self.employee_deductions:
        if d.components.upper() in ["CIMAS", "MEDICAL AID"]:
            # If d.amount is the TOTAL, calculate employee portion
            amt = flt(d.amount_usd) if self.salary_currency == "USD" else flt(d.amount_zwg)
            emp_portion = amt * flt(self.cimas_employee_) / 100
            cimas_employee_credit = emp_portion * 0.5
            break
    
    tax_credits += cimas_employee_credit
    self.medical_aid_tax_credit = cimas_employee_credit
    self.total_tax_credits = round(tax_credits, 2)

    # 4. CALCULATE ALLOWABLE DEDUCTIONS
    # Remove rows for components with always_calculate unchecked, then ensure mandatory rows
    remove_unchecked_deductions(self)
    ensure_deductions(self)
    
    for d in self.employee_deductions:
        component_doc = frappe.get_doc("havano_salary_component", d.components)
        
        # Calculate NSSA if it's NSSA row
        if d.components.upper() == "NSSA":
            nssa_limit = 700 if self.salary_currency == "USD" else 700 * exchange_rate
            nssa_income = min(total_income, nssa_limit)
            nssa_amt = nssa_income * 0.045
            if self.salary_currency == "USD":
                d.amount_usd = nssa_amt
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = nssa_amt
            
            # NSSA is always allowable
            total_allowable_deductions += nssa_amt
            total_deduction += nssa_amt

        elif d.components.upper() in ["PAYEE", "AIDS LEVY", "SDL"]:
            # Skip these for now, calculate later
            continue
            
        else:
            # Other deductions (NEC, Pension, etc.)
            amt = flt(d.amount_usd) if self.salary_currency == "USD" else flt(d.amount_zwg)
            
            # Special logic for NEC
            if d.components.upper() == "NEC":
                amt = basic_salary * 0.015
                if self.salary_currency == "USD":
                    d.amount_usd = amt
                else:
                    d.amount_zwg = amt
            
            total_deduction += amt
            if component_doc.is_tax_applicable:
                total_allowable_deductions += amt

    self.allowable_deductions = round(total_allowable_deductions, 2)
    
    # 5. FINAL PAYE CALCULATION
    # Taxable Income = Taxable Earnings - Allowable Deductions
    self.ensuarable_earnings = round(taxable_earnings - self.allowable_deductions, 2)
    self.total_taxable_income = self.ensuarable_earnings

    # Get PAYE from Slab: ((Taxable * %) - Deduction)
    base_payee = payee_against_slab(self.ensuarable_earnings, self.payroll_frequency, self.salary_currency)
    
    # Final Payee = Base Payee - Total Tax Credits
    final_payee = round(max(base_payee - tax_credits, 0), 2)
    
    # Aids Levy = 3% of Payee
    aids_levy = round(final_payee * 0.03, 2)
    
    # SDL = 5% of Gross (reference only, not a deduction)
    # self.sdl = round(self.total_income * 0.05, 2)
    self.sdl = 0

    # 6. UPDATE DEDUCTION TABLE ROWS
    for d in self.employee_deductions:
        if d.components.upper() == "PAYEE":
            if self.salary_currency == "USD":
                d.amount_usd = final_payee
            else:
                d.amount_zwg = final_payee
        elif d.components.upper() == "AIDS LEVY":
            if self.salary_currency == "USD":
                d.amount_usd = aids_levy
            else:
                d.amount_zwg = aids_levy
        elif d.components.upper() == "SDL":
            d.amount_usd = 0
            d.amount_zwg = 0

    # 7. UPDATE TOTAL DEDUCTIONS AND NET INCOME
    total_deduction += final_payee + aids_levy
    self.payee = final_payee
    self.aids_levy = aids_levy
    self.total_deductions = round(total_deduction, 2)
    self.net_income = round(self.total_income - self.total_deductions, 2)

    # Update summary fields for display
    if default_currency == "USD":
        self.total_earnings_usd = self.total_income
        self.total_deduction_usd = self.total_deductions
        self.total_net_income_usd = self.net_income
        self.payee_usd = final_payee
        self.aids_levy_usd = aids_levy
        self.total_taxable_income_usd = self.total_taxable_income
    else:
        self.total_earnings_zwg = self.total_income
        self.total_deduction_zwg = self.total_deductions
        self.total_net_income_zwg = self.net_income
        self.payee_zwg = final_payee
        self.aids_levy_zwg = aids_levy
        self.total_taxable_income_zwg = self.total_taxable_income

    # Final debug message
    # frappe.msgprint(
    #     f"<b>Payroll Calculation:</b><br>"
    #     f"Gross: {self.total_income}<br>"
    #     f"Allowable Deductions: {self.allowable_deductions}<br>"
    #     f"Taxable Income: {self.total_taxable_income}<br>"
    #     f"Base PAYE: {base_payee}<br>"
    #     f"Tax Credits: {tax_credits}<br>"
    #     f"Final PAYE: {final_payee}<br>"
    #     f"Net Income: {self.net_income}"
    # )

def remove_unchecked_deductions(self):
    """Remove NSSA/PAYEE/AIDS LEVY rows from deductions where always_calculate is unchecked."""
    controlled = ["NSSA", "PAYEE", "AIDS LEVY"]
    to_remove = []
    for d in self.employee_deductions:
        upper = (d.components or "").upper()
        if upper in controlled:
            comp_name = frappe.db.get_value(
                "havano_salary_component",
                {"salary_component": ["like", d.components]},
                "salary_component"
            )
            always_calc = frappe.db.get_value(
                "havano_salary_component", comp_name, "always_calculate"
            ) if comp_name else 0
            if not always_calc:
                to_remove.append(d)
    
    for d in to_remove:
        self.remove(d)

def ensure_deductions(self):
    """Ensures statutory rows exist in employee_deductions ONLY if always_calculate is checked."""
    existing = [d.components.upper() for d in self.employee_deductions]
    for comp in ["NSSA", "PAYEE", "AIDS LEVY"]:
        if comp not in existing:
            # Only add if the salary component has always_calculate = 1
            comp_name = frappe.db.get_value(
                "havano_salary_component",
                {"salary_component": ["like", comp]},
                "salary_component"
            )
            if comp_name:
                always_calc = frappe.db.get_value(
                    "havano_salary_component", comp_name, "always_calculate"
                )
                if always_calc:
                    self.append("employee_deductions", {
                        "components": comp_name,
                        "amount_usd": 0,
                        "amount_zwg": 0
                    })


def payee_against_slab(amount, mode="Monthly", currency="USD"):
    if currency in ["ZWL", "ZWG"]:
        currency = "ZWG"
    
    payee = 0.0
    try:
        slab_name = f"{currency}-{mode}"
        if not frappe.db.exists("Havano Tax Slab", slab_name):
            slab_name = currency
            
        slab_doc = frappe.get_doc("Havano Tax Slab", slab_name)
        for slab in slab_doc.tax_brackets:
            if flt(slab.lower_limit) <= flt(amount) <= flt(slab.upper_limit):
                payee = (flt(amount) * (flt(slab.percent) / 100)) - flt(slab.fixed_amount)
                break
    except Exception as e:
        frappe.log_error(f"PAYE Calculation Error for {currency}: {e}")

    return max(flt(payee), 0.0)
