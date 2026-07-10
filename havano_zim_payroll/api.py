import frappe
from frappe.utils import flt
from frappe.utils import nowdate, flt
from datetime import date
import calendar
from frappe import error_log
frappe.error_log = error_log


@frappe.whitelist()
def run_payroll_async(month, year, work_date=None, daily=None, sync=False, employee=None):
    """
    Enqueue payroll or run synchronously.
    Defaults to sync=True to ensure immediate results if workers aren't active.
    """
    if str(sync).lower() in ["true", "1", "t", "y", "yes"]:
        # Run immediately in the current request
        return run_payroll(month, year, work_date, daily, employee=employee)
    
    job = frappe.enqueue(
        "havano_zim_payroll.api.run_payroll",
        month=month,
        year=year,
        work_date=work_date,
        daily=daily,
        employee=employee,
        queue="long",
        timeout=15000
    )

    return {
        "message": f"Payroll job queued for {month}/{year}",
        "job_id": job.id
    }


def normalize_year_month(year, month):
    # year comes as "2025" → 2025
    year = int(year)

    # month can be "December" or "12"
    if isinstance(month, str):
        if month.isdigit():
            month = int(month)
        else:
            month = list(calendar.month_name).index(month)

    return year, month
def get_month_range(year, month):
    year, month = normalize_year_month(year, month)

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    return start_date, end_date

def get_employee_hours(employee, year, month):
    start_date, end_date = get_month_range(year, month)

    total_hours = frappe.db.sql("""
        SELECT SUM(hours)
        FROM `tabhours worked`
        WHERE employee = %s
        AND date BETWEEN %s AND %s
    """, (employee, start_date, end_date))[0][0]

    return total_hours or 0


def add_basic_hourly(employee_id, amount):
    # fetch employee doc
    emp_doc = frappe.get_doc("havano_employee", employee_id)

    component = "Basic Salary"

    # check existing earnings
    existing = {
        (row.components or ""): row
        for row in emp_doc.employee_earnings
    }
    if component in existing:
        # update amount if it exists
        row = existing[component]
        row.amount_usd = amount
        row.amount_zwg = 0
        row.exchange_rate = 1
    else:
        # append new Basic Salary
        row = emp_doc.append("employee_earnings", {})
        row.components = component
        row.havano_salary_component = component
        row.item_code = component
        row.amount_usd = amount
        row.amount_zwg = 0
        row.exchange_rate = 1

    # save employee doc
    emp_doc.save(ignore_permissions=True)
    return f"Basic Salary updated for {employee_id}"

