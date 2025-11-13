import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import nowdate
from frappe.utils import flt


def main(self):
    default_currency = frappe.db.get_value("Company", self.company, "default_currency")
    self.salary_currency=default_currency

    # Initialize---------------tax credits
    tax_credits_usd = 0
    tax_credits_zwg = 0
   
    # frappe.msgprint(str(exchange_rate))
    self.tax_credits=[]

    # Elderly
    if getattr(self, "is_elderly", 0):
        tax_credits_usd += 75

    # Blind
    if getattr(self, "is_blind", 0):
        tax_credits_usd += 75
      

    # Disabled
    if getattr(self, "is_disabled", 0):
        tax_credits += 75

    # --- Create or Update havano_salary_structure ---
    if self.salary_structure:
        # Try to load existing
        try:
            salary_structure = frappe.get_doc("havano_salary_structure", self.salary_structure)
            print(f"Updating existing havano_salary_structure: {self.salary_structure}")
        except frappe.DoesNotExistError:
            salary_structure = frappe.new_doc("havano_salary_structure")
            # Assign a name since it may be Prompt autoname
            salary_structure.name = f"HSS-{self.name}-{now_datetime().strftime('%Y%m%d%H%M%S')}"
    else:
        # Create new
        salary_structure = frappe.new_doc("havano_salary_structure")
        salary_structure.name = f"HSS-{self.name}-{now_datetime().strftime('%Y%m%d%H%M%S')}"

    # --- Fill in fields ---
    salary_structure.company = self.company
    salary_structure.payroll_frequency = getattr(self, 'payroll_frequency', "Monthly")

    # Clear existing child tables
    salary_structure.earnings = []
    salary_structure.deductions = []

    # Populate earnings
# ---------------- Populate Earnings ----------------
    total_amount_basic_and_bonus_and_allowances_usd=0
    total_amount_basic_and_bonus_and_allowances_zwg=0
    total_ensuarable_earnings_usd= 0
    total_ensuarable_earnings_zwg= 0
    basic_salary_usd= 0
    basic_salary_zwg= 0

    for e in self.employee_earnings:
        # Capture Basic Salary
        if e.components == "Basic Salary":
            basic_salary_zwg += flt(e.amount_zwg) 
            basic_salary_usd += flt(e.amount_usd)

        salary_structure.append("earnings", {
            "components": e.components,
            "amount_zwg": e.amount_zwg,
            "amount_usd": e.amount_usd,
            "is_tax_applicable": bool(e.is_tax_applicable),
            "amount_currency": "BOTH-NO RELATION"
        })
        total_amount_basic_and_bonus_and_allowances_zwg += flt(e.amount_zwg)
        total_amount_basic_and_bonus_and_allowances_usd += flt(e.amount_usd)
      
        if bool(e.is_tax_applicable):
            total_ensuarable_earnings_zwg += flt(e.amount_zwg)
            total_ensuarable_earnings_usd += flt(e.amount_usd)

    # frappe.msgprint(str(total_amount_basic_and_bonus_and_allowances))
    self.total_income_usd=total_amount_basic_and_bonus_and_allowances_usd
    self.total_income_zwg=total_amount_basic_and_bonus_and_allowances_zwg
    self.total_ensuarable_earnings_usd=total_ensuarable_earnings_usd
    self.total_ensuarable_earnings_zwg=total_ensuarable_earnings_zwg
    self.total_deduction_usd=0
    self.total_deduction_zwg=0
    medical_usd=0
    medical_zwg=0

    # ---------------- Populate Deductions ----------------
    total_allowable_deductions_usd= 0
    total_allowable_deductions_zwg= 0

    for d in self.employee_deductions:
        # Get the related component document
        component_doc = frappe.get_doc("havano_salary_component", d.components)
        nassa_component = frappe.get_doc("havano_salary_component", "NSSA")
        # If NSSA, calculate 4.5% of Basic Salary
        if d.components == "NSSA":
            if flt(self.total_ensuarable_earnings_usd) >= nassa_component.usd_ceiling:
                nassa_usd= nassa_component.usd_ceiling_amount
            else:
                nassa_usd=flt(self.total_ensuarable_earnings_usd) * 0.045
            if flt(self.total_ensuarable_earnings_zwg) >= nassa_component.zwg_ceiling:
                nassa_zwg=  nassa_component.zwg_ceiling_amount
            else:
                nassa_zwg=flt(self.total_ensuarable_earnings_zwg) * 0.045

            d.amount_usd = nassa_usd
            d.amount_zwg = nassa_zwg

            total_allowable_deductions_usd += flt(nassa_usd)
            total_allowable_deductions_zwg += flt(nassa_zwg)

            self.total_deduction_usd += flt(nassa_usd)
            self.total_deduction_zwg += flt(nassa_zwg)
            
            # frappe.msgprint(f"{total_deduction}")

        # If Medical Aid, apply employer percentage
        elif component_doc.component_mode == "Medical Aid":
            #frappe.msgprint("✅ Medical Aid Deduction Found")
            print(f"Employer Percentage: {flt(component_doc.employer_amount)}")
     
            medical_zwg += flt(d.amount_zwg)
            medical_usd += flt(d.amount_usd)


            #----------------------------------------------------------------------------
            
            tax_credits_usd += (medical_usd * (flt(component_doc.employer_amount) / 100))
            tax_credits_zwg += (medical_zwg * (flt(component_doc.employer_amount) / 100))
            self.total_deduction_usd += flt(medical_usd)
            self.total_deduction_zwg += flt(medical_zwg)
            #----------------------------------------------------------------------------
            # self.append("tax_credits", {
            #     "credit_name": d.components,
            #     "amount_usd": usd_medical,
            #     "amount_zwg": zwg_medical
            # })
            self.total_tax_credits_usd = tax_credits_usd
            self.total_tax_credits_zwg = tax_credits_zwg
            # total_allowable_deductions += flt(medical)


        salary_structure.append("deductions", {
            "components": d.components,
            "amount_zwg": d.amount_zwg,
            "amount_usd": d.amount_usd,
            "is_tax_applicable": bool(d.is_tax_applicable),
            "amount_currency": "ZWG" if d.amount_zwg else "USD"
        })


    self.total_allowable_deductions_usd=total_allowable_deductions_usd
    print(f"total_allowable_deductions_usd {total_allowable_deductions_usd}")
    self.total_allowable_deductions_zwg=total_allowable_deductions_zwg
    self.total_earnings_usd=total_amount_basic_and_bonus_and_allowances_usd
    self.total_earnings_zwg=total_amount_basic_and_bonus_and_allowances_zwg
    self.total_taxable_income_usd=self.total_ensuarable_earnings_usd-self.total_allowable_deductions_usd
    self.total_taxable_income_zwg=self.total_ensuarable_earnings_zwg-self.total_allowable_deductions_zwg
    payee_usd=max(payee_against_slab_usd(self.total_taxable_income_usd)-tax_credits_usd,0)
    payee_zwg=max(payee_against_slab_zwg(self.total_taxable_income_zwg)-tax_credits_zwg,0)
    self.total_deduction_usd += payee_usd
    self.total_deduction_zwg += payee_zwg
    aids_levy_usd=0.03 * payee_usd
    aids_levy_zwg=0.03 * payee_zwg
    self.total_deduction_usd += aids_levy_usd
    self.total_deduction_zwg += aids_levy_zwg

    self.payee_usd=payee_usd
    self.payee_zwg=payee_zwg
    self.aids_levy_usd=aids_levy_usd
    self.aids_levy_zwg=aids_levy_zwg
    self.total_net_income_usd= self.total_earnings_usd - self.total_deduction_usd
    self.total_net_income_zwg= self.total_earnings_zwg - self.total_deduction_zwg

    # Save it_
    salary_structure.save()
    print(f"havano_salary_structure saved: {salary_structure.name}")
    # Link back to employee
    self.salary_structure = salary_structure.name

    

