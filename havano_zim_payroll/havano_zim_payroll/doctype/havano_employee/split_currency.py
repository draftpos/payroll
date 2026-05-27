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
    basic_salary_usd = 0.0
    basic_salary_zwg = 0.0
    for e in self.employee_earnings:
        if not e.components:
            continue
        if e.components.upper() == "MOTORING BENEFIT":
            if getattr(self, "has_motoring_benefit", 0) and getattr(self, "engine_capacity", None):
                deemed_usd = flt(frappe.db.get_value("Havano Motoring Benefit", {"engine_capacity": self.engine_capacity}, "deemed_value_usd"))
                e.amount_usd = deemed_usd
                e.amount_zwg = 0
                
            taxable_earnings_usd += flt(e.amount_usd)
            taxable_earnings_zwg += flt(e.amount_zwg)
            continue
            
        total_earnings_usd += flt(e.amount_usd)
        total_earnings_zwg += flt(e.amount_zwg)
        
        if e.is_tax_applicable:
            taxable_earnings_usd += flt(e.amount_usd)
            taxable_earnings_zwg += flt(e.amount_zwg)

        if (e.components or "") == "Basic Salary":
            basic_salary_usd = flt(e.amount_usd)
            basic_salary_zwg = flt(e.amount_zwg)

    self.total_earnings_usd = round(total_earnings_usd, 2)
    self.total_earnings_zwg = round(total_earnings_zwg, 2)
    self.total_income = self.total_earnings_usd + self.total_earnings_zwg
    self.basic_salary_calculated = basic_salary_usd + basic_salary_zwg

    # --- MOTORING BENEFIT ---
    _mot_currency = "USD" if basic_salary_usd else "ZWG"
    apply_motoring_benefit(self, _mot_currency, exchange_rate)

    # --- CASH IN LIEU OF LEAVE ---
    _cil_basic    = basic_salary_usd if basic_salary_usd else basic_salary_zwg
    _cil_currency = "USD" if basic_salary_usd else "ZWG"
    apply_cash_in_lieu(self, _cil_basic, _cil_currency)
    total_earnings_usd += flt(self.cash_in_lieu_amount) if _cil_currency == "USD" else 0.0
    total_earnings_zwg += flt(self.cash_in_lieu_amount) if _cil_currency != "USD" else 0.0

    # --- OVERTIME ---
    _ot_basic    = basic_salary_usd if basic_salary_usd else basic_salary_zwg
    _ot_currency = "USD" if basic_salary_usd else "ZWG"
    apply_overtime(self, _ot_basic, _ot_currency)
    total_earnings_usd += flt(self.overtime_amount) if _ot_currency == "USD" else 0.0
    total_earnings_zwg += flt(self.overtime_amount) if _ot_currency != "USD" else 0.0

    # --- SHORT TIME ---
    apply_short_time(self, _ot_basic, _ot_currency)

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

    include_nssa = 0
    try:
        include_nssa = frappe.db.get_single_value("Havano Payroll Settings", "include_nssa_in_taxable_income") or 0
    except Exception:
        pass

    for d in self.employee_deductions:
        if not d.components:
            continue
            
        component_doc = frappe.get_doc("havano_salary_component", d.components)

        if d.components.upper() == "NSSA":
            # Read calculation basis from the salary component
            nssa_basis = frappe.db.get_value("havano_salary_component", d.components, "nssa_calculation_basis") or "Gross Salary"
            # Use basic salary or gross earnings depending on setting
            nssa_base_usd = basic_salary_usd if nssa_basis == "Basic Only" else total_earnings_usd
            nssa_base_zwg = basic_salary_zwg if nssa_basis == "Basic Only" else total_earnings_zwg

            nssa_limit_usd = 700
            nssa_income_usd = min(nssa_base_usd, nssa_limit_usd)
            d.amount_usd = round(nssa_income_usd * 0.045, 2)
            nssa_limit_zwg = 700 * exchange_rate
            nssa_income_zwg = min(nssa_base_zwg, nssa_limit_zwg)
            d.amount_zwg = round(nssa_income_zwg * 0.045, 2)

            # NSSA is allowable if NOT "Include NSSA in Taxable Income"
            if not include_nssa:
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

        elif d.components.upper() in ["MEDICAL AID", "CIMAS", "MEDICAL AID EXPENSE"]:
            # Initialize original amount if not set
            if not getattr(d, "original_amount_usd", 0):
                d.original_amount_usd = d.amount_usd
                d.original_amount_zwg = d.amount_zwg
            
            emp_pct = flt(self.cimas_employee_) / 100
            
            base_amt_usd = flt(d.original_amount_usd)
            base_amt_zwg = flt(d.original_amount_zwg)
            
            emp_contribution_usd = round(base_amt_usd * emp_pct, 2)
            emp_contribution_zwg = round(base_amt_zwg * emp_pct, 2)

            medical_credit_usd = round(emp_contribution_usd * 0.5, 2)
            medical_credit_zwg = round(emp_contribution_zwg * 0.5, 2)
            self.medical_aid_tax_credit = medical_credit_usd + medical_credit_zwg

            # Update row amounts for UI and Payslip
            d.amount_usd = emp_contribution_usd
            d.amount_zwg = emp_contribution_zwg

            total_deduction_usd += emp_contribution_usd
            total_deduction_zwg += emp_contribution_zwg

        elif d.components.upper() in ["PAYEE", "AIDS LEVY", "SDL"]:
            continue

        elif d.components.upper() in ["LAPF", "UFAWUZ", "ZFBAWU"]:
            comp_data = frappe.db.get_value("havano_salary_component", d.components,
                ["employee_amount", "employer_amount"], as_dict=True) or {}
            emp_pct = flt(comp_data.get("employee_amount") or 0) / 100.0
            emp_amt_usd = round(basic_salary_usd * emp_pct, 2)
            emp_amt_zwg = round(basic_salary_zwg * emp_pct, 2)
            d.amount_usd = emp_amt_usd
            d.amount_zwg = emp_amt_zwg
            total_deduction_usd += emp_amt_usd
            total_deduction_zwg += emp_amt_zwg
            total_allowable_deductions_usd += emp_amt_usd
            total_allowable_deductions_zwg += emp_amt_zwg
            if d.components.upper() == "LAPF":
                emp_pct_val = flt(comp_data.get("employer_amount") or 0) / 100.0
                self.lapf_employee = emp_amt_usd + emp_amt_zwg
                self.lapf_employer = round((basic_salary_usd + basic_salary_zwg) * emp_pct_val, 2)
            continue

        else:
            total_deduction_usd += flt(d.amount_usd)
            total_deduction_zwg += flt(d.amount_zwg)
            if d.is_tax_applicable or (component_doc and component_doc.component_mode and "allowable" in component_doc.component_mode.lower()):
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
    self.total_ensuarable_earnings_usd = round(taxable_earnings_usd, 2)
    self.total_ensuarable_earnings_zwg = round(taxable_earnings_zwg, 2)
    self.total_taxable_income_usd = round(self.total_ensuarable_earnings_usd - total_allowable_deductions_usd, 2)
    self.total_taxable_income_zwg = round(self.total_ensuarable_earnings_zwg - total_allowable_deductions_zwg, 2)

    # 7. PAYE CALCULATION
    payee_usd = payee_against_slab(self.total_taxable_income_usd, self.payroll_frequency, "USD")
    payee_zwg = payee_against_slab(self.total_taxable_income_zwg, self.payroll_frequency, "ZWG")

    final_payee_usd = round(max(payee_usd - tax_credits_usd, 0), 2)
    final_payee_zwg = round(max(payee_zwg - tax_credits_zwg, 0), 2)

    aids_levy_usd = round(final_payee_usd * 0.03, 2)
    aids_levy_zwg = round(final_payee_zwg * 0.03, 2)

    # 8. UPDATE DEDUCTION TABLE
    for d in self.employee_deductions:
        if not d.components:
            continue
            
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
    existing = [(d.components or "").upper() for d in self.employee_deductions]
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
    existing = [(d.components or "").upper() for d in self.employee_deductions]
    
    medical_aid_comp = "CIMAS"
    try:
        medical_aid_comp = frappe.db.get_single_value("Havano Payroll Settings", "medical_aid_component_name") or "CIMAS"
    except Exception:
        pass

    for comp in ["NSSA", "PAYEE", "AIDS LEVY", medical_aid_comp.upper()]:
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



