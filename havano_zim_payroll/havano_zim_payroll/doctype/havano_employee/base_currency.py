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
        if not e.components:
            continue
        # Motoring Benefit Logic
        if e.components.upper() == "MOTORING BENEFIT":
            if getattr(self, "has_motoring_benefit", 0) and getattr(self, "engine_capacity", None):
                deemed_usd = flt(frappe.db.get_value("Havano Motoring Benefit", {"engine_capacity": self.engine_capacity}, "deemed_value_usd"))
                
                # Auto-set the amounts based on currency
                if default_currency == "USD":
                    e.amount_usd = deemed_usd
                    e.amount_zwg = 0
                    amount = deemed_usd
                else:
                    e.amount_usd = 0
                    e.amount_zwg = deemed_usd * exchange_rate
                    amount = deemed_usd * exchange_rate
                    
            # Check if amount is in USD or ZWG based on company default
            if default_currency == "USD":
                amount = flt(e.amount_usd)
            else:
                amount = flt(e.amount_zwg)

            # Motoring benefit is taxable but does NOT increase gross total_income
            taxable_earnings += amount
            continue

        # Check if amount is in USD or ZWG based on company default
        if default_currency == "USD":
            amount = flt(e.amount_usd)
        else:
            amount = flt(e.amount_zwg)
        
        total_income += amount
        
        if e.is_tax_applicable:
            taxable_earnings += amount
            
        if e.components == "Basic Salary":
            basic_salary = amount

    self.total_income = round(total_income, 2)
    self.basic_salary_calculated = basic_salary

    # --- MOTORING BENEFIT ---
    apply_motoring_benefit(self, default_currency, exchange_rate)

    # --- CASH IN LIEU OF LEAVE ---
    apply_cash_in_lieu(self, basic_salary, default_currency)
    total_income += flt(self.cash_in_lieu_amount)
    self.total_income = round(total_income, 2)

    # --- OVERTIME ---
    apply_overtime(self, basic_salary, default_currency)
    total_income += flt(self.overtime_amount)
    self.total_income = round(total_income, 2)

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
        if d.components.upper() in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE"]:
            # If d.amount is the TOTAL, calculate employee portion
            amt = flt(d.amount_usd) if self.salary_currency == "USD" else flt(d.amount_zwg)
            emp_portion = amt * flt(self.cimas_employee_) / 100
            cimas_employee_credit = emp_portion * 0.5
            break
    
    tax_credits += cimas_employee_credit
    self.medical_aid_tax_credit = cimas_employee_credit
    self.total_tax_credits = round(tax_credits, 2)

    # 4. CALCULATE ALLOWABLE DEDUCTIONS
    # Ensure mandatory rows exist if always_calculate is checked
    ensure_deductions(self)
    
    include_nssa = 0
    try:
        include_nssa = frappe.db.get_single_value("Havano Payroll Settings", "include_nssa_in_taxable_income") or 0
    except Exception:
        pass
    
    for d in self.employee_deductions:
        if not d.components:
            continue
            
        component_doc = frappe.get_doc("havano_salary_component", d.components)
        
        # Calculate NSSA if it's NSSA row
        if d.components.upper() == "NSSA":
            # Read calculation basis from the salary component
            nssa_basis = frappe.db.get_value("havano_salary_component", d.components, "nssa_calculation_basis") or "Gross Salary"
            # Use basic salary or gross income depending on setting
            nssa_base_income = basic_salary if nssa_basis == "Basic Only" else total_income
            nssa_limit = 700 if self.salary_currency == "USD" else 700 * exchange_rate
            nssa_income = min(nssa_base_income, nssa_limit)
            nssa_amt = nssa_income * 0.045
            if self.salary_currency == "USD":
                d.amount_usd = nssa_amt
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = nssa_amt
            
            # NSSA is allowable if NOT "Include NSSA in Taxable Income"
            if not include_nssa:
                total_allowable_deductions += nssa_amt
            total_deduction += nssa_amt

        elif d.components.upper() in ["PAYEE", "AIDS LEVY", "SDL"]:
            # Skip these for now, calculate later
            continue
            
        elif d.components.upper() in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE"]:
            amt = flt(d.amount_usd) if self.salary_currency == "USD" else flt(d.amount_zwg)
            emp_portion = amt * flt(self.cimas_employee_) / 100
            total_deduction += emp_portion
            
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
            if d.is_tax_applicable or (component_doc and component_doc.component_mode and "allowable" in component_doc.component_mode.lower()):
                total_allowable_deductions += amt

    self.allowable_deductions = round(total_allowable_deductions, 2)
    
    # 5. FINAL PAYE CALCULATION
    # NOTE: In the UI, the labels are swapped!
    # Fieldname 'total_taxable_income' is labeled as "Ensurable Earnings" (Gross)
    # Fieldname 'ensuarable_earnings' is labeled as "Total Taxable Income" (Net)
    
    self.total_taxable_income = round(taxable_earnings, 2)
    self.ensuarable_earnings = round(self.total_taxable_income - self.allowable_deductions, 2)

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
        if not d.components:
            continue
            
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
    existing = [(d.components or "").upper() for d in self.employee_deductions]
    if "PAYEE" not in existing:
        final_payee = 0
    if "AIDS LEVY" not in existing:
        aids_levy = 0

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