@frappe.whitelist()
def run_payroll(month, year, work_date=None, daily=0, employee=None):
    settin=get_payroll_settings()
    setting_cost_center=settin["cost_center"]
    setting_supplier=settin["supplier"]
    create_journal_entry = flt(settin.get("create_journal_entry"))
    default_payable_account = settin.get("default_payroll_payable_account")
    
    try:
        settings = frappe.get_single("Havano Payroll Settings")
        if settings:
            mapped_components = {row.component.strip().lower(): row.account for row in settings.get("payroll_journal_accounts", []) if row.account and row.component}
        else:
            mapped_components = {}
    except Exception:
        mapped_components = {}

    pj_data = {}
    ecj_data = {}
    je_data = {}
    
    account_cache = {}
    def get_account(component, company):
        key = (component, company)
        if key in account_cache:
            return account_cache[key]
        acc = frappe.db.get_value("havano_salary_accounts", 
            {"parent": component, "parenttype": "havano_salary_component", "company": company}, 
            "account")
        account_cache[key] = acc
        return acc

    """Runs payroll for all employees immediately (synchronous)."""
    # Cast parameters to ensure correct type
    from frappe.utils import cint
    daily = cint(daily)
    
    if daily:
        employees = frappe.get_all(
            "havano_employee",
            filters={"payroll_frequency": "Daily", "status": "Active"},
            fields=["name", "first_name", "last_name", "net_income", "payroll_frequency"],
            ignore_permissions=True,
            limit_page_length=0
        )
    else:
        # Default: Process all Active employees regardless of frequency (or you can filter for Monthly)
        employees = frappe.get_all(
            "havano_employee",
            filters={"status": "Active"},
            fields=["name", "first_name", "last_name", "net_income", "payroll_frequency"],
            ignore_permissions=True,
            limit_page_length=0
        )

    if employee:
        employees = [e for e in employees if e.name == employee]

    frappe.log_error(title="Payroll Debug", message=f"Found {len(employees)} active employees for payroll run (Daily={daily})")
    if not employees:
        frappe.log_error(title="Payroll Error", message="No employees found for payroll run")
        return "No employees found."
    
    frappe.log_error(title="Payroll Progress", message=f"Starting payroll run for {len(employees)} employees")
    total_net_salary_now=0
    total_sdl=0
    total_loan = 0
    # Normalize year and month at the start
    year, month_int = normalize_year_month(year, month)
    month_name = calendar.month_name[month_int]

    # Default work_date to end of month if not provided
    if not work_date:
        _, end_date = get_month_range(year, month_int)
        work_date = end_date

    # Ensure Havano Payroll Period exists (auto-create if missing)
    start_dt, end_dt = get_month_range(year, month_int)
    company = frappe.defaults.get_user_default("Company")
    if not company:
        company_doc = frappe.get_all("Company", limit=1)
        if company_doc:
            company = company_doc[0].name

    period_name = f"{month_name} {year}"

    # Check if Havano Payroll Period already exists for this period
    existing_period = frappe.db.exists("Havano Payroll Period", period_name)

    if not existing_period:
        try:
            p_doc = frappe.new_doc("Havano Payroll Period")
            p_doc.period_name = period_name
            p_doc.start_date = start_dt
            p_doc.end_date = end_dt
            if company:
                p_doc.company = company
            p_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.log_error(
                message=f"Auto-created Havano Payroll Period: {period_name}",
                title="Payroll Period Created"
            )
        except Exception as e:
            frappe.log_error(
                message=f"Failed to auto-create Havano Payroll Period {period_name}: {e}",
                title="Payroll Period Creation Error"
            )

    # Initialize default account for SDL report/invoice
    basic_comp_accounts = get_basic_salary_component()
    acc = basic_comp_accounts[0] if basic_comp_accounts else None
    
    if not acc:
        frappe.log_error(title="Payroll Configuration Error", message="Basic Salary component accounting is not configured. Cannot create invoices.")

    for emp in employees:
        frappe.logger().info(f"Processing payroll for: {emp.name}")
        emp_doc = frappe.get_doc("havano_employee", emp.name)
        # Deal with Cash in lieu (Leave encashment) for this period
        encashments = frappe.get_all("havano_leave_encashment", filters={"employee": emp.name, "payroll_period": period_name, "docstatus": 1}, fields=["days_being_encashed", "encashment_amount"])
        needs_save = False
        if encashments:
            total_encashment_days = sum([flt(e.days_being_encashed) for e in encashments])
            total_encashment_amount = sum([flt(e.encashment_amount) for e in encashments])
            if flt(emp_doc.get("leave_days_to_sell")) != total_encashment_days or flt(emp_doc.get("cash_in_lieu_amount")) != total_encashment_amount:
                emp_doc.leave_days_to_sell = total_encashment_days
                emp_doc.cash_in_lieu_amount = total_encashment_amount
                needs_save = True
        else:
            if flt(emp_doc.get("leave_days_to_sell")) or flt(emp_doc.get("cash_in_lieu_amount")):
                emp_doc.leave_days_to_sell = 0
                emp_doc.cash_in_lieu_amount = 0
                needs_save = True

        if needs_save:
            emp_doc.save(ignore_permissions=True)

        # 1. Clean existing loan components to prevent duplicates or lingering ones from past months
        emp_doc.employee_earnings = [e for e in getattr(emp_doc, "employee_earnings", []) if e.components != "Loan Amount"]
        emp_doc.employee_deductions = [d for d in getattr(emp_doc, "employee_deductions", []) if d.components != "Loan Repayment"]

        # Dealing with employee loan and deduction
        employee_loan_record = get_employee_loan(emp.name)
        
        loan_amount_earning = 0
        loan_repayment_deduction = 0

        if employee_loan_record:
            from datetime import datetime
            payslip_period_str = period_name
            
            def parse_period(p):
                if not p:
                    return None
                try:
                    return datetime.strptime(p.strip(), "%B %Y")
                except:
                    return None
            
            payslip_dt = parse_period(payslip_period_str)
            
            disbursement_str = getattr(employee_loan_record, "current_payroll_period", "")
            disbursement_dt = parse_period(disbursement_str) if disbursement_str else None
            
            repayment_start_str = getattr(employee_loan_record, "repayment_start_date", "")
            repayment_start_dt = parse_period(repayment_start_str) if repayment_start_str else None

            # Phase 3: Earnings
            if disbursement_dt and payslip_dt:
                if payslip_dt.year == disbursement_dt.year and payslip_dt.month == disbursement_dt.month:
                    loan_amount_earning = getattr(employee_loan_record, "loan_principal_amount", 0)
                    if loan_amount_earning > 0:
                        emp_doc.append("employee_earnings", {
                            "components": "Loan Amount",
                            "amount_usd": loan_amount_earning if employee_loan_record.currency == "USD" else 0,
                            "amount_zwg": loan_amount_earning if employee_loan_record.currency != "USD" else 0
                        })
                
            # Phase 3: Deductions
            current_balance = getattr(employee_loan_record, "current_loan_balance", 0)
            
            is_after_repayment = False
            if repayment_start_dt and payslip_dt:
                is_after_repayment = payslip_dt.year > repayment_start_dt.year or (payslip_dt.year == repayment_start_dt.year and payslip_dt.month >= repayment_start_dt.month)
                
            if is_after_repayment and current_balance > 0:
                monthly_deduct = getattr(employee_loan_record, "monthly_amount_to_be_paid", 0)
                loan_repayment_deduction = min(current_balance, monthly_deduct)
                
                if loan_repayment_deduction > 0:
                    emp_doc.append("employee_deductions", {
                        "components": "Loan Repayment",
                        "amount_usd": loan_repayment_deduction if employee_loan_record.currency == "USD" else 0,
                        "amount_zwg": loan_repayment_deduction if employee_loan_record.currency != "USD" else 0
                    })
                
                    # Update loan fields permanently
                    employee_loan_record.loan_paid = (getattr(employee_loan_record, "loan_paid", 0) or 0) + loan_repayment_deduction
                    employee_loan_record.current_loan_balance = current_balance - loan_repayment_deduction
                    employee_loan_record.flags.ignore_employee_update = True
                    employee_loan_record.save(ignore_permissions=True)
                
                    frappe.log_error(
                        message=f"Employee: {emp.name}, Monthly Loan Deduction: {loan_repayment_deduction}, Loan Paid: {employee_loan_record.loan_paid}, Current Balance: {employee_loan_record.current_loan_balance}",
                        title="Payroll Monthly Loan Update"
                    )

        # Ensure fresh calculations by saving the employee doc
        # This triggers before_save logic which calculates PAYE, Net Income, etc. including the loans we just dynamically added!
        try:
            emp_doc.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Payroll Skip - {emp.name} ({emp.get('first_name','')} {emp.get('last_name','')}) - save error"
            )
            continue

        # Create new Payroll Entry
        payroll = frappe.new_doc("Havano Payroll Entry")
        payroll.first_name = emp_doc.first_name
        payroll.last_name = emp_doc.last_name
        payroll.payroll_period = period_name
        payroll.date = work_date or nowdate()
        payroll.payroll_frequency=emp_doc.payroll_frequency
        nssa_usd=0
        nssa_zwg=0
        try:
            loan_deduction_add_back = get_loan_deduction_amounts(emp.name)
            emp_netpay = emp_doc.net_income
            total_net_salary_now += flt(emp_doc.net_income) + flt(loan_deduction_add_back.get("amount_usd", 0))
            total_loan += flt(loan_deduction_add_back.get("amount_usd", 0))
            total_sdl += flt(emp_doc.total_income) * 0.05
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Payroll Skip - {emp.name} ({emp.get('first_name','')} {emp.get('last_name','')}) - calc error"
            )
            continue

        # === Short Time Deduction (payslip only) ===
        st_data = frappe.db.get_value("havano_employee", emp.name,
            ["has_short_time", "short_time_days_worked", "basic_salary_calculated", "salary_currency"],
            as_dict=True) or {}
        if flt(st_data.get("has_short_time")):
            st_days_worked = flt(st_data.get("short_time_days_worked", 0))
            standard_days = 26.0
            if 0 < st_days_worked < standard_days:
                basic = flt(st_data.get("basic_salary_calculated", 0))
                if basic > 0:
                    daily_rate = basic / standard_days
                    short_days = standard_days - st_days_worked
                    short_amount = round(short_days * daily_rate, 2)
                    is_usd = (st_data.get("salary_currency", "") == "USD")
                    payroll.append("employee_earnings", {
                        "components": "Short Time",
                        "item_code": None,
                        "amount_usd": -short_amount if is_usd else 0.0,
                        "amount_zwg": -short_amount if not is_usd else 0.0,
                    })
                    emp_netpay -= short_amount

        # Copy Earnings
        if hasattr(emp_doc, "employee_earnings"):
            for e in emp_doc.employee_earnings:
                if e.components == "Backpay":
                    emp_netpay -= flt(e.amount_usd)
                payroll.append("employee_earnings", {
                    "components": e.components,
                    "item_code": e.item_code,
                    "amount_usd": e.amount_usd,
                    "amount_zwg": e.amount_zwg
                })

        # Add Loan Earnings (informational)
        if loan_amount_earning > 0:
            is_usd = (emp_doc.salary_currency == "USD")
            payroll.append("employee_earnings", {
                "components": "Loan Amount",
                "item_code": None,
                "amount_usd": loan_amount_earning if is_usd else 0.0,
                "amount_zwg": loan_amount_earning if not is_usd else 0.0,
            })

        # Deduct Loan Repayment from Net Pay
        if loan_repayment_deduction > 0:
            emp_netpay -= loan_repayment_deduction

        # Fetch the ledger for the employee
        ledger = frappe.db.get_value(
            "Employee Ledger",
            {"employee": emp.name},
            ["name", "employee", "current_balance_owing", "balance_added"],
            as_dict=True
        )

        if not ledger:
            # If no ledger exists, create one
            ledger_doc = frappe.get_doc({
                "doctype": "Employee Ledger",
                "employee": emp.name,
                "balance_added": emp_netpay,   # x
                "current_balance_owing": emp_netpay  # starting from 0 + x
            })
            ledger_doc.insert(ignore_permissions=True)
        else:
            # Update existing ledger
            ledger_doc = frappe.get_doc("Employee Ledger", ledger["name"])
            ledger_doc.balance_added = emp_netpay   # x
            ledger_doc.current_balance_owing = (flt(ledger.get("current_balance_owing")) or 0) + flt(emp_netpay)
            ledger_doc.save(ignore_permissions=True)


        # Copy Deductions
        if hasattr(emp_doc, "employee_deductions"):
            for d in emp_doc.employee_deductions:
                if d.components == "NSSA":
                    try:
                        nssa_rep_name = f"NSSA-EMP-{emp.name}-{month_name}-{year}"
                        create_payroll_report(emp_doc.first_name,emp_doc.last_name, d.amount_zwg,0,d.amount_usd,0,period_name,emp_doc.wcif_usd,emp_doc.wcif_zwg, nssa_rep_name)
                    except Exception as e:
                        frappe.log_error(title="Payroll Error", message=f"NSSA Report Error for {emp.name}: {e}")
                    nssa_usd = d.amount_usd
                    nssa_zwg = d.amount_zwg

                if d.components and "NEC" in d.components.upper():
                    try:
                        nec_rep_name = f"NEC-{emp.name}-{month_name}-{year}"
                        start_dt, end_dt = get_month_range(year, month_int)
                        # We assume employer matches employee
                        employer_usd = d.amount_usd or 0
                        employer_zwg = d.amount_zwg or 0
                        total_usd = (d.amount_usd or 0) + employer_usd
                        create_nec_report(
                            surname=emp_doc.last_name,
                            first_name=emp_doc.first_name,
                            start_date=start_dt,
                            end_date=end_dt,
                            grade=getattr(emp_doc, "grade", ""),
                            nec_earnings_usd=emp_doc.total_taxable_income_usd,
                            employer_contribution_usd=employer_usd,
                            employer_contribution_zwg=employer_zwg,
                            total_nec_usd=total_usd,
                            department=emp_doc.department,
                            name=nec_rep_name
                        )
                    except Exception as e:
                        frappe.log_error(title="Payroll Error", message=f"NEC Report Error for {emp.name}: {e}")

                payroll.append("employee_deductions", {
                    "components": d.components,
                    "item_code": d.item_code,
                    "amount_usd": d.amount_usd,
                    "amount_zwg": d.amount_zwg
                })

        try:
            payroll.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Payroll Skip - {emp.name} ({emp.get('first_name','')} {emp.get('last_name','')}) - insert error"
            )
            frappe.db.rollback()
            continue

        # Generate Statutory Reports (ZIMRA, SDL)
        try:
            # Handle all currency modes (Base and Split)
            p4_name = f"NSSA-P4-{emp.name}-{month_name}-{year}"
            p2_name = f"ZIMRA-P2-{emp.name}-{month_name}-{year}"
            itf16_name = f"ZIMRA-ITF16-{emp.name}-{month_name}-{year}"
            sdl_name = f"SDL-{emp.name}-{month_name}-{year}"
            start_dt, end_dt = get_month_range(year, month_int)

            if emp_doc.salary_currency == "USD" or flt(emp_doc.total_income_usd) > 0:
                create_nssa_p4_report_store(surname=emp_doc.last_name, first_name=emp_doc.first_name, national_id=emp_doc.national_id, payroll_period=period_name, start_date=start_dt, end_date=end_dt, total_insuarable_earnings_zwg=0, total_insuarable_earnings_usd=emp_doc.total_taxable_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_taxable_income_usd, current_contributions_usd=nssa_usd, current_contributions_zwg=0, total_payment_usd=nssa_usd, total_payment_zwg=0, department=emp_doc.department, name=p4_name)
                create_zimra_p2form(employer_name="DPT", trade_name="DPT", tax_period=period_name, total_renumeration=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_usd, gross_paye=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_usd, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_usd, total_tax_due=flt(emp_doc.aids_levy or 0) + flt(emp_doc.payee or 0) if emp_doc.payslip_type == "Base Currency" else flt(emp_doc.aids_levy_usd or 0) + flt(emp_doc.payee_usd or 0), currency="USD", name=p2_name)
                create_zimra_itf16(surname=emp_doc.last_name, first_name=emp_doc.first_name, employee_id=emp_doc.name, gross_paye=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_usd, payee=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_usd, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_usd, currency="USD", dob=emp_doc.date_of_birth, start_date=emp_doc.final_confirmation_date, end_date=emp_doc.contract_end_date, department=emp_doc.department, name=itf16_name)
                add_sdl_report(employee=emp_doc.name, date=period_name, amount=flt(emp_doc.total_income) * 0.05, department=emp_doc.department, name=sdl_name)
            
            elif emp_doc.salary_currency in ["ZWL", "ZWG"] or flt(emp_doc.total_income_zwg) > 0:
                create_nssa_p4_report_store(surname=emp_doc.last_name, first_name=emp_doc.first_name, national_id=emp_doc.national_id, payroll_period=period_name, start_date=start_dt, end_date=end_dt, total_insuarable_earnings_zwg=emp_doc.total_taxable_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_taxable_income_zwg, total_insuarable_earnings_usd=0, current_contributions_usd=0, current_contributions_zwg=nssa_zwg, total_payment_usd=0, total_payment_zwg=nssa_zwg, department=emp_doc.department, name=p4_name)
                create_zimra_p2form(employer_name="DPT", trade_name="DPT", tax_period=period_name, total_renumeration=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_zwg, gross_paye=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_zwg, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_zwg, total_tax_due=flt(emp_doc.aids_levy or 0) + flt(emp_doc.payee or 0) if emp_doc.payslip_type == "Base Currency" else flt(emp_doc.aids_levy_zwg or 0) + flt(emp_doc.payee_zwg or 0), currency="ZWG", name=p2_name)
                create_zimra_itf16(surname=emp_doc.last_name, first_name=emp_doc.first_name, employee_id=emp_doc.name, gross_paye=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_zwg, payee=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_zwg, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_zwg, currency="ZWG", dob=emp_doc.date_of_birth, start_date=emp_doc.final_confirmation_date, end_date=emp_doc.contract_end_date, department=emp_doc.department, name=itf16_name)
                add_sdl_report(employee=emp_doc.name, date=period_name, amount=flt(emp_doc.total_income) * 0.05, department=emp_doc.department, name=sdl_name)
        except Exception as e:
            frappe.log_error(title="Payroll Error", message=f"Statutory Report Error for {emp.name}: {e}")

        # Auto-Create Custom Report Stores (Funeral, Medical Aid, Leave, Overtime)
        try:
            payroll_period_str = period_name
            
            # Calculate Amounts from Earnings/Deductions
            funeral_amt = 0
            medical_emp = 0
            overtime_amt = 0
            
            if hasattr(emp_doc, "employee_deductions"):
                for d in emp_doc.employee_deductions:
                    if d.components and "FUNERAL" in d.components.upper():
                        funeral_amt += flt(d.amount_usd) + flt(d.amount_zwg)
                    if d.components and ("CIMAS" in d.components.upper() or "MEDICAL" in d.components.upper()):
                        medical_emp += flt(d.amount_usd) + flt(d.amount_zwg)
                        
            if hasattr(emp_doc, "employee_earnings"):
                for e in emp_doc.employee_earnings:
                    if e.components and "OVERTIME" in e.components.upper():
                        overtime_amt += flt(e.amount_usd) + flt(e.amount_zwg)
                        
            medical_employer = flt(getattr(emp_doc, "cimas_employer_", 0))

            # 1. Funeral Report Store
            frappe.get_doc({
                "doctype": "Funeral Report Store",
                "employee": emp.name,
                "department": emp_doc.department,
                "payroll_period": payroll_period_str,
                "amount": funeral_amt
            }).insert(ignore_permissions=True)
            
            # 2. Medical Aid Report Store
            frappe.get_doc({
                "doctype": "Medical Aid Report Store",
                "employee": emp.name,
                "department": emp_doc.department,
                "payroll_period": payroll_period_str,
                "employee_contribution": medical_emp,
                "employer_contribution": medical_employer,
                "total_contribution": medical_emp + medical_employer
            }).insert(ignore_permissions=True)
            
            # 3. Leave Report Store
            leave_taken = flt(frappe.db.get_value("Havano Leave Balances", {"employee": emp.name, "havano_leave_type": "Annual Leave"}, "leave_taken") or 0)
            frappe.get_doc({
                "doctype": "Leave Report Store",
                "employee": emp.name,
                "department": emp_doc.department,
                "payroll_period": payroll_period_str,
                "leave_days": leave_taken
            }).insert(ignore_permissions=True)
            
            # 4. Overtime Report Store
            frappe.get_doc({
                "doctype": "Overtime Report Store",
                "employee": emp.name,
                "department": emp_doc.department,
                "payroll_period": payroll_period_str,
                "overtime_hours": 0, # Could be calculated if hourly rate is known
                "amount": overtime_amt
            }).insert(ignore_permissions=True)
            # 5. Dynamic Report Stores for ALL Other Components
            component_totals = {}
            if hasattr(emp_doc, "employee_earnings"):
                for e in emp_doc.employee_earnings:
                    if e.components and "OVERTIME" not in e.components.upper():
                        component_totals[e.components] = component_totals.get(e.components, 0) + flt(e.amount_usd) + flt(e.amount_zwg)
                        
            if hasattr(emp_doc, "employee_deductions"):
                for d in emp_doc.employee_deductions:
                    if d.components and "FUNERAL" not in d.components.upper() and "CIMAS" not in d.components.upper() and "MEDICAL" not in d.components.upper():
                        component_totals[d.components] = component_totals.get(d.components, 0) + flt(d.amount_usd) + flt(d.amount_zwg)

            for comp_name, amt in component_totals.items():
                dt_name = f"{comp_name} Report Store"
                if frappe.db.exists("DocType", dt_name):
                    frappe.get_doc({
                        "doctype": dt_name,
                        "employee": emp.name,
                        "department": emp_doc.department,
                        "payroll_period": payroll_period_str,
                        "amount": amt
                    }).insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(title="Payroll Error", message=f"Custom Report Store Error for {emp.name}: {e}")

        try:
            update_employee_annual_leave(emp.name, payroll_period=period_name)
        except Exception as e:
            frappe.log_error(title="Payroll Error", message=f"Error updating annual leave allocation for {emp.name}: {str(e)}")

        try:
            update_havano_leave_balances(emp.name)
        except Exception as e:
            frappe.log_error(title="Payroll Error", message=f"Error updating leave balances for {emp.name}: {str(e)}")        
        # --- Journal Entry Aggregation ---
        emp_company = emp_doc.company
        currency = emp_doc.salary_currency or frappe.get_cached_value("Company", emp_company, "default_currency")
        je_key = (emp_company, currency)
        if je_key not in je_data:
            je_data[je_key] = {"entries": [], "net_pay": 0}
            
        # Earnings (Debits)
        if hasattr(emp_doc, "employee_earnings"):
            for e in emp_doc.employee_earnings:
                amt = flt(e.amount_usd) if currency == "USD" else flt(e.amount_zwg)
                if amt:
                    acc = get_account(e.components, emp_company)
                    if acc:
                        je_data[je_key]["entries"].append({
                            "account": acc, "debit": amt, "credit": 0, "cost_center": setting_cost_center
                        })
        
        # Deductions (Credits)
        if hasattr(emp_doc, "employee_deductions"):
            for d in emp_doc.employee_deductions:
                amt = flt(d.amount_usd) if currency == "USD" else flt(d.amount_zwg)
                if amt:
                    acc = get_account(d.components, emp_company)
                    if acc:
                        je_data[je_key]["entries"].append({
                            "account": acc, "debit": 0, "credit": amt, "cost_center": setting_cost_center
                        })
        
        # Net Pay (Credit)
        je_data[je_key]["net_pay"] += flt(emp_netpay)
            
        # --- Havano Payroll Journal Aggregation ---
        emp_company = emp_doc.company
        currency = emp_doc.salary_currency or frappe.get_cached_value("Company", emp_company, "default_currency")
        
        if emp_company not in pj_data:
            pj_data[emp_company] = {"total_earnings": 0, "zimra": 0, "mapped": {}, "net_pay": 0}
            
        if emp_company not in ecj_data:
            ecj_data[emp_company] = {
                "nssa": 0,
                "medical_aid": 0,
                "funeral_policy": 0,
                "lapf": 0,
                "nec": 0
            }

        # Employer Contributions (Medical Aid, Funeral, LAPF, NEC)
        basic_salary = flt(getattr(emp_doc, "basic_salary_calculated", 0))
        ecj_data[emp_company]["medical_aid"] += flt(getattr(emp_doc, "cimas_employer_", 0))
        ecj_data[emp_company]["funeral_policy"] += flt(getattr(emp_doc, "funeral_policy_employer_", 0))
        ecj_data[emp_company]["lapf"] += basic_salary * 0.173
        ecj_data[emp_company]["nec"] += basic_salary * 0.01

        total_earnings = 0
        zimra = 0
        
        if hasattr(emp_doc, "employee_earnings"):
            for e in emp_doc.employee_earnings:
                amt = flt(e.amount_usd) + flt(e.amount_zwg)
                total_earnings += amt
                
        if hasattr(emp_doc, "employee_deductions"):
            for d in emp_doc.employee_deductions:
                amt = flt(d.amount_usd) + flt(d.amount_zwg)
                if d.components in ["PAYE", "Aids Levy"]:
                    zimra += amt
                elif d.components and d.components.strip().lower() in mapped_components:
                    pj_data[emp_company]["mapped"][d.components] = pj_data[emp_company]["mapped"].get(d.components, 0) + amt
                
                # NSSA Employer Contribution match
                if d.components == "NSSA":
                    ecj_data[emp_company]["nssa"] += amt
                    
        pj_data[emp_company]["total_earnings"] += total_earnings
        pj_data[emp_company]["zimra"] += zimra
        pj_data[emp_company]["net_pay"] += flt(emp_netpay)
        
        frappe.db.commit()
    # --- Auto-create Havano Payroll Journal ---
    if not create_journal_entry:
        pj_data = {}
        ecj_data = {}

    for comp, data in pj_data.items():
        if not comp:
            frappe.log_error(title="Payroll Warning", message="Skipping Havano Payroll Journal creation for employee with no company")
            continue
            
        if data["total_earnings"] > 0:
            try:
                # Remove existing journal for the same period and company
                existing_pj = frappe.get_all("Havano Payroll Journal", filters={"payroll_period": period_name, "company": comp})
                for pj_rec in existing_pj:
                    frappe.delete_doc("Havano Payroll Journal", pj_rec.name, ignore_permissions=True)
                    
                pj = frappe.new_doc("Havano Payroll Journal")
                pj.name = f"{month_name}-{year}-{comp}"
                pj.payroll_period = period_name
                pj.company = comp
                
                # Row 2: Mapped Deductions
                mapped_total = 0
                for k, v in data["mapped"].items():
                    rounded_v = frappe.utils.flt(v, 2)
                    if rounded_v > 0:
                        pj.append("journal_details", {
                            "detail": k,
                            "dr": 0,
                            "cr": rounded_v
                        })
                        mapped_total += rounded_v
                
                # Row 3: ZIMRA
                zimra_total = frappe.utils.flt(data.get("zimra", 0), 2)
                if zimra_total > 0:
                    pj.append("journal_details", {
                        "detail": "ZIMRA",
                        "dr": 0,
                        "cr": zimra_total
                    })
                    
                # Row 4: Payroll Payables
                payables = frappe.utils.flt(data.get("net_pay", 0), 2)
                if payables > 0:
                    pj.append("journal_details", {
                        "detail": "Payroll Payables",
                        "dr": 0,
                        "cr": payables
                    })
                
                # Row 1: Salaries and Wages (Sum of CR side)
                total_cr = mapped_total + zimra_total + payables
                pj.append("journal_details", {
                    "detail": "Salaries and Wages",
                    "dr": total_cr,
                    "cr": 0
                })
                
                pj.insert(ignore_permissions=True)
                frappe.db.commit()
                
                # --- Create Accounting Journal Entry for Payroll ---
                je_entries = []
                missing_account = False
                for row in pj.journal_details:
                    if row.detail == "Salaries and Wages":
                        acc_gl = get_account("Basic Salary", comp)
                    elif row.detail == "Payroll Payables":
                        acc_gl = default_payable_account or mapped_components.get("payroll payables", "")
                    else:
                        acc_gl = mapped_components.get(row.detail.strip().lower() if row.detail else "")
                        
                    if not acc_gl:
                        err_msg = f"Missing GL Account for '{row.detail}' in Havano Payroll Settings > Setup Accounts"
                        if row.detail == "Salaries and Wages":
                            err_msg = f"Missing GL Account for 'Basic Salary' in Havano Salary Component > Setup Accounts"
                        elif row.detail == "Payroll Payables":
                            err_msg = f"Missing Default Payroll Payable Account in Havano Payroll Settings"
                        frappe.log_error(title="Accounting JE Error", message=err_msg)
                        frappe.msgprint(err_msg, indicator="orange", alert=True)
                        missing_account = True
                        break
                    acc_type = frappe.db.get_value("Account", acc_gl, "account_type")
                    entry = {
                        "account": acc_gl,
                        "debit_in_account_currency": row.dr,
                        "credit_in_account_currency": row.cr,
                        "debit": row.dr,
                        "credit": row.cr,
                        "cost_center": setting_cost_center
                    }
                    if acc_type in ["Payable", "Receivable"] and setting_supplier:
                        entry["party_type"] = "Supplier"
                        entry["party"] = setting_supplier
                    je_entries.append(entry)
                    
                if not missing_account and je_entries:
                    
                    remark = f"Payroll Journal Entry for {month_name} {year}"
                    existing_jes = frappe.get_all("Journal Entry", filters={"user_remark": remark, "company": comp, "docstatus": 0})
                    for existing_je in existing_jes:
                        frappe.delete_doc("Journal Entry", existing_je.name, ignore_permissions=True)
                        
                    # Calculate Custom Name
                    jes = frappe.get_all("Journal Entry", filters={"name": ["like", "EmployeeJournal-%"]}, fields=["name"])
                    max_id = 0
                    for je_rec in jes:
                        try:
                            num = int(je_rec.name.replace("EmployeeJournal-", ""))
                            if num > max_id:
                                max_id = num
                        except:
                            pass
                    je_name = f"EmployeeJournal-{str(max_id + 1).zfill(4)}"
                        
                    je = frappe.new_doc("Journal Entry")
                    je.voucher_type = "Journal Entry"
                    je.company = comp
                    je.posting_date = work_date or nowdate()
                    je.user_remark = remark
                    je.title = f"Payroll Journal - {month_name} {year}"
                    for e in je_entries:
                        je.append("accounts", e)
                    je.insert(ignore_permissions=True)
                    
                    if je.name != je_name:
                        frappe.flags.ignore_permissions = True
                        frappe.rename_doc("Journal Entry", je.name, je_name, force=True)
                        frappe.flags.ignore_permissions = False
                        
                    je.submit()
                    frappe.db.commit()
                    
                frappe.msgprint(f"Havano Payroll Journal created for {comp}", alert=True)
            except Exception as e:
                frappe.log_error(title=f"Havano Payroll Journal Error for {comp}", message=frappe.get_traceback())
                frappe.msgprint(f"Failed to create Havano Payroll Journal for {comp}. Check Error Log.", indicator="red")

    # --- Auto-create Havano Employer Contributions Journal ---
    for comp, data in ecj_data.items():
        if not comp:
            continue
            
        # Round each contribution before summing to avoid 1-cent imbalances
        nssa_cr = frappe.utils.flt(data["nssa"], 2)
        med_cr = frappe.utils.flt(data["medical_aid"], 2)
        fun_cr = frappe.utils.flt(data["funeral_policy"], 2)
        lapf_cr = frappe.utils.flt(data["lapf"], 2)
        nec_cr = frappe.utils.flt(data["nec"], 2)
        
        total_dr = nssa_cr + med_cr + fun_cr + lapf_cr + nec_cr
        
        if total_dr > 0:
            try:
                # Remove existing journal for the same period and company
                existing_ecj = frappe.get_all("Havano Employer Contributions Journal", filters={"payroll_period": period_name, "company": comp})
                for ecj_rec in existing_ecj:
                    frappe.delete_doc("Havano Employer Contributions Journal", ecj_rec.name, ignore_permissions=True)
                    
                ecj = frappe.new_doc("Havano Employer Contributions Journal")
                ecj.name = f"{month_name}-{year}-{comp}"
                ecj.payroll_period = period_name
                ecj.company = comp
                
                # DR side
                ecj.append("journal_details", {
                    "detail": "Salaries and Wages",
                    "dr": total_dr,
                    "cr": 0
                })
                
                # CR side
                if nssa_cr > 0:
                    ecj.append("journal_details", {"detail": "NSSA", "dr": 0, "cr": nssa_cr})
                if med_cr > 0:
                    ecj.append("journal_details", {"detail": "Medical Aid", "dr": 0, "cr": med_cr})
                if fun_cr > 0:
                    ecj.append("journal_details", {"detail": "Funeral Policy", "dr": 0, "cr": fun_cr})
                if lapf_cr > 0:
                    ecj.append("journal_details", {"detail": "LAPF", "dr": 0, "cr": lapf_cr})
                if nec_cr > 0:
                    ecj.append("journal_details", {"detail": "NEC", "dr": 0, "cr": nec_cr})
                    
                ecj.insert(ignore_permissions=True)
                frappe.db.commit()
                
                # --- Create Accounting Journal Entry for Employer Contributions ---
                je_entries = []
                missing_account = False
                for row in ecj.journal_details:
                    if row.detail == "Salaries and Wages":
                        acc_gl = get_account("Basic Salary", comp)
                    else:
                        acc_gl = mapped_components.get(row.detail.strip().lower() if row.detail else "")
                        
                    if not acc_gl:
                        err_msg = f"Missing GL Account for '{row.detail}' in Havano Payroll Settings > Setup Accounts"
                        if row.detail == "Salaries and Wages":
                            err_msg = f"Missing GL Account for 'Basic Salary' in Havano Salary Component > Setup Accounts (used for Employer Contributions expense)"
                        frappe.log_error(title="Accounting JE Error", message=err_msg)
                        frappe.msgprint(err_msg, indicator="orange", alert=True)
                        missing_account = True
                        break
                    acc_type = frappe.db.get_value("Account", acc_gl, "account_type")
                    entry = {
                        "account": acc_gl,
                        "debit_in_account_currency": row.dr,
                        "credit_in_account_currency": row.cr,
                        "debit": row.dr,
                        "credit": row.cr,
                        "cost_center": setting_cost_center
                    }
                    if acc_type in ["Payable", "Receivable"] and setting_supplier:
                        entry["party_type"] = "Supplier"
                        entry["party"] = setting_supplier
                    je_entries.append(entry)
                    
                if not missing_account and je_entries:
                    
                    remark = f"Employer Contributions Journal Entry for {month_name} {year}"
                    existing_jes = frappe.get_all("Journal Entry", filters={"user_remark": remark, "company": comp, "docstatus": 0})
                    for existing_je in existing_jes:
                        frappe.delete_doc("Journal Entry", existing_je.name, ignore_permissions=True)
                        
                    # Calculate Custom Name
                    jes = frappe.get_all("Journal Entry", filters={"name": ["like", "EmployerJournal-%"]}, fields=["name"])
                    max_id = 0
                    for je_rec in jes:
                        try:
                            num = int(je_rec.name.replace("EmployerJournal-", ""))
                            if num > max_id:
                                max_id = num
                        except:
                            pass
                    je_name = f"EmployerJournal-{str(max_id + 1).zfill(4)}"
                        
                    je = frappe.new_doc("Journal Entry")
                    je.voucher_type = "Journal Entry"
                    je.company = comp
                    je.posting_date = work_date or nowdate()
                    je.user_remark = remark
                    je.title = f"Employer Contributions - {month_name} {year}"
                    for e in je_entries:
                        je.append("accounts", e)
                    je.insert(ignore_permissions=True)
                    
                    if je.name != je_name:
                        frappe.flags.ignore_permissions = True
                        frappe.rename_doc("Journal Entry", je.name, je_name, force=True)
                        frappe.flags.ignore_permissions = False
                        
                    je.submit()
                    frappe.db.commit()
                    
                frappe.msgprint(f"Havano Employer Contributions Journal created for {comp}", alert=True)
            except Exception as e:
                frappe.log_error(title=f"Employer Contributions Journal Error for {comp}", message=frappe.get_traceback())
                frappe.msgprint(f"Failed to create Employer Contributions Journal for {comp}. Check Error Log.", indicator="red")
    
    return f"Payroll created for {len(employees)} employees for {month_name} {year}."