def apply_overtime(self, basic_salary, default_currency_split):
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

    is_double_split = ot_type == 'Time & Half and Double Time'
    if not basic_salary or not ot_type:
        self.hourly_rate     = 0.0
        self.overtime_amount = 0.0
        return
    if not is_double_split and ot_hours <= 0:
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
    elif ot_type == 'Time & Half and Double Time':
        from frappe.utils import flt as _flt
        half_hours   = _flt(getattr(self, 'hours_half', 0) or 0)
        double_hours = _flt(getattr(self, 'hours_double', 0) or 0)
        half_amount  = round(half_hours * hourly_rate * 1.5, 2)
        double_amount = round(double_hours * hourly_rate * 2, 2)
        self.half_amount   = half_amount
        self.double_amount = double_amount
        self.overtime_amount = half_amount + double_amount
        if half_hours > 0:
            a_usd = half_amount if default_currency_split == 'USD' else 0.0
            a_zwg = half_amount if default_currency_split != 'USD' else 0.0
            self.append('employee_earnings', {'components': 'Overtime Short', 'amount_usd': a_usd, 'amount_zwg': a_zwg, 'is_tax_applicable': 0})
        if double_hours > 0:
            a_usd = double_amount if default_currency_split == 'USD' else 0.0
            a_zwg = double_amount if default_currency_split != 'USD' else 0.0
            self.append('employee_earnings', {'components': 'Overtime Double', 'amount_usd': a_usd, 'amount_zwg': a_zwg, 'is_tax_applicable': 1})
        return
    else:
        self.overtime_amount = 0.0
        return

    self.overtime_amount = ot_amount

    # Inject into earnings table
    amount_usd = ot_amount if default_currency_split == "USD" else 0.0
    amount_zwg = ot_amount if default_currency_split != "USD" else 0.0

    self.append("employee_earnings", {
        "components":        comp_name,
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
        "is_tax_applicable": is_taxable,
    })