def ensure_deductions(self):
    """Ensures statutory rows exist in employee_deductions ONLY if always_calculate is checked."""
    existing = [(d.components or "").upper() for d in self.employee_deductions]
    
    medical_aid_comp = "CIMAS"
    try:
        medical_aid_comp = frappe.db.get_single_value("Havano Payroll Settings", "medical_aid_component_name") or "CIMAS"
    except Exception:
        pass

    for comp in ["NSSA", "PAYEE", "AIDS LEVY", medical_aid_comp.upper()]:
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


def apply_overtime(self, basic_salary, default_currency):
    """
    Overtime Calculation Formula:
      Daily Rate  = Basic Salary / 26
      Hourly Rate = Daily Rate / 7.5
      Double Time = Hours * Hourly Rate * 2        -> component: Overtime Double (taxable)
      Time & Half = Hours * Hourly Rate * 1.5      -> component: Overtime Short  (not taxable)
    """
    from frappe.utils import flt

    days_worked = 26.0
    ot_hours    = flt(self.hours) or 0.0
    ot_type     = (self.overtime or "").strip()

    # Always remove both overtime rows first (clean slate)
    self.employee_earnings = [
        e for e in self.employee_earnings
        if (e.components or "") not in ("Overtime Double", "Overtime Short")
    ]

    if not basic_salary or ot_hours <= 0 or not ot_type:
        self.hourly_rate     = 0.0
        self.overtime_amount = 0.0
        return

    daily_rate  = basic_salary / days_worked
    hourly_rate = daily_rate / 7.5
    self.hourly_rate = round(hourly_rate, 4)

    if ot_type == "Double Time":
        ot_amount    = round(ot_hours * hourly_rate * 2, 2)
        comp_name    = "Overtime Double"
        is_taxable   = 1
    elif ot_type == "Time & Half":
        ot_amount    = round(ot_hours * hourly_rate * 1.5, 2)
        comp_name    = "Overtime Short"
        is_taxable   = 0
    else:
        self.overtime_amount = 0.0
        return

    self.overtime_amount = ot_amount

    # Inject into earnings table
    amount_usd = ot_amount if default_currency == "USD" else 0.0
    amount_zwg = ot_amount if default_currency != "USD" else 0.0

    self.append("employee_earnings", {
        "components":        comp_name,
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
        "is_tax_applicable": is_taxable,
    })


def apply_cash_in_lieu(self, basic_salary, default_currency):
    """
    Cash in Lieu of Leave:
      Daily Rate = Basic Salary / 26
      Amount     = Days to Sell * Daily Rate
    """
    from frappe.utils import flt

    days_to_sell = flt(self.leave_days_to_sell) or 0.0

    # Remove existing cash in lieu row (clean slate)
    self.employee_earnings = [
        e for e in self.employee_earnings
        if (e.components or "") != "cash in lieu of leave"
    ]

    if not basic_salary or days_to_sell <= 0:
        self.cash_in_lieu_amount = 0.0
        return

    daily_rate = basic_salary / 26.0
    amount = round(days_to_sell * daily_rate, 2)
    self.cash_in_lieu_amount = amount

    amount_usd = amount if default_currency == "USD" else 0.0
    amount_zwg = amount if default_currency != "USD" else 0.0

    self.append("employee_earnings", {
        "components":        "cash in lieu of leave",
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
        "is_tax_applicable": 0,
    })


def apply_motoring_benefit(self, default_currency, exchange_rate=1.0):
    """
    Auto-inject Motoring Benefit row into earnings.
    Amount = deemed_value_usd from Havano Motoring Benefit table (by engine_capacity).
    Taxable but does NOT count toward gross total_income (ZIMRA rule).
    """
    import frappe
    from frappe.utils import flt

    # Always remove existing row first (clean slate)
    self.employee_earnings = [
        e for e in self.employee_earnings
        if (e.components or "").upper() != "MOTORING BENEFIT"
    ]

    if not getattr(self, "has_motoring_benefit", 0) or not getattr(self, "engine_capacity", None):
        return

    deemed_usd = flt(frappe.db.get_value("Havano Motoring Benefit", {"engine_capacity": self.engine_capacity}, "deemed_value_usd"))
    if not deemed_usd:
        return

    if default_currency == "USD":
        amount_usd = deemed_usd
        amount_zwg = 0.0
    else:
        amount_usd = 0.0
        amount_zwg = round(deemed_usd * flt(exchange_rate), 2)

    self.append("employee_earnings", {
        "components":        "Motoring Benefit",
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
        "is_tax_applicable": 1,
    })
