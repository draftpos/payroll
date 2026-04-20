import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt, nowdate


def main(self):
    default_currency = frappe.db.get_value("Company", self.company, "default_currency")
    self.salary_currency = default_currency

    # ── Tax credits ──────────────────────────────────────────────────────────
    tax_credits = 0.0

    exchange_rate = flt(
        frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": "USD", "to_currency": "ZWL"},
            "exchange_rate",
        )
        or 1
    )

    if getattr(self, "is_elderly", 0):
        tax_credits += 75
        self.elderly = 75
    else:
        self.elderly = 0

    if getattr(self, "is_blind", 0):
        tax_credits += 75
        self.blind = 75
    else:
        self.blind = 0

    if getattr(self, "is_disabled", 0):
        tax_credits += 75
        self.disabled = 75
    else:
        self.disabled = 0

    # Read any extra tax credits from the employee's tax_credits child table
    for tc in getattr(self, "tax_credits", []):
        if default_currency == "USD":
            tax_credits += flt(tc.amount_usd)
        else:
            tax_credits += flt(tc.amount_zwg)

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
    total_income = 0.0
    basic_salary = 0.0
    nassa_tracking = 0.0

    # ── Overtime Logic ───────────────────────────────────────────────────────
    if self.overtime in ["Time & Half", "Double Time"]:
        # remove existing overtime rows
        for e in self.employee_earnings:
            if e.components in ["Overtime Short", "Overtime Double"]:
                self.remove(e)
        
        # Calculate basic_now based on currency
        basic_now = 0
        for e in self.employee_earnings:
            if e.components == "Basic Salary":
                if self.salary_currency == "USD":
                    basic_now += flt(e.amount_zwg) / exchange_rate
                    basic_now += flt(e.amount_usd)
                else:
                    basic_now += flt(e.amount_usd) * exchange_rate
                    basic_now += flt(e.amount_zwg)
        
        hourly_rate = flt(basic_now / 26 / 7.5)
        multiplier = 1.5 if self.overtime == "Time & Half" else 2.0
        overtime_amount = flt(hourly_rate * self.hours * multiplier)
        
        comp_name = "Overtime Short" if self.overtime == "Time & Half" else "Overtime Double"
        new_row = self.append("employee_earnings", {})
        new_row.components = comp_name
        new_row.amount_usd = overtime_amount if self.salary_currency == "USD" else 0
        new_row.amount_zwg = overtime_amount if self.salary_currency != "USD" else 0
        new_row.is_tax_applicable = True
        
        overtime_doc = frappe.get_doc({
            "doctype": "Havano Employee Overtime",
            "employee": self.name,
            "overtime_type": self.overtime,
            "amount": overtime_amount
        })
        overtime_doc.insert()
        frappe.db.commit()
        
        self.overtime = ""
        self.hours = 0

    for e in self.employee_earnings:
        if default_currency == "USD":
            amount = flt(e.amount_usd)
        else:
            amount = flt(e.amount_zwg)

        if e.components == "Basic Salary":
            comp_master = frappe.get_doc("havano_salary_component", e.components)
            if comp_master.component_mode == "daily rate":
                amount = (amount / 26) * self.total_days_worked
            
            basic_salary = amount
            self.basic_salary_calculated = basic_salary

        # Long Service Allowance
        elif e.components.upper() == "LONG SERVICE ALLOWANCE":
            amount = self.basic_salary_calculated * 0.01
            if default_currency == "USD":
                e.amount_usd = amount
                e.amount_zwg = 0
            else:
                e.amount_usd = 0
                e.amount_zwg = amount

        total_income += amount

        try:
            ecomp = frappe.get_doc("havano_salary_component", e.components)
            if ecomp.track_nassa:
                nassa_tracking += amount
        except Exception:
            pass

        salary_structure.append("earnings", {
            "components": e.components,
            "amount_zwg": e.amount_zwg,
            "amount_usd": e.amount_usd,
            "is_tax_applicable": bool(e.is_tax_applicable),
            "amount_currency": default_currency,
        })

    self.total_income = total_income
    if default_currency == "USD":
        self.total_income_usd = total_income
        self.total_income_zwg = 0
    else:
        self.total_income_usd = 0
        self.total_income_zwg = total_income

    # ── Ensure PAYEE / Aids Levy rows exist ──────────────────────────────────
    _ensure_deductions(self)

    # ── Deductions ───────────────────────────────────────────────────────────
    total_deduction = 0.0
    total_allowable_deductions = 0.0

    for d in self.employee_deductions:
        try:
            component_doc = frappe.get_doc("havano_salary_component", d.components)
        except frappe.DoesNotExistError:
            frappe.log_error(f"Salary component not found: {d.components}", "Payroll Config Error")
            continue

        comp_upper = d.components.strip().upper()

        if comp_upper == "NSSA":
            if default_currency == "USD":
                if flt(nassa_tracking) >= flt(component_doc.usd_ceiling):
                    nssa = flt(component_doc.usd_ceiling_amount)
                else:
                    nssa = flt(nassa_tracking) * flt(component_doc.percentage or 4.5) / 100
                d.amount_usd = nssa
                d.amount_zwg = 0
            else:
                if flt(nassa_tracking) >= flt(component_doc.zwg_ceiling):
                    nssa = flt(component_doc.zwg_ceiling_amount)
                else:
                    nssa = flt(nassa_tracking) * 0.045
                d.amount_usd = 0
                d.amount_zwg = nssa
            total_deduction += flt(nssa)

        elif comp_upper == "PAYEE":
            d.amount_usd = 0
            d.amount_zwg = 0

        elif comp_upper == "AIDS LEVY":
            d.amount_usd = 0
            d.amount_zwg = 0

        elif comp_upper == "NEC":
            nec_employee = basic_salary * 0.015
            nec_employer = basic_salary * 0.015
            total_deduction += flt(nec_employee)
            self.nec_employee = nec_employee
            self.nec_employer = nec_employer
            if default_currency == "USD":
                d.amount_usd = nec_employee
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = nec_employee

        elif comp_upper in ["CIMAS", "MEDICAL AID"]:
            cimas_employee = flt(d.amount_usd) * flt(self.cimas_employee_) / 100
            cimas_employer = flt(d.amount_usd) * flt(self.cimas_employer_) / 100
            total_deduction += flt(cimas_employee)
            medical_aid_tax_credit = cimas_employee * 0.5
            tax_credits += medical_aid_tax_credit
            self.medical_aid_tax_credit = medical_aid_tax_credit
            self.cimas_employee = cimas_employee
            self.cimas_employer = cimas_employer

        elif comp_upper == "FUNERAL POLICY":
            if d.amount_usd:
                funeral_employee = flt(d.amount_usd) * flt(self.funeral_policy_employee_) / 100
                funeral_employer = flt(d.amount_usd) * flt(self.funeral_policy_employer_) / 100
                total_deduction += flt(funeral_employee)
                self.funeral_employee = funeral_employee
                self.funeral_employer = funeral_employer

        elif comp_upper == "NECWEI":
            necwei = basic_salary * flt(component_doc.employee_amount) / 100
            total_deduction += flt(necwei)
            self.necwei = necwei
            d.amount_usd = necwei
            d.amount_zwg = 0

        elif comp_upper == "ZESCWU":
            zescwu = basic_salary * flt(component_doc.employee_amount) / 100
            total_deduction += flt(zescwu)
            self.zescwu = zescwu
            d.amount_usd = zescwu
            d.amount_zwg = 0

        elif comp_upper == "UFAWUZ":
            ufawuz = 0.03 * basic_salary
            total_deduction += flt(ufawuz)
            d.amount_usd = ufawuz
            d.amount_zwg = 0

        elif comp_upper == "ZIBAWU":
            zibawu = 0.02 * basic_salary
            total_deduction += flt(zibawu)
            d.amount_usd = zibawu
            d.amount_zwg = 0

        elif comp_upper == "LAPF":
            lapf_employee = 0.06 * basic_salary
            lapf_employer = 0.173 * basic_salary
            total_deduction += flt(lapf_employee)
            d.amount_usd = lapf_employee
            d.amount_zwg = 0
            self.lapf_employee = lapf_employee
            self.lapf_employer = lapf_employer

        else:
            if default_currency == "USD":
                total_deduction += flt(d.amount_usd)
            else:
                total_deduction += flt(d.amount_zwg)

        if component_doc.is_tax_applicable:
            if default_currency == "USD":
                total_allowable_deductions += flt(d.amount_usd)
            else:
                total_allowable_deductions += flt(d.amount_zwg)

        salary_structure.append("deductions", {
            "components": d.components,
            "amount_zwg": d.amount_zwg,
            "amount_usd": d.amount_usd,
            "is_tax_applicable": bool(d.is_tax_applicable),
            "amount_currency": "ZWG" if d.amount_zwg else "USD",
        })

    self.allowable_deductions = total_allowable_deductions
    taxable_income = total_income - total_allowable_deductions
    self.ensuarable_earnings = taxable_income

    payee = round(
        max(
            payee_against_slab(taxable_income, self.payroll_frequency, default_currency)
            - tax_credits,
            0,
        ),
        2,
    )
    aids_levy = round(0.03 * payee, 2)
    sdl_amount = round(total_income * 0.05, 2)

    frappe.msgprint(
        f"<b>Payroll Calc (Base):</b><br>"
        f"Gross: {total_income}<br>"
        f"Allowable Deductions: {total_allowable_deductions}<br>"
        f"Taxable Income: {taxable_income}<br>"
        f"Tax Credits: {tax_credits}<br>"
        f"Currency: {default_currency}<br>"
        f"PAYEE: {payee}<br>"
        f"AIDS Levy: {aids_levy}<br>"
        f"SDL: {sdl_amount}"
    )

    total_deduction += payee + aids_levy

    self.payee = payee
    self.aids_levy = aids_levy
    self.sdl = sdl_amount
    self.total_tax_credits = tax_credits

    for d in self.employee_deductions:
        comp_upper = d.components.strip().upper()
        if comp_upper == "PAYEE":
            if default_currency == "USD":
                d.amount_usd = payee
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = payee
        elif comp_upper == "AIDS LEVY":
            if default_currency == "USD":
                d.amount_usd = aids_levy
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = aids_levy
        elif comp_upper == "SDL":
            if default_currency == "USD":
                d.amount_usd = sdl_amount
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = sdl_amount

    self.total_deductions = round(total_deduction, 2)
    self.net_income = total_income - self.total_deductions

    if default_currency == "USD":
        self.total_earnings_usd = total_income
        self.total_earnings_zwg = 0
        self.total_deduction_usd = self.total_deductions
        self.total_deduction_zwg = 0
        self.total_net_income_usd = self.net_income
        self.total_net_income_zwg = 0
    else:
        self.total_earnings_usd = 0
        self.total_earnings_zwg = total_income
        self.total_deduction_usd = 0
        self.total_deduction_zwg = self.total_deductions
        self.total_net_income_usd = 0
        self.total_net_income_zwg = self.net_income

    salary_structure.save()
    self.salary_structure = salary_structure.name


def payee_against_slab(amount, mode="Monthly", currency="USD"):
    if currency == "ZWL":
        currency = "ZWG"

    payee = 0.0
    try:
        slab_doc = frappe.get_doc("Havano Tax Slab", currency)
        for slab in slab_doc.tax_brackets:
            lower = flt(slab.lower_limit)
            upper = flt(slab.upper_limit)
            if lower <= amount <= upper:
                payee = (amount * (flt(slab.percent) / 100)) - flt(slab.fixed_amount)
                break
    except Exception as e:
        frappe.log_error(f"PAYE Slab Error [{currency}]: {e}", "PAYE Calculation")

    return max(payee, 0.0)


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
