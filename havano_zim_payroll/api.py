import frappe
from frappe.utils import flt
from frappe.utils import nowdate, flt
from datetime import date
import calendar
from frappe import error_log
frappe.error_log = error_log


@frappe.whitelist()
def run_payroll_async(month, year, work_date=None, daily=None, sync=False):
    """
    Enqueue payroll or run synchronously.
    Defaults to sync=True to ensure immediate results if workers aren't active.
    """
    if sync:
        # Run immediately in the current request
        return run_payroll(month, year, work_date, daily)
    
    job = frappe.enqueue(
        "havano_zim_payroll.api.run_payroll",
        month=month,
        year=year,
        work_date=work_date,
        daily=daily,
        queue="default",
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
def run_payroll(month, year, work_date, daily):
    settin=get_payroll_settings()
    setting_cost_center=settin["cost_center"]
    setting_supplier=settin["supplier"]
    create_journal_entry = flt(settin.get("create_journal_entry"))
    default_payable_account = settin.get("default_payroll_payable_account")
    
    try:
        settings = frappe.get_single("Havano Payroll Settings")
        mapped_components = [row.component for row in settings.get("payroll_journal_accounts", [])]
    except Exception:
        mapped_components = []

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
            ignore_permissions=True
        )
    else:
        # Default: Process all Active employees regardless of frequency (or you can filter for Monthly)
        employees = frappe.get_all(
            "havano_employee",
            filters={"status": "Active"},
            fields=["name", "first_name", "last_name", "net_income", "payroll_frequency"],
            ignore_permissions=True
        )

    frappe.log_error(f"Found {len(employees)} active employees for payroll run (Daily={daily})", "Payroll Debug")
    if not employees:
        frappe.log_error("No employees found for payroll run", "Payroll Error")
        return "No employees found."
    
    frappe.log_error(f"Starting payroll run for {len(employees)} employees", "Payroll Progress")
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

    # Initialize default account for SDL report/invoice
    basic_comp_accounts = get_basic_salary_component()
    acc = basic_comp_accounts[0] if basic_comp_accounts else None
    
    if not acc:
        frappe.log_error("Basic Salary component accounting is not configured. Cannot create invoices.", "Payroll Configuration Error")

    for emp in employees:
        frappe.logger().info(f"Processing payroll for: {emp.name}")
        emp_doc = frappe.get_doc("havano_employee", emp.name)
        # 1. Clean existing loan components to prevent duplicates or lingering ones from past months
        emp_doc.employee_earnings = [e for e in getattr(emp_doc, "employee_earnings", []) if e.components != "Loan Amount"]
        emp_doc.employee_deductions = [d for d in getattr(emp_doc, "employee_deductions", []) if d.components != "Loan Repayment"]

        # Dealing with employee loan and deduction
        employee_loan_record = get_employee_loan(emp.name)
        
        loan_amount_earning = 0
        loan_repayment_deduction = 0

        if employee_loan_record:
            from datetime import datetime
            payslip_period_str = f"{month_name} {year}"
            
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
            frappe.log_error(f"Error saving employee {emp.name} during payroll: {e}")
            continue

        # Create new Payroll Entry
        payroll = frappe.new_doc("Havano Payroll Entry")
        payroll.first_name = emp_doc.first_name
        payroll.last_name = emp_doc.last_name
        payroll.payroll_period = f"{month_name} {year}"
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
            frappe.log_error(f"Payroll Calc Error for {emp.name}: {e}")
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
                        create_payroll_report(emp_doc.first_name,emp_doc.last_name, d.amount_zwg,0,d.amount_usd,0,f"{month_name} {year}",emp_doc.wcif_usd,emp_doc.wcif_zwg, nssa_rep_name)
                    except Exception as e:
                        frappe.log_error(f"NSSA Report Error for {emp.name}: {e}")
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
                            name=nec_rep_name
                        )
                    except Exception as e:
                        frappe.log_error(f"NEC Report Error for {emp.name}: {e}")

                payroll.append("employee_deductions", {
                    "components": d.components,
                    "item_code": d.item_code,
                    "amount_usd": d.amount_usd,
                    "amount_zwg": d.amount_zwg
                })

        payroll.insert(ignore_permissions=True)
        frappe.db.commit()

        # Generate Statutory Reports (ZIMRA, SDL)
        try:
            # Handle all currency modes (Base and Split)
            p4_name = f"NSSA-P4-{emp.name}-{month_name}-{year}"
            p2_name = f"ZIMRA-P2-{emp.name}-{month_name}-{year}"
            itf16_name = f"ZIMRA-ITF16-{emp.name}-{month_name}-{year}"
            sdl_name = f"SDL-{emp.name}-{month_name}-{year}"

            if emp_doc.salary_currency == "USD" or flt(emp_doc.total_income_usd) > 0:
                create_nssa_p4_report_store(surname=emp_doc.last_name, first_name=emp_doc.first_name, total_insuarable_earnings_zwg=0, total_insuarable_earnings_usd=emp_doc.total_taxable_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_taxable_income_usd, current_contributions_usd=nssa_usd, current_contributions_zwg=0, total_payment_usd=nssa_usd, total_payment_zwg=0, name=p4_name)
                create_zimra_p2form(employer_name="DPT", trade_name="DPT", tax_period=f"{month_name} {year}", total_renumeration=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_usd, gross_paye=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_usd, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_usd, total_tax_due=flt(emp_doc.aids_levy or 0) + flt(emp_doc.payee or 0) if emp_doc.payslip_type == "Base Currency" else flt(emp_doc.aids_levy_usd or 0) + flt(emp_doc.payee_usd or 0), currency="USD", name=p2_name)
                create_zimra_itf16(surname=emp_doc.last_name, first_name=emp_doc.first_name, employee_id=emp_doc.name, gross_paye=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_usd, payee=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_usd, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_usd, currency="USD", dob=emp_doc.date_of_birth, start_date=emp_doc.final_confirmation_date, end_date=emp_doc.contract_end_date, name=itf16_name)
                add_sdl_report(employee=emp_doc.name, date=f"{month_name} {year}", amount=flt(emp_doc.total_income) * 0.05, name=sdl_name)
            
            elif emp_doc.salary_currency in ["ZWL", "ZWG"] or flt(emp_doc.total_income_zwg) > 0:
                create_nssa_p4_report_store(surname=emp_doc.last_name, first_name=emp_doc.first_name, total_insuarable_earnings_zwg=emp_doc.total_taxable_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_taxable_income_zwg, total_insuarable_earnings_usd=0, current_contributions_usd=0, current_contributions_zwg=nssa_zwg, total_payment_usd=0, total_payment_zwg=nssa_zwg, name=p4_name)
                create_zimra_p2form(employer_name="DPT", trade_name="DPT", tax_period=f"{month_name} {year}", total_renumeration=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_zwg, gross_paye=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_zwg, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_zwg, total_tax_due=flt(emp_doc.aids_levy or 0) + flt(emp_doc.payee or 0) if emp_doc.payslip_type == "Base Currency" else flt(emp_doc.aids_levy_zwg or 0) + flt(emp_doc.payee_zwg or 0), currency="ZWG", name=p2_name)
                create_zimra_itf16(surname=emp_doc.last_name, first_name=emp_doc.first_name, employee_id=emp_doc.name, gross_paye=emp_doc.total_income if emp_doc.payslip_type == "Base Currency" else emp_doc.total_income_zwg, payee=emp_doc.payee if emp_doc.payslip_type == "Base Currency" else emp_doc.payee_zwg, aids_levy=emp_doc.aids_levy if emp_doc.payslip_type == "Base Currency" else emp_doc.aids_levy_zwg, currency="ZWG", dob=emp_doc.date_of_birth, start_date=emp_doc.final_confirmation_date, end_date=emp_doc.contract_end_date, name=itf16_name)
                add_sdl_report(employee=emp_doc.name, date=f"{month_name} {year}", amount=flt(emp_doc.total_income) * 0.05, name=sdl_name)
        except Exception as e:
            frappe.log_error(f"Statutory Report Error for {emp.name}: {e}")

        try:
            update_employee_annual_leave(emp.name, payroll_period=f"{month_name} {year}")
        except Exception as e:
            frappe.log_error(f"Error updating annual leave allocation for {emp.name}: {str(e)}", "Payroll Error")

        try:
            update_havano_leave_balances(emp.name)
        except Exception as e:
            frappe.log_error(f"Error updating leave balances for {emp.name}: {str(e)}", "Payroll Error")        
        # --- Journal Entry Aggregation ---
        if create_journal_entry and default_payable_account:
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
            pj_data[emp_company] = {"total_earnings": 0, "zimra": 0, "mapped": {}}
            
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
                if d.components in ["Payee", "Aids Levy"]:
                    zimra += amt
                elif d.components in mapped_components:
                    pj_data[emp_company]["mapped"][d.components] = pj_data[emp_company]["mapped"].get(d.components, 0) + amt
                
                # NSSA Employer Contribution match
                if d.components == "NSSA":
                    ecj_data[emp_company]["nssa"] += amt
                    
        pj_data[emp_company]["total_earnings"] += total_earnings
        pj_data[emp_company]["zimra"] += zimra
        
        frappe.db.commit()
    # Create Journal Entries
    if create_journal_entry and default_payable_account:
        for (comp, cur), data in je_data.items():
            if data["net_pay"] > 0:
                data["entries"].append({
                    "account": default_payable_account,
                    "debit": 0,
                    "credit": data["net_pay"],
                    "cost_center": setting_cost_center
                })
            if data["entries"]:
                create_journal_entry_safe(
                    company=comp,
                    posting_date=work_date or nowdate(),
                    entries=data["entries"],
                    voucher_type="Journal Entry"
                )

    if acc and not (create_journal_entry and default_payable_account):
        try:
            c = create_salary_purchase_invoice(
                item_name=acc.get("item", "Payroll Item"),
                supplier=acc.get("supplier"),
                company=acc.get("company"),
                cost_center=acc.get("cost_center"),
                total=total_net_salary_now,
                salary_account=acc.get("account"),
                currency=acc.get("currency", "USD"),
                expense_account=acc.get("account"),
                custom_from_payroll = 1,
                custom_payroll_period = f"{month_name} {year}"
            )
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Salary Purchase Invoice Creation Failed")
        
        try:
            c = create_salary_purchase_invoice(
                item_name="Payroll Expense",
                supplier=setting_supplier,
                company=acc.get("company"),
                cost_center=setting_cost_center,
                total=total_sdl,
                salary_account=acc.get("account"),
                currency=acc.get("currency", "USD"),
                expense_account=acc.get("account"),
                custom_payroll_period = f"{month_name} {year}",
                custom_from_payroll = 1
            )
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "SDL Purchase Invoice Creation Failed")
            
    # --- Auto-create Havano Payroll Journal ---
    for comp, data in pj_data.items():
        if data["total_earnings"] > 0:
            try:
                # Remove existing journal for the same period and company
                existing_pj = frappe.get_all("Havano Payroll Journal", filters={"payroll_period": f"{month_name} {year}", "company": comp})
                for pj_rec in existing_pj:
                    frappe.delete_doc("Havano Payroll Journal", pj_rec.name, ignore_permissions=True)
                    
                pj = frappe.new_doc("Havano Payroll Journal")
                pj.payroll_period = f"{month_name} {year}"
                pj.company = comp
                
                # Row 1: Salaries and Wages
                pj.append("journal_details", {
                    "detail": "Salaries and Wages",
                    "dr": data["total_earnings"],
                    "cr": 0
                })
                
                # Row 2: Mapped Deductions
                mapped_total = 0
                for k, v in data["mapped"].items():
                    if v > 0:
                        pj.append("journal_details", {
                            "detail": k,
                            "dr": 0,
                            "cr": v
                        })
                        mapped_total += v
                
                # Row 3: ZIMRA
                if data["zimra"] > 0:
                    pj.append("journal_details", {
                        "detail": "ZIMRA",
                        "dr": 0,
                        "cr": data["zimra"]
                    })
                    
                # Row 4: Payroll Payables
                payables = data["total_earnings"] - mapped_total - data["zimra"]
                pj.append("journal_details", {
                    "detail": "Payroll Payables",
                    "dr": 0,
                    "cr": payables
                })
                
                pj.insert(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint(f"Havano Payroll Journal created for {comp}", alert=True)
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Havano Payroll Journal Error for {comp}")
                frappe.msgprint(f"Failed to create Havano Payroll Journal for {comp}. Check Error Log.", indicator="red")

    # --- Auto-create Havano Employer Contributions Journal ---
    for comp, data in ecj_data.items():
        total_dr = data["nssa"] + data["medical_aid"] + data["funeral_policy"] + data["lapf"] + data["nec"]
        if total_dr > 0:
            try:
                # Remove existing journal for the same period and company
                existing_ecj = frappe.get_all("Havano Employer Contributions Journal", filters={"payroll_period": f"{month_name} {year}", "company": comp})
                for ecj_rec in existing_ecj:
                    frappe.delete_doc("Havano Employer Contributions Journal", ecj_rec.name, ignore_permissions=True)
                    
                ecj = frappe.new_doc("Havano Employer Contributions Journal")
                ecj.payroll_period = f"{month_name} {year}"
                ecj.company = comp
                
                # DR side
                ecj.append("journal_details", {
                    "detail": "Salaries and Wages",
                    "dr": total_dr,
                    "cr": 0
                })
                
                # CR side
                if data["nssa"] > 0:
                    ecj.append("journal_details", {"detail": "NSSA", "dr": 0, "cr": data["nssa"]})
                if data["medical_aid"] > 0:
                    ecj.append("journal_details", {"detail": "Medical Aid", "dr": 0, "cr": data["medical_aid"]})
                if data["funeral_policy"] > 0:
                    ecj.append("journal_details", {"detail": "Funeral Policy", "dr": 0, "cr": data["funeral_policy"]})
                if data["lapf"] > 0:
                    ecj.append("journal_details", {"detail": "LAPF", "dr": 0, "cr": data["lapf"]})
                if data["nec"] > 0:
                    ecj.append("journal_details", {"detail": "NEC", "dr": 0, "cr": data["nec"]})
                    
                ecj.insert(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint(f"Employer Contributions Journal created for {comp}", alert=True)
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Employer Contributions Journal Error for {comp}")
                frappe.msgprint(f"Failed to create Employer Contributions Journal for {comp}. Check Error Log.", indicator="red")
    
    return f"Payroll created for {len(employees)} employees for {month_name} {year}."



def create_journal_entry_safe(company, posting_date, entries, voucher_type="Cash Entry"):
    """
    Create a Journal Entry in ERPNext safely.
    'entries' must be a list of dicts with keys: account, debit, credit, cost_center (optional)
    """
    import frappe
    from frappe.utils import flt

    try:
        # Prepare rows
        accounts = []
        for e in entries:
            accounts.append({
                "account": e.get("account"),
                "debit": flt(e.get("debit", 0)),
                "credit": flt(e.get("credit", 0)),
                "cost_center": e.get("cost_center")  # optional
            })

        je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": voucher_type,
            "company": company,
            "posting_date": posting_date,
            "accounts": accounts
        })
        je.insert()
        je.submit()

        frappe.msgprint(f"Journal Entry Created: {je.name}")
        return je

    except Exception:
        import traceback
        tb = traceback.format_exc()
        frappe.log_error(message=tb, title="Journal Entry Creation Error")
        frappe.msgprint("Failed to create Journal Entry. Check Error Log.")
        return None

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
def add_sdl_report(employee=None,date=None, amount=None, name=None):
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
        "amount": amount
    })
    if name:
        doc.name = name
    doc.insert(ignore_permissions=True)
    frappe.db.commit()  # optional, forces immediate save

    return f"SDL Report created: {doc.name}"