def get_loan_deduction_amounts(employee_id):
    """
    Check if the employee has a 'Loan Repayment' deduction.
    Returns a dict with amount_usd and amount_zwg, 0 if not found.
    """
    try:
        emp_doc = frappe.get_doc("havano_employee", employee_id)
        for ded in emp_doc.employee_deductions:
            if ded.components == "Loan Repayment":
                return {
                    "amount_usd": ded.amount_usd or 0,
                    "amount_zwg": ded.amount_zwg or 0
                }
        # If not found
        return {"amount_usd": 0, "amount_zwg": 0}
    except frappe.DoesNotExistError:
        return {"amount_usd": 0, "amount_zwg": 0}

@frappe.whitelist()
def get_basic_salary_component():
    doc = frappe.get_doc("havano_salary_component", "Basic Salary")
    return doc.as_dict().get("accounts")


def get_employee_loan(employee_id):
    # Check if the employee has any Employee Loan record
    loans = frappe.get_all(
        "Employee Loan",
        filters={"employee": employee_id},
        fields=["name", "monthly_amount_to_be_paid", "loan_paid", "current_loan_balance"]
    )

    if not loans:
        return None  # No loan found

    # If multiple loans, you can pick the latest one or return all
    latest_loan = loans[-1]  # or loans[0] depending on ordering
    loan_doc = frappe.get_doc("Employee Loan", latest_loan["name"])
    return loan_doc

