import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate


def main(self):
    default_currency = frappe.db.get_value("Company", self.company, "default_currency")
    self.salary_currency = default_currency

    # ── Tax credits ──────────────────────────────────────────────────────────
    tax_credits_usd = 0.0
    tax_credits_zwg = 0.0

    exchange_rate = flt(
        frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": "USD", "to_currency": "ZWL"},
            "exchange_rate",
        )
        or 1
    )

    if getattr(self, "is_elderly", 0):
        tax_credits_usd += 75
        tax_credits_zwg += 75 * exchange_rate
        self.elderly = 75
    else:
        self.elderly = 0

    if getattr(self, "is_blind", 0):
        tax_credits_usd += 75
        tax_credits_zwg += 75 * exchange_rate
        self.blind = 75
    else:
        self.blind = 0

    if getattr(self, "is_disabled", 0):
        tax_credits_usd += 75
        tax_credits_zwg += 75 * exchange_rate
        self.disabled = 75
    else:
        self.disabled = 0

    # Read any extra tax credits from the employee's tax_credits child table
    for tc in getattr(self, "tax_credits", []):
        tax_credits_usd += flt(tc.amount_usd)
        tax_credits_zwg += flt(tc.amount_zwg)

    # ── Salary Structure: create or update ───────────────────────────────────
    if self.salary_structure:
        try:
            salary_structure = frappe.get_doc("havano_salary_structure", self.salary_structure)
        except frappe.DoesNotExistError:
            salary_structure = frappe.new_doc("havano_salary_structure")
            salary_structure.name = f"HSS-{self.name}-{now_datetime().strftime('%Y%m%d%H%M%S')}"
    else:
        salary_structure = frappe.new_doc("havano_salary_structure")
        salary_structure.name = f"HSS-{self.name}-{now_datetime().strftime('%Y%m%d%H%M%S')}"

    salary_structure.company = self.company
    salary_structure.payroll_frequency = getattr(self, "payroll_frequency", "Monthly")
    salary_structure.earnings = []
    salary_structure.deductions = []

    # ── Earnings ─────────────────────────────────────────────────────────────
    total_usd = 0.0
    total_zwg = 0.0
    basic_salary_usd = 0.0
    basic_salary_zwg = 0.0
    nassa_tracking_usd = 0.0
    nassa_tracking_zwg = 0.0

    # ── Overtime Logic ───────────────────────────────────────────────────────
    if self.overtime in ["Time & Half", "Double Time"]:
        # remove existing overtime rows
        for e in self.employee_earnings:
            if e.components in ["Overtime Short", "Overtime Double"]:
                self.remove(e)
        
        # Calculate hourly rate from current basic salary
        basic_now_usd = 0
        basic_now_zwg = 0
        for e in self.employee_earnings:
            if e.components == "Basic Salary":
                basic_now_usd += flt(e.amount_usd)
                basic_now_zwg += flt(e.amount_zwg)
        
        # Combined hourly rate (convert ZWG to USD for simpler math, then split back if needed)
        combined_basic_usd = basic_now_usd + (basic_now_zwg / exchange_rate)
        hourly_rate_usd = flt(combined_basic_usd / 26 / 7.5)
        
        multiplier = 1.5 if self.overtime == "Time & Half" else 2.0
        overtime_amount_usd = flt(hourly_rate_usd * self.hours * multiplier)
        
        comp_name = "Overtime Short" if self.overtime == "Time & Half" else "Overtime Double"
        new_row = self.append("employee_earnings", {})
        new_row.components = comp_name
        new_row.amount_usd = overtime_amount_usd
        new_row.amount_zwg = 0
        new_row.is_tax_applicable = True
        
        overtime_doc = frappe.get_doc({
            "doctype": "Havano Employee Overtime",
            "employee": self.name,
            "overtime_type": self.overtime,
            "amount": overtime_amount_usd
        })
        overtime_doc.insert()
        frappe.db.commit()
        
        self.overtime = ""
        self.hours = 0

    for e in self.employee_earnings:
        usd = flt(e.amount_usd)
        zwg = flt(e.amount_zwg)

        if e.components == "Basic Salary":
            comp_master = frappe.get_doc("havano_salary_component", e.components)
            if comp_master.component_mode == "daily rate":
                usd = (usd / 26) * self.total_days_worked
                zwg = (zwg / 26) * self.total_days_worked
            
            basic_salary_usd = usd
            basic_salary_zwg = zwg
            self.basic_salary_calculated = usd + (zwg / exchange_rate)

        # Long Service Allowance
        elif e.components.upper() == "LONG SERVICE ALLOWANCE":
            usd = basic_salary_usd * 0.01
            zwg = basic_salary_zwg * 0.01
            e.amount_usd = usd
            e.amount_zwg = zwg

        total_usd += usd
        total_zwg += zwg

        try:
            ecomp = frappe.get_doc("havano_salary_component", e.components)
            if ecomp.track_nassa:
                nassa_tracking_usd += usd
                nassa_tracking_zwg += zwg
        except Exception:
            pass

        salary_structure.append("earnings", {
            "components": e.components,
            "amount_zwg": e.amount_zwg,
            "amount_usd": e.amount_usd,
            "is_tax_applicable": bool(e.is_tax_applicable),
            "amount_currency": "BOTH-NO RELATION",
        })

    self.total_income_usd = total_usd
    self.total_income_zwg = total_zwg
    self.total_income = total_usd + total_zwg
    self.total_earnings_usd = total_usd
    self.total_earnings_zwg = total_zwg

    # ── Ensure PAYEE / Aids Levy rows exist ──────────────────────────────────
    _ensure_deductions(self)

    # ── Deductions ───────────────────────────────────────────────────────────
    total_deduction_usd = 0.0
    total_deduction_zwg = 0.0
    total_allowable_usd = 0.0
    total_allowable_zwg = 0.0

    for d in self.employee_deductions:
        try:
            component_doc = frappe.get_doc("havano_salary_component", d.components)
        except frappe.DoesNotExistError:
            frappe.log_error(f"Salary component not found: {d.components}", "Payroll Config Error")
            continue

        comp_upper = d.components.strip().upper()

        if comp_upper == "NSSA":
            if flt(nassa_tracking_usd) >= flt(component_doc.usd_ceiling):
                nssa_usd = flt(component_doc.usd_ceiling_amount)
            else:
                nssa_usd = flt(nassa_tracking_usd) * flt(component_doc.percentage or 4.5) / 100

            if flt(nassa_tracking_zwg) >= flt(component_doc.zwg_ceiling):
                nssa_zwg = flt(component_doc.zwg_ceiling_amount)
            else:
                nssa_zwg = flt(nassa_tracking_zwg) * 0.045

            d.amount_usd = nssa_usd
            d.amount_zwg = nssa_zwg
            total_deduction_usd += nssa_usd
            total_deduction_zwg += nssa_zwg

        elif comp_upper == "PAYEE":
            d.amount_usd = 0
            d.amount_zwg = 0

        elif comp_upper == "AIDS LEVY":
            d.amount_usd = 0
            d.amount_zwg = 0

        elif comp_upper in ["MEDICAL AID", "CIMAS"]:
            emp_cimas_usd = flt(d.amount_usd) * flt(self.cimas_employee_) / 100
            emp_cimas_zwg = flt(d.amount_zwg) * flt(self.cimas_employee_) / 100

            tax_credits_usd += emp_cimas_usd * 0.5
            tax_credits_zwg += emp_cimas_zwg * 0.5
            self.medical_aid_tax_credit = (emp_cimas_usd * 0.5) + (emp_cimas_zwg * 0.5)

            total_deduction_usd += emp_cimas_usd
            total_deduction_zwg += emp_cimas_zwg

        elif comp_upper == "NEC":
            self.nec_usd = basic_salary_usd * 0.015
            self.nec_zwg = basic_salary_zwg * 0.015
            d.amount_usd = self.nec_usd
            d.amount_zwg = self.nec_zwg
            total_deduction_usd += flt(self.nec_usd)
            total_deduction_zwg += flt(self.nec_zwg)

        else:
            total_deduction_usd += flt(d.amount_usd)
            total_deduction_zwg += flt(d.amount_zwg)

        if component_doc.is_tax_applicable:
            total_allowable_usd += flt(d.amount_usd)
            total_allowable_zwg += flt(d.amount_zwg)

        salary_structure.append("deductions", {
            "components": d.components,
            "amount_zwg": d.amount_zwg,
            "amount_usd": d.amount_usd,
            "is_tax_applicable": bool(d.is_tax_applicable),
            "amount_currency": "ZWG" if d.amount_zwg else "USD",
        })

    self.total_allowable_deductions_usd = total_allowable_usd
    self.total_allowable_deductions_zwg = total_allowable_zwg

    taxable_usd = total_usd - total_allowable_usd
    taxable_zwg = total_zwg - total_allowable_zwg

    self.total_taxable_income_usd = taxable_usd
    self.total_taxable_income_zwg = taxable_zwg

    payee_usd = round(
        max(
            payee_against_slab_usd(taxable_usd, getattr(self, "payroll_frequency", "Monthly"))
            - tax_credits_usd,
            0,
        ),
        2,
    )
    payee_zwg = round(
        max(
            payee_against_slab_zwg(taxable_zwg, getattr(self, "payroll_frequency", "Monthly"))
            - tax_credits_zwg,
            0,
        ),
        2,
    )

    aids_levy_usd = round(payee_usd * 0.03, 2)
    aids_levy_zwg = round(payee_zwg * 0.03, 2)

    sdl_usd = round(total_usd * 0.05, 2)
    sdl_zwg = round(total_zwg * 0.05, 2)

    frappe.msgprint(
        f"<b>Payroll Calc (Split):</b><br>"
        f"Gross USD: {total_usd} | Gross ZWG: {total_zwg}<br>"
        f"Allowable Ded USD: {total_allowable_usd} | ZWG: {total_allowable_zwg}<br>"
        f"Taxable USD: {taxable_usd} | ZWG: {taxable_zwg}<br>"
        f"Tax Credits USD: {tax_credits_usd} | ZWG: {tax_credits_zwg}<br>"
        f"PAYEE USD: {payee_usd} | ZWG: {payee_zwg}<br>"
        f"AIDS Levy USD: {aids_levy_usd} | ZWG: {aids_levy_zwg}<br>"
        f"SDL USD: {sdl_usd} | ZWG: {sdl_zwg}"
    )

    self.payee_usd = payee_usd
    self.payee_zwg = payee_zwg
    self.aids_levy_usd = aids_levy_usd
    self.aids_levy_zwg = aids_levy_zwg
    self.payee = payee_usd + payee_zwg
    self.aids_levy = aids_levy_usd + aids_levy_zwg
    self.sdl = sdl_usd + sdl_zwg
    self.total_tax_credits_usd = tax_credits_usd
    self.total_tax_credits_zwg = tax_credits_zwg
    self.total_tax_credits = tax_credits_usd + tax_credits_zwg

    for d in self.employee_deductions:
        comp_upper = d.components.strip().upper()
        if comp_upper == "PAYEE":
            d.amount_usd = payee_usd
            d.amount_zwg = payee_zwg
        elif comp_upper == "AIDS LEVY":
            d.amount_usd = aids_levy_usd
            d.amount_zwg = aids_levy_zwg
        elif comp_upper == "SDL":
            d.amount_usd = sdl_usd
            d.amount_zwg = sdl_zwg

    total_deduction_usd += payee_usd + aids_levy_usd
    total_deduction_zwg += payee_zwg + aids_levy_zwg

    self.total_deduction_usd = total_deduction_usd
    self.total_deduction_zwg = total_deduction_zwg
    self.total_net_income_usd = total_usd - total_deduction_usd
    self.total_net_income_zwg = total_zwg - total_deduction_zwg
    self.net_income = self.total_net_income_usd + self.total_net_income_zwg
    self.total_deductions = total_deduction_usd + total_deduction_zwg

    self.wcif_usd = taxable_usd * flt(self.wcif_percentage) / 100
    self.wcif_zwg = taxable_zwg * flt(self.wcif_percentage) / 100

    salary_structure.save()
    self.salary_structure = salary_structure.name


