import frappe
from frappe.utils import flt, cint

def main(self):
    """Split Currency Calculation Logic."""
    # 1. INITIALIZE TOTALS
    total_earnings_usd = 0.0
    total_earnings_zwg = 0.0
    total_allowable_deductions_usd = 0.0
    total_allowable_deductions_zwg = 0.0
    total_deduction_usd = 0.0
    total_deduction_zwg = 0.0

    # 2. CALCULATE EARNINGS (GROSS)
    taxable_earnings_usd = 0.0
    taxable_earnings_zwg = 0.0
    for e in self.employee_earnings:
        total_earnings_usd += flt(e.amount_usd)
        total_earnings_zwg += flt(e.amount_zwg)
        
        component_doc = frappe.get_doc("havano_salary_component", e.components)
        if component_doc.is_tax_applicable:
            taxable_earnings_usd += flt(e.amount_usd)
            taxable_earnings_zwg += flt(e.amount_zwg)

    self.total_earnings_usd = round(total_earnings_usd, 2)
    self.total_earnings_zwg = round(total_earnings_zwg, 2)
    self.total_income = self.total_earnings_usd + self.total_earnings_zwg
    self.basic_salary_calculated = sum(flt(e.amount_usd) + flt(e.amount_zwg) for e in self.employee_earnings if e.components == "Basic Salary")

    # 3. EXCHANGE RATE
    exchange_rate = flt(frappe.db.get_value("Currency Exchange", {"from_currency": "USD", "to_currency": ["in", ["ZWG", "ZWL"]]}, "exchange_rate") or 1)

    # 4. BASE TAX CREDITS (elderly/blind/disabled)
    base_credits_usd = 0.0
    if getattr(self, "is_elderly", 0): base_credits_usd += 75
    if getattr(self, "is_blind", 0): base_credits_usd += 75
    if getattr(self, "is_disabled", 0): base_credits_usd += 75

    tax_credits_usd = base_credits_usd
    tax_credits_zwg = base_credits_usd * exchange_rate
    medical_credit_usd = 0.0
    medical_credit_zwg = 0.0

    # 5. CALCULATE DEDUCTIONS
    # Ensure mandatory rows exist if always_calculate is checked
    ensure_deductions(self)

    for d in self.employee_deductions:
        component_doc = frappe.get_doc("havano_salary_component", d.components)

        if d.components.upper() == "NSSA":
            nssa_limit_usd = 700
            nssa_income_usd = min(total_earnings_usd, nssa_limit_usd)
            d.amount_usd = round(nssa_income_usd * 0.045, 2)
            nssa_limit_zwg = 700 * exchange_rate
            nssa_income_zwg = min(total_earnings_zwg, nssa_limit_zwg)
            d.amount_zwg = round(nssa_income_zwg * 0.045, 2)

            total_allowable_deductions_usd += d.amount_usd
            total_allowable_deductions_zwg += d.amount_zwg
            total_deduction_usd += d.amount_usd
            total_deduction_zwg += d.amount_zwg

        elif d.components.upper() == "NEC":
            basic_usd = sum(flt(e.amount_usd) for e in self.employee_earnings if e.components == "Basic Salary")
            basic_zwg = sum(flt(e.amount_zwg) for e in self.employee_earnings if e.components == "Basic Salary")
            d.amount_usd = round(basic_usd * 0.015, 2)
            d.amount_zwg = round(basic_zwg * 0.015, 2)
            total_allowable_deductions_usd += d.amount_usd
            total_allowable_deductions_zwg += d.amount_zwg
            total_deduction_usd += d.amount_usd
            total_deduction_zwg += d.amount_zwg

        elif d.components.upper() in ["MEDICAL AID", "CIMAS"]:
            emp_pct = flt(self.cimas_employee_) / 100
            emp_contribution_usd = round(flt(d.amount_usd) * emp_pct, 2)
            emp_contribution_zwg = round(flt(d.amount_zwg) * emp_pct, 2)

            medical_credit_usd = round(emp_contribution_usd * 0.5, 2)
            medical_credit_zwg = round(emp_contribution_zwg * 0.5, 2)
            self.medical_aid_tax_credit = medical_credit_usd + medical_credit_zwg

            total_deduction_usd += emp_contribution_usd
            total_deduction_zwg += emp_contribution_zwg

        elif d.components.upper() in ["PAYEE", "AIDS LEVY", "SDL"]:
            continue

        else:
            total_deduction_usd += flt(d.amount_usd)
            total_deduction_zwg += flt(d.amount_zwg)
            if component_doc.is_tax_applicable:
                total_allowable_deductions_usd += flt(d.amount_usd)
                total_allowable_deductions_zwg += flt(d.amount_zwg)

    # Apply medical credit to tax credits
    tax_credits_usd += medical_credit_usd
    tax_credits_zwg += medical_credit_zwg
    self.total_tax_credits_usd = round(tax_credits_usd, 2)
    self.total_tax_credits_zwg = round(tax_credits_zwg, 2)

    self.total_allowable_deductions_usd = round(total_allowable_deductions_usd, 2)
    self.total_allowable_deductions_zwg = round(total_allowable_deductions_zwg, 2)

    # 6. TAXABLE INCOME = Taxable Earnings - Allowable Deductions
    self.total_taxable_income_usd = round(taxable_earnings_usd - total_allowable_deductions_usd, 2)
    self.total_taxable_income_zwg = round(taxable_earnings_zwg - total_allowable_deductions_zwg, 2)

    # 7. PAYE CALCULATION
    payee_usd = payee_against_slab(self.total_taxable_income_usd, self.payroll_frequency, "USD")
    payee_zwg = payee_against_slab(self.total_taxable_income_zwg, self.payroll_frequency, "ZWG")

    final_payee_usd = round(max(payee_usd - tax_credits_usd, 0), 2)
    final_payee_zwg = round(max(payee_zwg - tax_credits_zwg, 0), 2)

    aids_levy_usd = round(final_payee_usd * 0.03, 2)
    aids_levy_zwg = round(final_payee_zwg * 0.03, 2)

    # 8. UPDATE DEDUCTION TABLE
    for d in self.employee_deductions:
        if d.components.upper() == "PAYEE":
            d.amount_usd = final_payee_usd
            d.amount_zwg = final_payee_zwg
        elif d.components.upper() == "AIDS LEVY":
            d.amount_usd = aids_levy_usd
            d.amount_zwg = aids_levy_zwg
        elif d.components.upper() == "SDL":
            d.amount_usd = round(total_earnings_usd * 0.05, 2)
            d.amount_zwg = round(total_earnings_zwg * 0.05, 2)

    # 9. FINAL SUMMARY
    existing = [d.components.upper() for d in self.employee_deductions]
    if "PAYEE" not in existing:
        final_payee_usd = 0
        final_payee_zwg = 0
    if "AIDS LEVY" not in existing:
        aids_levy_usd = 0
        aids_levy_zwg = 0

    self.payee_usd = final_payee_usd
    self.payee_zwg = final_payee_zwg
    self.aids_levy_usd = aids_levy_usd
    self.aids_levy_zwg = aids_levy_zwg
    self.payee = final_payee_usd + final_payee_zwg

    total_deduction_usd += final_payee_usd + aids_levy_usd
    total_deduction_zwg += final_payee_zwg + aids_levy_zwg

    self.total_deduction_usd = round(total_deduction_usd, 2)
    self.total_deduction_zwg = round(total_deduction_zwg, 2)
    self.total_deductions = self.total_deduction_usd + self.total_deduction_zwg

    self.total_net_income_usd = round(total_earnings_usd - total_deduction_usd, 2)
    self.total_net_income_zwg = round(total_earnings_zwg - total_deduction_zwg, 2)
    self.net_income = self.total_net_income_usd + self.total_net_income_zwg

    self.sdl = round(self.total_income * 0.05, 2)

    # frappe.msgprint(
    #     f"<b>Split Currency Calculation:</b><br>"
    #     f"Gross USD: {self.total_earnings_usd} | Allowable Deductions: {self.total_allowable_deductions_usd}<br>"
    #     f"Taxable USD: {self.total_taxable_income_usd} | Tax Credits: {self.total_tax_credits_usd}<br>"
    #     f"Gross PAYEE: {payee_usd} | Final PAYEE: {final_payee_usd}<br>"
    #     f"AIDS Levy: {aids_levy_usd} | Net Income: {self.total_net_income_usd}"
    # )


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
    except Exception:
        pass
    return max(flt(payee), 0.0)


def ensure_deductions(self):
    """Ensures statutory rows exist in employee_deductions ONLY if always_calculate is checked."""
    existing = [d.components.upper() for d in self.employee_deductions]
    for comp in ["NSSA", "PAYEE", "AIDS LEVY"]:
        if comp not in existing:
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