@frappe.whitelist()
def add_sdl_report(employee=None,date=None, amount=None, department=None, name=None):
    """
    Adds an SDL Report record if one for the same employee and date doesn't exist.
    
    Args:
        employee (str): Employee ID
        employee_name (str): Employee full name
        date (str): Month-Year format, e.g., "June 2026"
        amount (float): SDL amount
        name (str): Doc name
    Returns:
        str: Name of the created SDL Report or a message if skipped
    """
    if not (employee and date and amount is not None):
        frappe.throw("All fields (employee, employee_name, date, amount) are required.")

    # Check if record already exists for this employee and date
    existing = frappe.db.exists("SDL Report", {"employee": employee, "date": date})
    if existing:
        return f"SDL Report for {employee} on {date} already exists. Skipping creation."

    # Create new SDL Report
    doc = frappe.get_doc({
        "doctype": "SDL Report",
        "employee": employee,
        "date": date,
        "amount": amount,
        "department": department
    })
    if name:
        doc.name = name
    doc.insert(ignore_permissions=True)
    frappe.db.commit()  # optional, forces immediate save

    return f"SDL Report created: {doc.name}"


def create_havano_leave_ledger_entry(employee, transaction_type, transaction_name, days_added, days_deducted, balance):
    try:
        from frappe.utils import nowdate
        doc = frappe.new_doc("Havano Leave Ledger Entry")
        doc.employee = employee
        doc.posting_date = nowdate()
        doc.transaction_type = transaction_type
        doc.transaction_name = transaction_name
        doc.days_added = days_added
        doc.days_deducted = days_deducted
        doc.balance_after_transaction = balance
        doc.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(title="Leave Ledger Entry Failed", message=frappe.get_traceback())

