import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import flt
from frappe.utils import nowdate



def main(self):
    # frappe.msgprint(self.payslip_type)
    default_currency = frappe.db.get_value("Company", self.company, "default_currency")
    self.salary_currency=default_currency

    # Initialize---------------tax credits
    tax_credits = 0
    exchange_rate = flt(frappe.db.get_value(
        "Currency Exchange", 
        {"from_currency": 'USD', "to_currency":"ZWL"},
        "exchange_rate"
    ) or 1)
    # frappe.msgprint(str(exchange_rate))
    self.tax_credits=[]

    # Elderly
    if getattr(self, "is_elderly", 0):
        if self.salary_currency == "USD":
            tax_credits += 75
        else:
            tax_credits += 75 * exchange_rate
        # self.append("tax_credits", {
        #     "credit_name": "Elderly",
        #     "amount_usd": 75,
        #     "amount_zwg": 75 * exchange_rate
        # })

    # Blind
    if getattr(self, "is_blind", 0):
        if self.salary_currency == "USD":
            tax_credits += 75
        else:
            tax_credits += 75 * exchange_rate
        # self.append("tax_credits", {
        #     "credit_name": "Blind",
        #     "amount_usd": 75,
        #     "amount_zwg": 75 * exchange_rate
        # })

    # Disabled
    if getattr(self, "is_disabled", 0):
        if self.salary_currency == "USD":
            tax_credits += 75
        else:
            tax_credits += 75 * exchange_rate
        # self.append("tax_credits", {
        #     "credit_name": "Disabled",
        #     "amount_usd": 75,
        #     "amount_zwg": 75 * exchange_rate
        # })

    # Set total


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
    total_amount_basic_and_bonus_and_allowances=0
    ensurable_earnings= 0
    basic_salary= 0
    overtime=self.overtime

    # Remove any existing "Basic Salary" rows first
    if self.overtime == "Short Time":
        print("overt time-----------------")
        # remove existing "Overtime Short" rows properly
        for e in self.employee_earnings:
            if e.components == "Overtime Short":
                self.remove(e)
             # remove existing "Overtime Short" rows properly
        basic_now=0
        for e in self.employee_earnings:
            if e.components == "Basic Salary":
           
                if self.salary_currency == "USD":
                    basic_now += flt(e.amount_zwg) / exchange_rate
                    basic_now += flt(e.amount_usd)
                else: 
                    basic_now += flt(e.amount_usd) * exchange_rate
                    basic_now += flt(e.amount_zwg)
        

        hourly_rate = flt(basic_now / 26 / 7.5, 2)
        overtime_amount = flt(hourly_rate * self.hours * (2 if self.overtime == "Double Time" else 1 if self.overtime == "Short Time" else 0))
        print(f"-----------------overrr-------{basic_now}")
        self.overtime_amount = overtime_amount
        # total_amount_basic_and_bonus_and_allowances += overtime_amount
        # append new row
        new_row = self.append("employee_earnings", {})
        new_row.components = "Overtime Short"
        new_row.amount_zwg = 0
        new_row.amount_usd = overtime_amount
        new_row.is_tax_applicable = True
        # Create a new Havano Employee Overtime document
        overtime_doc = frappe.get_doc({
            "doctype": "Havano Employee Overtime",
            "employee": self.name,
            "overtime_type": self.overtime,
            "amount": overtime_amount
        })

        overtime_doc.insert()
        frappe.db.commit()
        self.overtime=""
        self.hours=0
            



    elif self.overtime == "Double Time":
        print("overt time-----------------")
        # remove existing "Overtime Short" rows properly
        for e in self.employee_earnings:
            if e.components == "Overtime Double":
                self.remove(e)
             # remove existing "Overtime Short" rows properly
        basic_now=0
        for e in self.employee_earnings:
            if e.components == "Basic Salary":
           
                if self.salary_currency == "USD":
                    basic_now += flt(e.amount_zwg) / exchange_rate
                    basic_now += flt(e.amount_usd)
                else: 
                    basic_now += flt(e.amount_usd) * exchange_rate
                    basic_now += flt(e.amount_zwg)
        

        hourly_rate = flt(basic_now / 26 / 7.5, 2)
        overtime_amount = flt(hourly_rate * self.hours * (2 if self.overtime == "Double Time" else 1 if self.overtime == "Short Time" else 0))
        self.overtime_amount = overtime_amount
        # total_amount_basic_and_bonus_and_allowances += overtime_amount
        # append new row
        new_row = self.append("employee_earnings", {})
        new_row.components = "Overtime Double"
        new_row.amount_zwg = 0
        new_row.amount_usd = overtime_amount
        new_row.is_tax_applicable = True
        # Create a new Havano Employee Overtime document
        overtime_doc = frappe.get_doc({
            "doctype": "Havano Employee Overtime",
            "employee": self.name,
            "overtime_type": self.overtime,
            "amount": overtime_amount
        })

        overtime_doc.insert()
        frappe.db.commit()
            

    for e in self.employee_earnings:
        print(e.components)
        # Capture Basic Salary
        if e.components == "Basic Salary":
            if self.salary_currency == "USD":
                basic_salary += flt(e.amount_zwg) / exchange_rate
                basic_salary += flt(e.amount_usd)
            else: 
                basic_salary += flt(e.amount_usd) * exchange_rate
                basic_salary += flt(e.amount_zwg)
        # -----------------------------------------------------START BACKPAY-----------------------------------------------------
        elif e.components == "Backpay":
            print("----------------------------------back pay")
            backpay=0
            if self.salary_currency == "USD":
                backpay += flt(e.amount_zwg) / exchange_rate
                backpay += e.amount_usd
            else:
                backpay += flt(e.amount_zwg)
                backpay += flt(e.amount_usd) * exchange_rate

            # if self.backpay < backpay:
            #     frappe.throw(f"Back pay should not exceed amount owed in component: {self.backpay}")    
            
            # tax_credits += (medical * (flt(component_doc.employee_amount) / 100))
            # self.medical=medical
            # total_deduction += flt(medical)
            # self.total_tax_credits = tax_credits