#------------------------------------------------------------------splt currecy--------------------------------------------------------------------------------------







#------------------------------------------------------------------splt currecy--------------------------------------------------------------------------------------

def payee_against_slab_usd(amount):
    """
    Calculate PAYE based on given slabs.
    :param amount: Taxable income (float)
    :return: PAYE amount (float)
    """
    from frappe.utils import flt
    payee = 0.0
    slabs = [
        (0.00, 100.00, 0.0, 0.00),
        (100.01, 300.00, 0.20, 20.00),
        (300.01, 1000.00, 0.25, 35.00),
        (1000.01, 2000.00, 0.30, 85.00),
        (2000.01, 3000.00, 0.35, 185.00),
        (3000.01, 1000000.00, 0.40, 335.00),
    ]

    for lower, upper, percent, fixed in slabs:
        if lower <= amount <= upper:
            payee = ( amount * percent) - fixed
            print(f"{amount} -----wwwwwwwwwwwwwwwww-----percent {percent} --fixed {fixed}-----------payee {payee}")
            break

    return flt(payee)



def payee_against_slab_zwg(amount):
    """
    Calculate PAYE based on given slabs.
    :param amount: Taxable income (float)
    :return: PAYE amount (float)
    """
    from frappe.utils import flt
    payee = 0.0
    slabs = [
        (0.00, 2800.00, 0.0, 0.00),
        (2800.01, 8400.00, 0.20, 560.00),
        (8400.01, 28000.00, 0.25, 980.00),
        (28000.01, 56000.00, 0.30, 2380.00),
        (56000.01, 84000.00, 0.35, 5180.00),
        (84000.01, 1000000.00, 0.40, 9380.00),
    ]

    for lower, upper, percent, fixed in slabs:
        if lower <= amount <= upper:
            payee = ( amount * percent) - fixed
            print(f"{amount} -----wwwwwwwwwwwwwwwww-----percent {percent} --fixed {fixed}-----------payee {payee}")
            break

    return flt(payee)