@frappe.whitelist()
def update_employee_annual_leave(employee, days_to_add=2.5, payroll_period=None):
    """
    Adds or updates annual leave allocation for a single employee.
    Returns the final total_days.
    """

    # Default payroll period = current year-month
    if not payroll_period:
        from datetime import date
        payroll_period = date.today().strftime("%B %Y")

    # Get employee record
    emp = frappe.db.get_value(
        "havano_employee",
        {"name": employee},
        ["name", "employee_name"],
        as_dict=True
    )
    if not emp:
        frappe.throw(f"Employee {employee} not found")

    # Check if allocation exists
    existing_allocation = frappe.db.get_value(
        "Havano Annual Leave Allocation",
        {"employee": employee},
        ["name", "total_days"],
        as_dict=True
    )

    if existing_allocation:
        # Add to total_days
        new_total = (existing_allocation.get("total_days") or 0) + float(days_to_add)
        frappe.db.set_value("Havano Annual Leave Allocation", existing_allocation.get("name"), "total_days", new_total)
        create_havano_leave_ledger_entry(employee, "Leave Allocation", payroll_period, float(days_to_add), 0.0, new_total)
        frappe.db.commit()
        return new_total
    else:
        # Create new record
        new_doc = frappe.get_doc({
            "doctype": "Havano Annual Leave Allocation",
            "employee": employee,
            "total_days": float(days_to_add),
            "payment_period": payroll_period
        })
        new_doc.insert(ignore_permissions=True)
        create_havano_leave_ledger_entry(employee, "Leave Allocation", payroll_period, float(days_to_add), 0.0, float(days_to_add))
        frappe.db.commit()
        return new_doc.total_days


