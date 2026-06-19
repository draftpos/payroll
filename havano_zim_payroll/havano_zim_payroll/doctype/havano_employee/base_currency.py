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

    # 2. FIND BASIC SALARY FIRST
    basic_salary = 0.0
    for e in self.employee_earnings:
        if not e.components:
            continue
        amount = flt(e.amount_usd) if default_currency == "USD" else flt(e.amount_zwg)
        if (e.components or "").strip().title().startswith("Basic Salary"):
            basic_salary = amount

    self.basic_salary_calculated = basic_salary

    # 3. APPLY DYNAMIC EARNINGS
    # --- MOTORING BENEFIT ---
    apply_motoring_benefit(self, default_currency, exchange_rate)

    # --- CASH IN LIEU OF LEAVE ---
    apply_cash_in_lieu(self, basic_salary, default_currency)

    # --- OVERTIME ---
    apply_overtime(self, basic_salary, default_currency)

    # --- SHORT TIME ---
    apply_short_time(self, basic_salary, default_currency)

    # 4. CALCULATE TOTAL EARNINGS AND TAXABLE INCOME
    taxable_earnings = 0.0
    for e in self.employee_earnings:
        if not e.components:
            continue
            
        amount = flt(e.amount_usd) if default_currency == "USD" else flt(e.amount_zwg)
        
        # Motoring Benefit Logic
        if e.components.upper() == "MOTORING BENEFIT":
            if getattr(e, "is_tax_applicable", 0):
                taxable_earnings += amount
            continue # Motoring benefit is taxable but does NOT increase gross total_income
            
        total_income += amount
        if getattr(e, "is_tax_applicable", 0):
            taxable_earnings += amount

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
    cimas_full_amount = flt(getattr(self, "cimas_amount", 0.0))
    emp_portion = cimas_full_amount * flt(self.cimas_employee_) / 100.0
    cimas_employee_credit = emp_portion * 0.5
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
            
            try:
                nssa_dynamic = frappe.db.get_single_value("Havano Payroll Settings", "nssa_on_gross_if_other_earnings_exceed_basic") or 0
                if nssa_dynamic:
                    other_earnings = total_income - basic_salary
                    if other_earnings >= basic_salary:
                        nssa_base_income = total_income
            except Exception:
                pass
            
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
            continue

        elif d.components.upper() in ["PAYEE", "AIDS LEVY", "SDL"]:
            # Skip these for now, calculate later
            continue

        elif d.components.upper() in ["LAPF", "UFAWUZ", "ZFBAWU"]:
            comp_data = frappe.db.get_value("havano_salary_component", d.components,
                ["employee_amount", "employer_amount"], as_dict=True) or {}
            emp_pct = flt(comp_data.get("employee_amount") or 0) / 100.0
            emp_amt = round(basic_salary * emp_pct, 2)
            if self.salary_currency == "USD":
                d.amount_usd = emp_amt
                d.amount_zwg = 0
            else:
                d.amount_usd = 0
                d.amount_zwg = emp_amt
            total_deduction += emp_amt
            total_allowable_deductions += emp_amt
            # Store LAPF employer contribution on employee record
            if d.components.upper() == "LAPF":
                emp_pct_val = flt(comp_data.get("employer_amount") or 0) / 100.0
                self.lapf_employee = emp_amt
                self.lapf_employer = round(basic_salary * emp_pct_val, 2)
            continue
        # Find base component to use as template
        base_comp_name = frappe.db.get_value("havano_salary_component", {"salary_component": ["like", "CIMAS"]}, "name")
        if not base_comp_name:
            base_comp_name = frappe.db.get_value("havano_salary_component", {"salary_component": ["like", "MEDICAL AID%"]}, "name")
        
        # Determine the target Medical Aid label
        medical_aid_label = (getattr(self, "medical_aid_display_name", "") or "").strip() or "Medical Aid"

        # Determine the target Funeral Policy label
        funeral_policy_label = "Funeral Policy"

        # Check if this row is the Medical Aid row
        if d.components.upper() in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE", medical_aid_label.upper()]:
            # Use the new cimas_amount field from the main document
            cimas_full_amount = flt(getattr(self, "cimas_amount", 0.0))
            
            # Calculate employee and employer portions
            emp_portion = round(cimas_full_amount * flt(self.cimas_employee_) / 100.0, 2)
            employer_portion = round(cimas_full_amount * flt(self.cimas_employer_) / 100.0, 2)
            
            # Save the calculated amounts to the main document for reference
            self.cimas_employee = emp_portion
            self.cimas_employer = employer_portion
            
            # Logic: If employee pays a percentage, show calculated amount.
            # If employer pays 100% (employee pays 0%), show 0.0 deduction.
            if emp_portion > 0:
                display_amount = emp_portion
                deduction_effect = emp_portion
            else:
                display_amount = 0.0
                deduction_effect = 0.0

            # Update the row so the UI and payslip reflect the correct deduction
            if self.salary_currency == "USD":
                d.amount_usd = display_amount
                d.amount_zwg = 0
            else:
                d.amount_zwg = display_amount
                d.amount_usd = 0
            
            # Create the Salary Component dynamically if it doesn't exist
            if not frappe.db.exists("havano_salary_component", medical_aid_label):
                comp_doc = frappe.new_doc("havano_salary_component")
                comp_doc.salary_component = medical_aid_label
                comp_doc.type = "Deduction"
                comp_doc.always_calculate = 1
                if base_comp_name:
                    base_doc = frappe.get_doc("havano_salary_component", base_comp_name)
                    comp_doc.is_tax_applicable = base_doc.is_tax_applicable
                    comp_doc.track_nassa = getattr(base_doc, "track_nassa", 0)
                comp_doc.code = "" 
                comp_doc.insert(ignore_permissions=True, ignore_mandatory=True)
                
            # Update the component name and item code on the row
            d.components = medical_aid_label
            d.item_code = frappe.db.get_value("havano_salary_component", medical_aid_label, "code") or medical_aid_label
                
            total_deduction += deduction_effect
        elif d.components.upper() in ["FUNERAL POLICY", "FUNERAL", funeral_policy_label.upper()]:
            funeral_full_amount = flt(getattr(self, "funeral_amount", 0.0))
            
            emp_portion = round(funeral_full_amount * flt(self.funeral_policy_employee_) / 100.0, 2)
            employer_portion = round(funeral_full_amount * flt(self.funeral_policy_employer_) / 100.0, 2)
            
            self.funeral_employee = emp_portion
            self.funeral_employer = employer_portion
            
            if emp_portion > 0:
                display_amount = emp_portion
                deduction_effect = emp_portion
            else:
                display_amount = 0.0
                deduction_effect = 0.0

            if self.salary_currency == "USD":
                d.amount_usd = display_amount
                d.amount_zwg = 0
            else:
                d.amount_zwg = display_amount
                d.amount_usd = 0
            
            # Create the Salary Component dynamically if it doesn't exist
            if not frappe.db.exists("havano_salary_component", funeral_policy_label):
                comp_doc = frappe.new_doc("havano_salary_component")
                comp_doc.salary_component = funeral_policy_label
                comp_doc.type = "Deduction"
                comp_doc.always_calculate = 1
                if base_comp_name:
                    base_doc = frappe.get_doc("havano_salary_component", base_comp_name)
                    comp_doc.is_tax_applicable = base_doc.is_tax_applicable
                    comp_doc.track_nassa = getattr(base_doc, "track_nassa", 0)
                comp_doc.code = "" 
                comp_doc.insert(ignore_permissions=True, ignore_mandatory=True)
                
            d.components = funeral_policy_label
            d.item_code = frappe.db.get_value("havano_salary_component", funeral_policy_label, "code") or funeral_policy_label
                
            total_deduction += deduction_effect
        else:
            # Other deductions (NEC, Pension, etc.)
            # Skip PAYEE and AIDS LEVY here because they are added at the very end
            if d.components.upper() in ["PAYEE", "AIDS LEVY", "SDL"]:
                continue
                
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
    
    try:
        from havano_zim_payroll.havano_zim_payroll.doctype.havano_employee.fds_tax import calculate_fds_tax
        if frappe.db.get_single_value("Havano Payroll Settings", "allow_forecast_fds_method"):
            current_month = nowdate().split("-")[1]
            current_year = nowdate().split("-")[0]
            # Override base_payee with FDS calculation
            base_payee = calculate_fds_tax(
                employee_id=self.name,
                first_name=self.first_name,
                last_name=self.last_name,
                current_taxable_income=self.ensuarable_earnings,
                currency=self.salary_currency,
                current_month_num=current_month,
                current_year=current_year
            )
    except Exception as e:
        frappe.log_error(f"FDS Calculation Error for {self.name}: {e}")
    
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
    
    # Auto-detect the medical aid target label
    base_comp_name = frappe.db.get_value("havano_salary_component", {"salary_component": ["like", "CIMAS"]}, "name")
    if not base_comp_name:
        base_comp_name = frappe.db.get_value("havano_salary_component", {"salary_component": ["like", "MEDICAL AID%"]}, "name")
        
    medical_aid_label = (getattr(self, "medical_aid_display_name", "") or "").strip() or "Medical Aid"
    
    funeral_policy_label = "Funeral Policy"
    
    # Check if we already have a medical aid row
    has_medical_aid = any(x in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE", medical_aid_label.upper()] for x in existing)
    
    # Check if we already have a funeral policy row
    has_funeral_policy = any(x in ["FUNERAL POLICY", "FUNERAL", funeral_policy_label.upper()] for x in existing)

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
                    
    # Separately ensure Medical Aid
    if not has_medical_aid:
        always_calc = 0
        if frappe.db.exists("havano_salary_component", medical_aid_label):
            always_calc = frappe.db.get_value("havano_salary_component", medical_aid_label, "always_calculate")
        else:
            always_calc = 1 # We will create it on the fly later, so assume it should be there
            
        if flt(getattr(self, "cimas_amount", 0.0)) > 0:
            always_calc = 1
            
        if always_calc:
            self.append("employee_deductions", {
                "components": medical_aid_label,
                "amount_usd": 0,
                "amount_zwg": 0
            })

    # Separately ensure Funeral Policy
    if not has_funeral_policy:
        always_calc = 0
        if frappe.db.exists("havano_salary_component", funeral_policy_label):
            always_calc = frappe.db.get_value("havano_salary_component", funeral_policy_label, "always_calculate")
        else:
            always_calc = 1 # We will create it on the fly later, so assume it should be there
            
        if flt(getattr(self, "funeral_amount", 0.0)) > 0:
            always_calc = 1
            
        if always_calc:
            self.append("employee_deductions", {
                "components": funeral_policy_label,
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

    # Always remove both overtime rows first
    to_remove = [e for e in self.employee_earnings if (e.components or "") in ("Overtime Double", "Overtime Short")]
    existing_data = {}
    for r in to_remove:
        existing_data[r.components] = {"name": r.name, "is_tax_applicable": getattr(r, "is_tax_applicable", 0)}
        self.employee_earnings.remove(r)

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
    elif ot_type == "Time & Half":
        ot_amount    = round(ot_hours * hourly_rate * 1.5, 2)
        comp_name    = "Overtime Short"
    elif ot_type == 'Time & Half and Double Time':
        half_hours   = flt(getattr(self, 'hours_half', 0) or 0)
        double_hours = flt(getattr(self, 'hours_double', 0) or 0)
        half_amount  = round(half_hours * hourly_rate * 1.5, 2)
        double_amount = round(double_hours * hourly_rate * 2, 2)
        ot_amount    = half_amount + double_amount
        self.half_amount   = half_amount
        self.double_amount = double_amount
        self.overtime_amount = ot_amount

        if half_hours > 0:
            amount_usd = half_amount if default_currency == 'USD' else 0.0
            amount_zwg = half_amount if default_currency != 'USD' else 0.0
            row_data = {
                'components': 'Overtime Short',
                'amount_usd': amount_usd,
                'amount_zwg': amount_zwg,
            }
            if 'Overtime Short' in existing_data:
                row_data['name'] = existing_data['Overtime Short']['name']
                row_data['is_tax_applicable'] = existing_data['Overtime Short']['is_tax_applicable']
            else:
                row_data['is_tax_applicable'] = frappe.db.get_value("havano_salary_component", "Overtime Short", "is_tax_applicable") or 0
            self.append('employee_earnings', row_data)
            
        if double_hours > 0:
            amount_usd = double_amount if default_currency == 'USD' else 0.0
            amount_zwg = double_amount if default_currency != 'USD' else 0.0
            row_data = {
                'components': 'Overtime Double',
                'amount_usd': amount_usd,
                'amount_zwg': amount_zwg,
            }
            if 'Overtime Double' in existing_data:
                row_data['name'] = existing_data['Overtime Double']['name']
                row_data['is_tax_applicable'] = existing_data['Overtime Double']['is_tax_applicable']
            else:
                row_data['is_tax_applicable'] = frappe.db.get_value("havano_salary_component", "Overtime Double", "is_tax_applicable") or 0
            self.append('employee_earnings', row_data)
        return
    else:
        self.overtime_amount = 0.0
        return

    self.overtime_amount = ot_amount

    # Inject into earnings table
    amount_usd = ot_amount if default_currency == "USD" else 0.0
    amount_zwg = ot_amount if default_currency != "USD" else 0.0

    row_data = {
        "components":        comp_name,
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
    }
    if comp_name in existing_data:
        row_data['name'] = existing_data[comp_name]['name']
        row_data['is_tax_applicable'] = existing_data[comp_name]['is_tax_applicable']
    else:
        row_data['is_tax_applicable'] = frappe.db.get_value("havano_salary_component", comp_name, "is_tax_applicable") or 0
    self.append("employee_earnings", row_data)


def apply_cash_in_lieu(self, basic_salary, default_currency):
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

    # Remove existing cash in lieu row
    to_remove = [e for e in self.employee_earnings if (e.components or "").upper() == "CASH IN LIEU OF LEAVE"]
    existing_data = {}
    for r in to_remove:
        existing_data["cash in lieu of leave"] = {"name": r.name, "is_tax_applicable": getattr(r, "is_tax_applicable", 0)}
        self.employee_earnings.remove(r)

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

    amount_usd = amount if default_currency == "USD" else 0.0
    amount_zwg = amount if default_currency != "USD" else 0.0

    row_data = {
        "components":        "cash in lieu of leave",
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
    }
    if "cash in lieu of leave" in existing_data:
        row_data['name'] = existing_data["cash in lieu of leave"]['name']
        row_data['is_tax_applicable'] = existing_data["cash in lieu of leave"]['is_tax_applicable']
    else:
        row_data['is_tax_applicable'] = frappe.db.get_value("havano_salary_component", "cash in lieu of leave", "is_tax_applicable") or 0
        
    self.append("employee_earnings", row_data)


def apply_motoring_benefit(self, default_currency, exchange_rate=1.0):
    """
    Auto-inject Motoring Benefit row into earnings.
    Amount = deemed_value_usd from Havano Motoring Benefit table (by engine_capacity).
    Taxable but does NOT count toward gross total_income (ZIMRA rule).
    """
    import frappe
    from frappe.utils import flt

    # Always remove existing row
    to_remove = [e for e in self.employee_earnings if (e.components or "").upper() == "MOTORING BENEFIT"]
    existing_data = {}
    for r in to_remove:
        existing_data["Motoring Benefit"] = {"name": r.name, "is_tax_applicable": getattr(r, "is_tax_applicable", 0)}
        self.employee_earnings.remove(r)

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

    row_data = {
        "components":        "Motoring Benefit",
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
    }
    if "Motoring Benefit" in existing_data:
        row_data['name'] = existing_data["Motoring Benefit"]['name']
        row_data['is_tax_applicable'] = existing_data["Motoring Benefit"]['is_tax_applicable']
    else:
        row_data['is_tax_applicable'] = frappe.db.get_value("havano_salary_component", "Motoring Benefit", "is_tax_applicable") or 0

    self.append("employee_earnings", row_data)


def apply_short_time(self, basic_salary, default_currency):
    """Short Time: removes row then re-adds with negative amount if has_short_time is checked."""
    from frappe.utils import flt
    to_remove = [e for e in self.employee_earnings if (e.components or "").upper() == "SHORT TIME"]
    existing_data = {}
    for r in to_remove:
        existing_data["Short Time"] = {"name": r.name, "is_tax_applicable": getattr(r, "is_tax_applicable", 0)}
        self.employee_earnings.remove(r)
    if not getattr(self, "has_short_time", 0):
        return
    days_worked = flt(getattr(self, "short_time_days_worked", 0))
    standard_days = 26.0
    if not basic_salary or not (0 < days_worked < standard_days):
        return
    short_days = standard_days - days_worked
    daily_rate = basic_salary / standard_days
    short_amount = round(daily_rate * short_days, 2)
    amount_usd = -short_amount if default_currency == "USD" else 0.0
    amount_zwg = -short_amount if default_currency != "USD" else 0.0
    
    row_data = {
        "components":        "Short Time",
        "amount_usd":        amount_usd,
        "amount_zwg":        amount_zwg,
    }
    if "Short Time" in existing_data:
        row_data['name'] = existing_data["Short Time"]['name']
        row_data['is_tax_applicable'] = existing_data["Short Time"]['is_tax_applicable']
    else:
        row_data['is_tax_applicable'] = frappe.db.get_value("havano_salary_component", "Short Time", "is_tax_applicable") or 0

    self.append("employee_earnings", row_data)