@frappe.whitelist()
def create_salary_purchase_invoice(
    item_name, supplier, company, cost_center, total,
    salary_account, currency=None, expense_account=None,
    salary_component=None, period=None, custom_from_payroll = None,custom_payroll_period =None
):

    currency = currency or frappe.get_cached_value("Company", company, "default_currency")

    # Create Purchase Invoice
    purchase_invoice = frappe.new_doc("Purchase Invoice")
    purchase_invoice.update({
        "supplier": supplier,
        "company": company,
        "currency": currency,
        "cost_center": cost_center,
        "bill_no": f"Salary-Run-{period or 'NA'}-{salary_component or item_name}",
        "bill_date": nowdate(),
        "due_date": nowdate(),
        "items": [],
        "custom_from_payroll": 1,
        "custom_payroll_period": custom_payroll_period
    })

    item = {
        "item_code": item_name,
        "item_name": item_name,
        "description": f"{salary_component or item_name} - {period or 'NA'}",
        "qty": 1,
        "rate": total,
        "amount": total,
        "cost_center": cost_center,
        "expense_account": expense_account or salary_account
    }
    purchase_invoice.append("items", item)

    # Auto-set missing values + calculate totals
    purchase_invoice.run_method("set_missing_values")
    purchase_invoice.run_method("calculate_taxes_and_totals")

    # Save + submit
    purchase_invoice.insert(ignore_permissions=True)
    purchase_invoice.submit()
    return purchase_invoice.name


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
                
                frappe.log_error(f"Updated Annual Leave for {emp.name}: {current_balance} -> {new_balance}", "Leave Update")
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
            frappe.log_error(f"Created new {actual_leave_type} for {emp.name} with balance {balance}", "Leave Update")
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
        frappe.log_error(frappe.get_traceback(), "ZIMRA ITF16 Creation Failed")
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
            "currency": currency
        })
        if name:
            doc.name = name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "name": doc.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "ZIMRA P2FORM Creation Failed")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def create_nssa_p4_report_store(
    surname=None,
    first_name=None,
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
    name=None
):
    """Create a new record in NSSA P4 Report Store"""
    try:
        doc = frappe.get_doc({
            "doctype": "NSSA P4 Report Store",
            "surname": surname,
            "first_name": first_name,
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
            "total_nec_usd": total_nec_usd
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
                frappe.log_error(f"Error reversing leave for {emp} during cancel: {str(e)}", "Leave Reversal Error")

    # Call period-wide deletes once outside the loop
    payroll_period_str = f"{month} {int(year)}"
    cancel_payroll_purchase_invoices(payroll_period_str)
    delete_sdl_for_period(payroll_period_str)
    delete_nassa_reports_for_period(payroll_period_str)
    delete_salary_summary_for_period(payroll_period_str)
    delete_havano_payroll_entries(payroll_period_str)

    return f"{len(payroll_entries)} payroll entries for {month} {year} with reason: {reason}."

def reverse_leave_for_employee(employee, days_to_deduct=2.5):
    # 1. Deduct from Annual Leave Allocation
    allocation = frappe.db.get_value("Havano Annual Leave Allocation", {"employee": employee}, "name")
    if allocation:
        current_alloc = flt(frappe.db.get_value("Havano Annual Leave Allocation", allocation, "total_days") or 0)
        frappe.db.set_value("Havano Annual Leave Allocation", allocation, "total_days", current_alloc - days_to_deduct)

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