def get_payroll_settings():
    try:
        settings = frappe.get_single("Havano Payroll Settings")
    except frappe.DoesNotExistError:
        frappe.throw("Havano Payroll Settings NOT FOUND. Please create it first!", title="Missing Settings")

    if not settings.supplier or not settings.cost_center:
        frappe.throw("Supplier or Cost Center is missing in Havano Payroll Settings.", 
                     title="Incomplete Settings")
    return {
        "supplier": settings.supplier,
        "cost_center": settings.cost_center,
        "create_journal_entry": getattr(settings, "create_journal_entry", 0),
        "default_payroll_payable_account": getattr(settings, "default_payroll_payable_account", None)
    }

@frappe.whitelist()
def update_havano_leave_balances(employee):
    """
    Ensures all standard leave types exist for the employee in 'Havano Leave Balances'.
    If a type exists, skip it — except 'Annual Leave', which always increases by 2.5 days.
    """

    settings = frappe.get_single("Havano Payroll Settings")
    max_annual = flt(settings.max_annual_leave_days) or 90.0
    max_study = flt(settings.max_study_leave_days) or 10.0
    max_special = flt(settings.max_special_leave_days) or 12.0
    max_bereavement = flt(settings.max_bereavement_leave_days) or 12.0
    max_sick = flt(settings.max_sick_leave_days) or 90.0
    max_maternity = flt(settings.max_maternity_leave_days) or 90.0

    # Define the default leave types and their default balances
    default_leave_types = {
        "Annual Leave": 2.5,
        "Study Leave": max_study,
        "Special Leave": max_special,
        "Bereavement Leave": max_bereavement,
        "Sick Leave": max_sick,
        "Maternity Leave": max_maternity
    }

    # Get employee details
    emp = frappe.get_doc("havano_employee", employee)

    # Loop over each leave type
    for leave_type, balance in default_leave_types.items():
        # Try to find the actual name of the leave type in the system
        # If it doesn't match 'Annual Leave' exactly, try to find one that looks like it
        actual_leave_type = leave_type
        if leave_type == "Annual Leave":
            db_leave_type = frappe.db.get_value("havano_leave_type", {"name": ["like", "%Annual%"]}, "name")
            if db_leave_type:
                actual_leave_type = db_leave_type

        existing_record = frappe.db.get_value(
            "Havano Leave Balances",
            {"employee": emp.name, "havano_leave_type": actual_leave_type},
            "name"
        )

        if existing_record:
            # If it already exists, only modify Annual Leave
            if "annual" in actual_leave_type.lower():
                # Fetch current balance directly from DB to avoid any caching
                current_balance = flt(frappe.db.get_value("Havano Leave Balances", existing_record, "leave_balance") or 0)
                new_balance = current_balance + 2.5
                
                # Cap at max_annual days
                if new_balance > max_annual:
                    new_balance = max_annual
                
                # Update using set_value for direct DB update
                frappe.db.set_value("Havano Leave Balances", existing_record, "leave_balance", new_balance)
                frappe.db.commit()
                
                frappe.log_error(title="Leave Update", message=f"Updated Annual Leave for {emp.name}: {current_balance} -> {new_balance}")
                frappe.logger().info(f"Updated Annual Leave for {emp.name} to {new_balance} (capped at {max_annual})")
            else:
                frappe.logger().info(f"{leave_type} already exists for {emp.name}, skipped.")
        else:
            # Create new leave record
            new_doc = frappe.get_doc({
                "doctype": "Havano Leave Balances",
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "havano_leave_type": actual_leave_type,
                "leave_balance": balance
            })
            new_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.log_error(title="Leave Update", message=f"Created new {actual_leave_type} for {emp.name} with balance {balance}")
            frappe.logger().info(f"Created {actual_leave_type} for {emp.name}")

    return f"Leave balances updated for {emp.employee_name}"