def payee_against_slab_usd(amount, mode="Monthly"):
    payee = 0.0
    try:
        slab_doc = frappe.get_doc("Havano Tax Slab", "USD")
        for slab in slab_doc.tax_brackets:
            if flt(slab.lower_limit) <= amount <= flt(slab.upper_limit):
                payee = (amount * (flt(slab.percent) / 100)) - flt(slab.fixed_amount)
                break
    except Exception as e:
        frappe.log_error(f"PAYE Slab Error [USD]: {e}", "PAYE Calculation")
    return max(flt(payee), 0.0)


def payee_against_slab_zwg(amount, mode="Monthly"):
    payee = 0.0
    try:
        slab_doc = frappe.get_doc("Havano Tax Slab", "ZWG")
        for slab in slab_doc.tax_brackets:
            if flt(slab.lower_limit) <= amount <= flt(slab.upper_limit):
                payee = (amount * (flt(slab.percent) / 100)) - flt(slab.fixed_amount)
                break
    except Exception as e:
        frappe.log_error(f"PAYE Slab Error [ZWG]: {e}", "PAYE Calculation")
    return max(flt(payee), 0.0)


def _ensure_deductions(self):
    existing = {(r.components or "").strip().upper() for r in self.employee_deductions}
    for component in ["PAYEE", "AIDS LEVY", "SDL"]:
        if component not in existing:
            row = self.append("employee_deductions", {})
            row.components = component
            row.havano_salary_component = component
            row.item_code = component
            row.amount_usd = 0
            row.amount_zwg = 0
            row.exchange_rate = 1