def apply_cash_in_lieu(self, basic_salary, default_currency_split):
    """
    Cash in Lieu of Leave:
      Formula mode (enabled in Havano Payroll Settings):
        Daily Rate = Basic Salary / 26
        Amount     = Days to Sell * Daily Rate
      Manual mode: use the entered cash_in_lieu_amount directly
    """
    import frappe
    from frappe.utils import flt

    days_to_sell = flt(getattr(self, "leave_days_to_sell", 0.0)) or 0.0

    self.employee_earnings = [
        e for e in self.employee_earnings
        if (e.components or "") != "cash in lieu of leave"
    ]

    use_formula = frappe.db.get_single_value("Havano Payroll Settings", "use_formula_cash_in_lieu")

    if use_formula:
        if not basic_salary or days_to_sell <= 0:
            self.cash_in_lieu_amount = 0.0
            return
        daily_rate = basic_salary / 26.0
        amount = round(days_to_sell * daily_rate, 2)
        self.cash_in_lieu_amount = amount
    else:
        amount = flt(getattr(self, "cash_in_lieu_amount", 0.0)) or 0.0
        if amount <= 0:
            return

    amount_usd = amount if default_currency_split == "USD" else 0.0
    amount_zwg = amount if default_currency_split != "USD" else 0.0

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


def apply_short_time(self, basic_salary, default_currency_split):
    """Short Time: removes row then re-adds with negative amount if has_short_time is checked."""
    from frappe.utils import flt
    self.employee_earnings = [
        e for e in self.employee_earnings
        if (e.components or "") != "Short Time"
    ]
    if not getattr(self, "has_short_time", 0):
        return
    days_worked = flt(getattr(self, "short_time_days_worked", 0))
    standard_days = 26.0
    if not basic_salary or not (0 < days_worked < standard_days):
        return
    short_days = standard_days - days_worked
    daily_rate = basic_salary / standard_days
    short_amount = round(daily_rate * short_days, 2)
    amount_usd = -short_amount if default_currency_split == "USD" else 0.0
    amount_zwg = -short_amount if default_currency_split != "USD" else 0.0
    self.append("employee_earnings", {
        "components":        "Short Time",
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
        "is_tax_applicable": 0,
    })
    self.net_income = round(self.net_income - short_amount, 2)