@frappe.whitelist()
def create_zimra_itf16(*,
    surname=None,
    first_name=None,
    employee_id=None,
    dob=None,
    start_date=None,
    end_date=None,
    gross_paye=None,
    basic_pension=None,
    payee=None,
    aids_levy=None,
    currency=None,
    name=None
):

    try:
        # Safely cast numeric values
        gross_paye = float(gross_paye or 0)
        basic_pension = float(basic_pension or 0)
        payee = float(payee or 0)
        aids_levy = float(aids_levy or 0)

        # Create the document
        doc = frappe.get_doc({
            "doctype": "ZIMRA ITF16",
            "surname": surname,
            "first_name": first_name,
            "employee_id": employee_id,
            "dob": dob,
            "start_date": start_date,
            "end_date": end_date,
            "gross_paye": gross_paye,
            "basic_pension": basic_pension,
            "payee": payee,
            "aids_levy": aids_levy,
            "currency":currency
        })
        if name:
            doc.name = name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "name": doc.name}
    except Exception as e:
        frappe.log_error(title="ZIMRA ITF16 Creation Failed", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def create_zimra_p2form(*, 
    employer_name=None,
    trade_name=None,
    tin_number=None,
    tax_period=None,
    total_renumeration=None,
    gross_paye=None,
    aids_levy=None,
    total_tax_due=None,
    currency=None,
    name=None
):
    """Create a new ZIMRA P2FORM document using named parameters with defaults"""
    try:
        doc = frappe.get_doc({
            "doctype": "ZIMRA P2FORM",
            "employer_name": employer_name,
            "trade_name": trade_name,
            "tin_number": tin_number,
            "tax_period": tax_period,
            "total_renumeration": total_renumeration,
            "gross_paye": gross_paye,
            "aids_levy": aids_levy,
            "total_tax_due": total_tax_due,
            "currency": currency,
            "department": department
        })
        if name:
            doc.name = name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "name": doc.name}

    except Exception as e:
        frappe.log_error(title="ZIMRA P2FORM Creation Failed", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def create_nssa_p4_report_store(
    surname=None,
    first_name=None,
    national_id=None,
    payroll_period=None,
    start_date=None,
    end_date=None,
    total_insuarable_earnings_usd=None,
    total_insuarable_earnings_zwg=None,
    current_contributions_usd=None,
    current_contributions_zwg=None,
    arrears_usd=None,
    arrears_zwg=None,
    prepayments_usd=None,
    surcharge_usd=None,
    surchage_zwg=None,
    total_payment_usd=None,
    total_payment_zwg=None,
    prepayments_zwg_column=None,
    department=None,
    name=None
):
    """Create a new record in NSSA P4 Report Store"""
    try:
        doc = frappe.get_doc({
            "doctype": "NSSA P4 Report Store",
            "surname": surname,
            "first_name": first_name,
            "national_id": national_id,
            "payroll_period": payroll_period,
            "start_date": start_date,
            "end_date": end_date,
            "total_insuarable_earnings_usd": total_insuarable_earnings_usd,
            "total_insuarable_earnings_zwg": total_insuarable_earnings_zwg,
            "current_contributions_usd": current_contributions_usd,
            "current_contributions_zwg": current_contributions_zwg,
            "arrears_usd": arrears_usd,
            "arrears_zwg": arrears_zwg,
            "prepayments_usd": prepayments_usd,
            "surcharge_usd": surcharge_usd,
            "surchage_zwg": surchage_zwg,
            "total_payment_usd": total_payment_usd,
            "total_payment_zwg": total_payment_zwg,
            "prepayments_zwg_column": prepayments_zwg_column,
            "department": department,
        })
        
        if name:
            doc.name = name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": "Record created successfully", "name": doc.name}

    except Exception as e:
        frappe.log_error(message=str(e), title="NSSA P4 Report Store Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def create_payroll_report(
    first_name,
    surname,
    nssa_zwg_employee,
    nssa_zwg_employer,
    nssa_usd_employee,
    nssa_usd_employer,
    payroll_period,
    wcif_usd,
    wcif_zwg,
    name=None
):
    """
    Creates a new Payroll Summary record in the system.
    """
    try:
        doc = frappe.new_doc("Reports Store NASSA")  # replace with your actual Doctype name
        doc.first_name = first_name
        doc.surname = surname
        doc.nssa_zwg_employee = nssa_zwg_employee
        doc.nssa_zwg_employer = nssa_zwg_employer
        doc.nssa_usd_employee = nssa_usd_employee
        doc.nssa_usd_employer = nssa_usd_employer
        doc.payroll_period = payroll_period
        doc.wcif_usd = wcif_usd
        doc.wcif_zwg = wcif_zwg

        if name:
            doc.name = name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": f"Payroll Summary created for {first_name} {surname}"}

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Payroll Summary Creation Failed")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def create_nec_report(
    surname=None,
    first_name=None,
    start_date=None,
    end_date=None,
    grade=None,
    nec_earnings_usd=None,
    employer_contribution_usd=None,
    employer_contribution_zwg=None,
    total_nec_usd=None,
    department=None,
    name=None
):
    """Create a new record in NEC Report"""
    try:
        doc = frappe.get_doc({
            "doctype": "NEC Report",
            "surname": surname,
            "first_name": first_name,
            "start_date": start_date,
            "end_date": end_date,
            "grade": grade,
            "nec_earnings_usd": nec_earnings_usd,
            "employer_contribution_usd": employer_contribution_usd,
            "employer_contribution_zwg": employer_contribution_zwg,
            "total_nec_usd": total_nec_usd,
            "department": department
        })
        
        if name:
            doc.name = name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": "NEC Record created successfully", "name": doc.name}

    except Exception as e:
        frappe.log_error(message=str(e), title="NEC Report Error")
        return {"status": "error", "message": str(e)}


from frappe.utils.pdf import get_pdf
import frappe
from frappe.utils import flt
import os
import frappe
from frappe.utils import flt
from frappe.utils.background_jobs import enqueue
from weasyprint import HTML, CSS
import os

@frappe.whitelist()
def generate_salary_slips_bulk(month, year):
    """
    Enqueue payroll PDF generation in the background.
    """
    job = enqueue(
        "havano_zim_payroll.api.generate_salary_slips",
        month=month,
        year=year,
        queue="long",
        timeout=15000
    )

    return {
        "message": f"Salary Slips job queued for {month}/{year}",
        "job_id": job.id
    }