# -----------------------------------------------------END BACKPAY-----------------------------------------------------



        salary_structure.append("earnings", {
            "components": e.components,
            "amount_zwg": e.amount_zwg,
            "amount_usd": e.amount_usd,
            "is_tax_applicable": bool(e.is_tax_applicable),
            "amount_currency": "ZWG" if e.amount_zwg else "USD"
        })
        if self.salary_currency == "USD":
            total_amount_basic_and_bonus_and_allowances += flt(e.amount_zwg) / exchange_rate
            total_amount_basic_and_bonus_and_allowances += flt(e.amount_usd)
        else: 
            total_amount_basic_and_bonus_and_allowances += flt(e.amount_zwg) 
            total_amount_basic_and_bonus_and_allowances += flt(e.amount_usd) * exchange_rate

        if bool(e.is_tax_applicable):
            if self.salary_currency == "USD":
                ensurable_earnings += flt(e.amount_zwg) / exchange_rate
                ensurable_earnings += flt(e.amount_usd)

            else: 
                ensurable_earnings += flt(e.amount_zwg)
                ensurable_earnings += flt(e.amount_usd) * exchange_rate



    # frappe.msgprint(str(total_amount_basic_and_bonus_and_allowances))
    self.total_income=total_amount_basic_and_bonus_and_allowances
    self.total_taxable_income=ensurable_earnings
    total_deduction=0

    print(f"Total Earnings USD: {total_amount_basic_and_bonus_and_allowances}")
    print(f"Ensurable Earnings USD: {ensurable_earnings}")
    # ---------------- Populate Deductions ----------------
    total_allowable_deductions= 0

    for d in self.employee_deductions:
        # Get the related component document
        component_doc = frappe.get_doc("havano_salary_component", d.components)
        print(f"-----------------------component doc--------------{component_doc}")

        # If NSSA, calculate 4.5% of Basic Salary
        if d.components == "NSSA":
            nassa_component = frappe.get_doc("havano_salary_component", "NSSA")
            nssa=0
            if self.salary_currency == "USD":
                if flt(ensurable_earnings) >= nassa_component.usd_ceiling:
                    nssa= nassa_component.usd_ceiling_amount
                else:
                    nssa=flt(ensurable_earnings) * 0.045
            else:
                if flt(ensurable_earnings) >= nassa_component.zwg_ceiling:
                    nssa=  nassa_component.zwg_ceiling_amount
                else:
                    nssa=flt(ensurable_earnings) * 0.045

            if self.salary_currency == "USD":
                d.amount_usd = nssa
                d.amount_zwg = 0
                total_allowable_deductions
            else: 
                d.amount_usd = 0
                d.amount_zwg = nssa
            total_allowable_deductions += flt(nssa)
            total_deduction += flt(nssa)
        elif component_doc.component_mode == "Medical Aid":
            medical=0
            if self.salary_currency == "USD":
                medical += flt(d.amount_zwg) / exchange_rate
                medical += d.amount_usd
            else:
                medical += flt(d.amount_zwg)
                medical += flt(d.amount_usd) * exchange_rate
            tax_credits += (medical * (flt(component_doc.employee_amount) / 100))
            self.medical=medical
            total_deduction += flt(medical)
            self.total_tax_credits = tax_credits

        # If NEC, apply employer percentage
        elif component_doc.component_mode == "allowable_deduction":
            if d.components.upper() == "NEC":
                print(f"Employer Percentage: {flt(component_doc.employer_amount)}")
                nec_employee= self.total_taxable_income * flt(component_doc.employee_amount) /100
                nec_employer= self.total_taxable_income * flt(component_doc.employer_amount) /100
                total_allowable_deductions += flt(nec_employee)
                total_deduction += flt(nec_employee)
                print(f"total nec---------------------{nec_employee}")
                self.nec_employee=nec_employee
                self.nec_employer=nec_employer
                if self.salary_currency == "USD":
                    d.amount_usd = nec_employee
                    d.amount_zwg = 0
                else: 
                    d.amount_usd = 0
                    d.amount_zwg = self.nec
            #----------------------------------------------------------------------------
            if d.components.upper() == "CIMAS":
                print(f"Employer Percentage: {flt(component_doc.employer_amount)}")
                cimas_employee= d.amount_usd  * flt(component_doc.employee_amount) /100
                cimas_employer= d.amount_usd  * flt(component_doc.employer_amount) /100
                # total_allowable_deductions += flt(cimas_employee)
                total_deduction += flt(cimas_employee)
                tax_credits += cimas_employee
                print(f"total cimas---------------------{cimas_employee}")
                self.cimas_employee=cimas_employee
                self.cimas_employer=cimas_employer
            #----------------------------------------------------------------------------

            if d.components.upper() == "FUNERAL POLICY":
                print(f"Employer Percentage: {flt(component_doc.employer_amount)}")
                funeral_employee= d.amount_usd  * flt(component_doc.employee_amount) /100
                funeral_employer= d.amount_usd  * flt(component_doc.employer_amount) /100
                # total_allowable_deductions += flt(cimas_employee)
                total_deduction += flt(funeral_employee)
                # tax_credits += funeral_employee
                print(f"total funeral---------------------{funeral_employee}")
                self.funeral_employee=funeral_employee
                self.funeral_employer=funeral_employer
            #-----------------------------------------------
        elif d.components.upper() == "UFAWUZ":
            ufawuz=0.03 * basic_salary
            total_deduction += flt(funeral_employee)
            print(f"total ufawuz---------------------{ufawuz}")
            d.amount_usd = ufawuz
            d.amount_zwg = 0

        elif d.components.upper() == "ZIBAWU":
            zibawu=0.02 * basic_salary
            total_deduction += flt(zibawu)
            print(f"total ufawuz---------------------{zibawu}")
            d.amount_usd = zibawu
            d.amount_zwg = 0

        elif d.components.upper() == "LAPF":
            lapf_employee=0.06 * basic_salary
            lapf_employer=0.173 * basic_salary
            total_deduction += flt(lapf_employee)
            print(f"total lapf_employee---------------------{lapf_employee}")
            d.amount_usd = lapf_employee
            d.amount_zwg = 0
            self.lapf_employee=lapf_employee
            self.lapf_employer=lapf_employer
                


            







        else:
            total_deduction += flt(d.amount_usd )





            #----------------------------------------------------------------------------

        salary_structure.append("deductions", {
            "components": d.components,
            "amount_zwg": d.amount_zwg,
            "amount_usd": d.amount_usd,
            "is_tax_applicable": bool(d.is_tax_applicable),
            "amount_currency": "ZWG" if d.amount_zwg else "USD"
        })

    print(f"Total Deductions: {total_allowable_deductions}")
    self.allowable_deductions=total_allowable_deductions
    self.ensuarable_earnings=self.total_taxable_income-self.allowable_deductions
    if default_currency == "USD":
        self.wcif_usd=self.total_taxable_income * self.wcif_percentage/100
        self.wcif_zwg=0
    else:
        self.wcif_zwg=self.total_taxable_income * self.wcif_percentage/100
        self.wcif_usd=0

    print(self.ensuarable_earnings)
    payee = round(max(payee_against_slab(self.ensuarable_earnings) - tax_credits, 0), 2)
    ads_levy = round(0.03 * payee, 2)
    total_deduction += payee
    total_deduction += ads_levy
    self.payee=payee
    self.aids_levy=ads_levy
    self.total_deductions=round(total_deduction,2)
    self.net_income= self.total_income - self.total_deductions
    # Save it
    salary_structure.save()
    print(f"havano_salary_structure saved: {salary_structure.name}")
    # Link back to employee
    self.salary_structure = salary_structure.name

 

def payee_against_slab(amount):
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
            break

    return flt(payee)