@frappe.whitelist()
def generate_salary_slips(month, year):
    import os
    from weasyprint import HTML

    # 1️⃣ Get employees (only what you need)
    employees = frappe.get_all(
        "havano_employee",
        filters={"status": "Active"},
        fields=["name", "employee_name"]
    )

    # 2️⃣ Load CSS once
    css_file = frappe.get_app_path(
        "frappe", "public", "dist", "css", "print.bundle.css"
    )

    inline_css = ""
    if os.path.exists(css_file):
        with open(css_file) as f:
            inline_css = f.read()

    # 3️⃣ Start ONE HTML document
    body_html = []

    for emp in employees:
        slip_html = frappe.get_print(
            doctype="havano_employee",
            name=emp.name,
            print_format="havano payslip single currency",
            no_letterhead=1
        )

        body_html.append(f"""
        <div class="page">
            <h2>{emp.employee_name or emp.name} — {month} {year}</h2>
            {slip_html}
        </div>
        """)

    # 4️⃣ Final HTML
    final_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            {inline_css}
            .page {{
                page-break-after: always;
                width: 100%;
                box-sizing: border-box;
            }}
        </style>
    </head>
    <body>
        {''.join(body_html)}
    </body>
    </html>
    """

    # 5️⃣ Generate PDF ONCE
    pdf = HTML(string=final_html).write_pdf()

    # 6️⃣ Save file
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": f"Salary_Slips_{month}_{year}.pdf",
        "is_private": 0,
        "content": pdf
    })
    file_doc.insert(ignore_permissions=True)

    # 7️⃣ Update settings
    settings = frappe.get_single("Havano Payroll Settings")
    settings.payroll_salary_slip_location = file_doc.file_url
    settings.save(ignore_permissions=True)

    return file_doc.file_url

@frappe.whitelist()
def cancel_payroll(month, year, reason):
    """
    Enqueue payroll in background and return job info.
    """
    job = frappe.enqueue(
        "havano_zim_payroll.api.cancel_payroll_func",  # your payroll function path
        month=month,
        year=year,
        reason=reason,
        queue="long",
        timeout=15000
    )

    # Return only simple data — avoid returning the Job object itself
    return {
        "message": f"Payroll cancell job queued for {month}/{year}",
        "job_id": job.id
    }


@frappe.whitelist()
def cancel_payroll_func(month, year, reason):
    """
    Print payroll entries for a given month and year along with the reason.
    """
    if not month or not year:
        frappe.throw("Month and Year are required.")
    print(f"{month},{int(year)}")

    payroll_entries = frappe.get_all(
        "Havano Payroll Entry",
        filters={"payroll_period": f"{month} {int(year)}"}, 
        fields=["name", "first_name", "last_name"]
    )

    if not payroll_entries:
        return f"No submitted payroll found for {month} {year}."

    # Print entries to the server log and reverse leave for each employee
    for entry in payroll_entries:
        print(f"Payroll: {entry['name']}, Employee: {entry.get('first_name')}, Reason: {reason}")
        
        # Reverse leave
        emp = frappe.db.get_value("havano_employee", {"first_name": entry.get("first_name"), "last_name": entry.get("last_name") or ""}, "name")
        if emp:
            try:
                reverse_leave_for_employee(emp)
            except Exception as e:
                frappe.log_error(title="Leave Reversal Error", message=f"Error reversing leave for {emp} during cancel: {str(e)}")

    # Call period-wide deletes once outside the loop
    payroll_period_str = f"{month} {int(year)}"
    cancel_payroll_purchase_invoices(payroll_period_str)
    delete_sdl_for_period(payroll_period_str)
    delete_nassa_reports_for_period(payroll_period_str)
    delete_salary_summary_for_period(payroll_period_str)
    delete_havano_payroll_entries(payroll_period_str)
    delete_journal_entries_for_period(payroll_period_str)

    return f"{len(payroll_entries)} payroll entries for {month} {year} with reason: {reason}."

def reverse_leave_for_employee(employee, days_to_deduct=2.5):
    # 1. Deduct from Annual Leave Allocation
    allocation = frappe.db.get_value("Havano Annual Leave Allocation", {"employee": employee}, "name")
    if allocation:
        current_alloc = flt(frappe.db.get_value("Havano Annual Leave Allocation", allocation, "total_days") or 0)
        new_bal = current_alloc - days_to_deduct
        frappe.db.set_value("Havano Annual Leave Allocation", allocation, "total_days", new_bal)
        create_havano_leave_ledger_entry(employee, "Leave Reversal", "Payroll Cancelled", 0.0, float(days_to_deduct), new_bal)

    # 2. Deduct from Havano Leave Balances
    actual_leave_type = "Annual Leave"
    db_leave_type = frappe.db.get_value("havano_leave_type", {"name": ["like", "%Annual%"]}, "name")
    if db_leave_type:
        actual_leave_type = db_leave_type

    leave_balance = frappe.db.get_value("Havano Leave Balances", {"employee": employee, "havano_leave_type": actual_leave_type}, "name")
    if leave_balance:
        current_bal = flt(frappe.db.get_value("Havano Leave Balances", leave_balance, "leave_balance") or 0)
        frappe.db.set_value("Havano Leave Balances", leave_balance, "leave_balance", current_bal - days_to_deduct)

    frappe.db.commit()

def cancel_payroll_purchase_invoices(payroll_period):

    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "custom_from_payroll": 1,
            "custom_payroll_period": payroll_period,
            "docstatus": 1  # Submitted only (uncancelled)
        },
        pluck="name"
    )

    if not invoices:
        frappe.log_error(
            title="Payroll PI Cancel",
            message=f"No Purchase Invoices found for payroll period: {payroll_period}"
        )
        return

    for pi_name in invoices:
        try:
            pi = frappe.get_doc("Purchase Invoice", pi_name)
            pi.cancel()

            frappe.log_error(
                title="Payroll PI Cancelled",
                message=f"Purchase Invoice {pi_name} cancelled for payroll period {payroll_period}"
            )

        except Exception:
            frappe.log_error(
                title="Payroll PI Cancel Failed",
                message=frappe.get_traceback()
            )

def delete_sdl_for_period(period_str):
    """
    Deletes SDL entries where payroll period is stored as string
    e.g. 'January 2025'
    """

    sdl_entries = frappe.get_all(
        "SDL Report", 
        filters={
            "date": period_str
        },
        pluck="name"
    )

    if not sdl_entries:
        frappe.log_error(
            title="SDL Delete",
            message=f"No SDL entries found for payroll period: {period_str}"
        )
        return

    deleted = 0

    for name in sdl_entries:
        try:
            frappe.delete_doc(
                "SDL Report",
                name,
                force=1
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                title="SDL Delete Failed",
                message=frappe.get_traceback()
            )

    frappe.log_error(
        title="SDL Delete Success",
        message=f"Deleted {deleted} SDL entries for payroll period {period_str}"
    )

def delete_nassa_reports_for_period(period_str):
    """
    Deletes Reports Store NASSA entries for a given payroll period string
    e.g. 'January 2025'
    """

    reports = frappe.get_all(
        "Reports Store NASSA",
        filters={
            "payroll_period": period_str
        },
        pluck="name"
    )

    if not reports:
        frappe.log_error(
            title="NASSA Reports Delete",
            message=f"No NASSA reports found for payroll period: {period_str}"
        )
        return

    deleted = 0

    for name in reports:
        try:
            frappe.delete_doc(
                "Reports Store NASSA",
                name,
                force=1
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                title="NASSA Reports Delete Failed",
                message=frappe.get_traceback()
            )

    frappe.log_error(
        title="NASSA Reports Delete Success",
        message=f"Deleted {deleted} NASSA report entries for payroll period {period_str}"
    )


def delete_salary_summary_for_period(period_str):
    """
    Deletes Salary Summary On Payroll Run entries
    for a given period string e.g. 'January 2025'
    """

    summaries = frappe.get_all(
        "Salary Summary On Payroll Run",
        filters={
            "period": period_str
        },
        pluck="name"
    )

    if not summaries:
        frappe.log_error(
            title="Salary Summary Delete",
            message=f"No Salary Summary entries found for period: {period_str}"
        )
        return

    deleted = 0

    for name in summaries:
        try:
            frappe.delete_doc(
                "Salary Summary On Payroll Run",
                name,
                force=1
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                title="Salary Summary Delete Failed",
                message=frappe.get_traceback()
            )

    frappe.log_error(
        title="Salary Summary Delete Success",
        message=f"Deleted {deleted} Salary Summary entries for period {period_str}"
    )

def delete_havano_payroll_entries(period_str):
    """
    Deletes Havano Payroll Entry records
    for a given period string e.g. 'January 2025'
    """

    entries = frappe.get_all(
        "Havano Payroll Entry",
        filters={
            "payroll_period": period_str
        },
        pluck="name"
    )

    if not entries:
        frappe.log_error(
            title="Havano Payroll Delete",
            message=f"No Havano Payroll Entry found for period: {period_str}"
        )
        return

    deleted = 0

    for name in entries:
        try:
            frappe.delete_doc(
                "Havano Payroll Entry",
                name,
                force=1
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                title="Havano Payroll Delete Failed",
                message=frappe.get_traceback()
            )

    frappe.log_error(
        title="Havano Payroll Delete Success",
        message=f"Deleted {deleted} Havano Payroll Entry records for period {period_str}"
    )

def delete_journal_entries_for_period(period_str):
    """
    Deletes Journal Entries, Havano Payroll Journals, and Employer Contribution Journals for a given period string.
    """
    # 1. Delete Journal Entries
    jes = frappe.get_all("Journal Entry", filters={"user_remark": ["like", f"%{period_str}%"]}, pluck="name")
    deleted_jes = 0
    for name in jes:
        try:
            frappe.delete_doc("Journal Entry", name, force=1, ignore_permissions=True)
            deleted_jes += 1
        except Exception:
            frappe.log_error(title="JE Delete Failed", message=frappe.get_traceback())

    # 2. Delete Havano Payroll Journal
    pjs = frappe.get_all("Havano Payroll Journal", filters={"payroll_period": period_str}, pluck="name")
    for name in pjs:
        try:
            frappe.delete_doc("Havano Payroll Journal", name, force=1, ignore_permissions=True)
        except Exception:
            pass
            
    # 3. Delete Havano Employer Contributions Journal
    ecjs = frappe.get_all("Havano Employer Contributions Journal", filters={"payroll_period": period_str}, pluck="name")
    for name in ecjs:
        try:
            frappe.delete_doc("Havano Employer Contributions Journal", name, force=1, ignore_permissions=True)
        except Exception:
            pass

    frappe.log_error(title="Journal Entries Delete Success", message=f"Deleted {deleted_jes} Journal Entries for period {period_str}")
import frappe
from frappe.utils import flt
import os
import json

@frappe.whitelist()
def add_payroll_fields_to_purchase_invoice():
    # Path to Purchase Invoice DocType JSON
    module_path = frappe.get_module_path("accounts")
    json_path = os.path.join(module_path, "doctype/purchase_invoice/purchase_invoice.json")

    # Load existing JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    # Define new fields
    new_fields = [
        {
            "fieldname": "custom_payroll_period",
            "label": "Payroll Period",
            "fieldtype": "Data",
            "insert_after": "posting_date",  # adjust where you want it
            "hidden": 0,
            "reqd": 0
        },
        {
            "fieldname": "custom_from_payroll",
            "label": "From Payroll",
            "fieldtype": "Check",
            "insert_after": "company",
            "hidden": 0,
            "reqd": 0
        }
    ]
    # Add fields if they don't exist
    existing_fieldnames = [f["fieldname"] for f in data.get("fields", [])]
    added = False

    for field in new_fields:
        if field["fieldname"] not in existing_fieldnames:
            data["fields"].append(field)
            added = True

    if added:
        # Save JSON back
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        # Reload DocType
        frappe.reload_doc("accounts", "doctype", "purchase_invoice", force=True)
        frappe.clear_cache(doctype="Purchase Invoice")

        return "Payroll Period and From Payroll fields added successfully"

    return "Fields already exist"

@frappe.whitelist()
def cleanup_obsolete_doctypes():
    for doctype in ["Payroll Summary", "Payroll Summary Item"]:
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
            frappe.db.commit()
    return "Cleanup Done"
