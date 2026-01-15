import frappe
from frappe.utils import nowdate, flt
from datetime import date
import calendar
from frappe import error_log
frappe.error_log = error_log


@frappe.whitelist()
def run_payroll_async(month, year):
    """
    Enqueue payroll in background and return job info.
    """
    job = frappe.enqueue(
        "havano_zim_payroll.api.run_payroll",  # your payroll function path
        month=month,
        year=year,
        queue="long",
        timeout=15000
    )

    # Return only simple data — avoid returning the Job object itself
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
def run_payroll(month, year):
    settin=get_payroll_settings()
    setting_cost_center=settin["cost_center"]
    setting_supplier=settin["supplier"]
    """Runs payroll for all employees immediately (synchronous)."""
    employees = frappe.get_all("havano_employee", fields=["name", "first_name", "last_name","net_income"])
    if not employees:
        return "No employees found."
    total_net_salary_now=0
    total_sdl=0
    total_loan = 0
    for emp in employees:
        emp_doc = frappe.get_doc("havano_employee", emp.name)
        # dealing with employee basic salary based on hours worked
        total_hours=get_employee_hours(emp.name, year, month)
        if total_hours > 0:
            caculated_basic = emp_doc.hourly_rate* total_hours
            add_basic_hourly(emp.name,caculated_basic)
            emp_doc.reload()
            frappe.log_error(f"Employee: {emp.name}, Hours Worked: {total_hours}", "Payroll Hours Worked Log")
        # Dealing with employee loan and deduction
        employee_loan_record = get_employee_loan(emp['name'])

        if employee_loan_record:
            # Get monthly deduction safely
            monthly_amount_to_be_paid = getattr(employee_loan_record, "monthly_amount_to_be_paid", 0)
            
            # Update loan fields
            employee_loan_record.loan_paid = (getattr(employee_loan_record, "loan_paid", 0) or 0) + monthly_amount_to_be_paid
            employee_loan_record.current_loan_balance = (getattr(employee_loan_record, "current_loan_balance", 0) or 0) - monthly_amount_to_be_paid
            
            # Save changes
            employee_loan_record.save(ignore_permissions=True)
            
            # Log the deduction
            frappe.log_error(
                message=f"Employee: {emp['name']}, Monthly Loan Deduction: {monthly_amount_to_be_paid}, Loan Paid: {employee_loan_record.loan_paid}, Current Balance: {employee_loan_record.current_loan_balance}",
                title="Payroll Monthly Loan Update"
            )


        # Create new Payroll Entry
        payroll = frappe.new_doc("Havano Payroll Entry")
        payroll.first_name = emp_doc.first_name
        payroll.surname = emp_doc.last_name
        payroll.payroll_period = f"{month} {year}"
        nssa_usd=0
        nssa_zwg=0
        try:
            loan_deduction_add_back = get_loan_deduction_amounts(emp.name)
            emp_netpay = emp.net_income
            total_net_salary_now += emp_doc.net_income + loan_deduction_add_back["amount_usd"]
            total_loan += loan_deduction_add_back["amount_usd"]
            total_sdl +=emp_doc.total_income * 0.01
        except AttributeError as e:
            print(f"Net income not found for employee {emp.employee}: {e}")
            frappe.log_error(f"{e}")

        # Copy Earnings
        if hasattr(emp_doc, "employee_earnings"):
            for e in emp_doc.employee_earnings:

                if e.components == "Backpay":
                    emp_netpay -=e.amount_usd
                payroll.append("employee_earnings", {
                    "components": e.components,
                    "item_code": e.item_code,
                    "amount_usd": e.amount_usd,
                    "amount_zwg": e.amount_zwg
                })

        print(f"---------------------rrrr----{emp_netpay}")
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
            ledger_doc.current_balance_owing = (ledger["current_balance_owing"] or 0) + emp_netpay
            ledger_doc.save(ignore_permissions=True)

        # Copy Deductions
        if hasattr(emp_doc, "employee_deductions"):
            for d in emp_doc.employee_deductions:
                if d.components == "NSSA":
                    print("------------------------------------nssa--------------------")
                    a=create_payroll_report(emp_doc.first_name,emp_doc.last_name, d.amount_zwg,0,d.amount_usd,0,f"{month} {year}",emp_doc.wcif_usd,emp_doc.wcif_zwg)
                    nssa_usd = d.amount_usd
                    nssa_zwg = d.amount_zwg
                payroll.append("employee_deductions", {
                    "components": d.components,
                    "item_code": d.item_code,
                    "amount_usd": d.amount_usd,
                    "amount_zwg": d.amount_zwg
                })

        payroll.insert(ignore_permissions=True)
        frappe.db.commit()
       # Get Basic Salary Component parent doc
        comp = get_basic_salary_component()

        # Extract child table row (accounts)
       
        update_havano_leave_balances(emp.name)
        a=update_employee_annual_leave(emp.name,payroll_period=f"{month} {year}")
        frappe.db.set_value("havano_employee", emp.name, "total_leave_allocated", a)
        frappe.db.commit()
        
        bb=""
        if emp_doc.salary_currency == "USD" and emp_doc.payslip_type =="Base Currency":
            create_nssa_p4_report_store(surname=emp_doc.last_name,first_name=emp_doc.first_name,total_insuarable_earnings_zwg=0,total_insuarable_earnings_usd=emp_doc.total_taxable_income, current_contributions_usd=nssa_usd,current_contributions_zwg=0,total_payment_usd=nssa_usd,total_payment_zwg=0)
            create_zimra_p2form(employer_name="DPT",trade_name="DPT",tax_period=f"{month} {year}",total_renumeration=emp_doc.total_income,gross_paye=emp_doc.payee,aids_levy=emp_doc.aids_levy,total_tax_due = float(emp_doc.aids_levy or 0) + float(emp_doc.payee or 0),currency="USD")
            create_zimra_itf16(surname=emp_doc.last_name,first_name=emp_doc.first_name,employee_id=emp_doc.name,gross_paye=emp_doc.total_income,payee=emp_doc.payee,aids_levy=emp_doc.aids_levy,currency="USD",dob=emp_doc.date_of_birth,start_date=emp_doc.final_confirmation_date,end_date=emp_doc.contract_end_date)
            bb=add_sdl_report(employee=emp_doc.name,date=f"{month} {year}",amount=emp_doc.total_income * 0.1)
        elif  emp_doc.salary_currency == "ZWL" and emp_doc.payslip_type =="Base Currency":
            create_nssa_p4_report_store(surname=emp_doc.last_name,first_name=emp_doc.first_name,total_insuarable_earnings_zwg=emp_doc.total_taxable_income,total_insuarable_earnings_usd=0, current_contributions_usd=0,current_contributions_zwg=nssa_zwg,total_payment_usd=nssa_usd,total_payment_zwg=nssa_zwg)
            create_zimra_p2form(employer_name="DPT",trade_name="DPT",tax_period=f"{month} {year}",total_renumeration=emp_doc.total_income,gross_paye=emp_doc.payee,aids_levy=emp_doc.aids_levy,total_tax_due = float(emp_doc.aids_levy or 0) + float(emp_doc.payee or 0),currency="ZWG")
            create_zimra_itf16(surname=emp_doc.last_name,first_name=emp_doc.first_name,employee_id=emp_doc.name,gross_paye=emp_doc.total_income,payee=emp_doc.payee,aids_levy=emp_doc.aids_levy,currency="ZWG",dob=emp_doc.date_of_birth,start_date=emp_doc.final_confirmation_date,end_date=emp_doc.contract_end_date)
        print(bb)

        acc = get_basic_salary_component()[0]


    # try:
    #     # Get the account (assuming get_basic_salary_component returns a list)
        

    #     entries = [
    #     {"account": "Administrative Expenses - AA a@a6326", "debit": 70.0, "credit": "70.0", "cost_center": "Aa Fridays - AA a@a6326"},
    #     {"account": "Cash - AA a@a6326", "debit": 70.0, "credit": 70.0, "cost_center": "Aa Fridays - AA a@a6326"}
    #         ]

    #     je_doc = create_journal_entry_safe(
    #         company="Aa Fridays",
    #         posting_date="2026-01-07",
    #         entries=entries,
    #         voucher_type="Cash Entry"
    #     )


    # except Exception as e:
    #     # Log the error in Frappe Error Log
    #     frappe.log_error(message=str(e), title="Journal Entry Creation Error")



    try:
        # PURCHASE Invoice for all employees net salaries

        c = create_salary_purchase_invoice(
            item_name=acc["item"],
            supplier=acc["supplier"],
            company=acc["company"],
            cost_center=acc["cost_center"],
            total=total_net_salary_now,
            salary_account=acc["account"],
            currency=acc["currency"],
            expense_account=acc["account"],
            custom_from_payroll = 1,
            custom_payroll_period = f"{month} {year}"
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Salary Purchase Invoice Creation Failed")
    
    try:
    # SDL Invoice for all employees net salaries
        c = create_salary_purchase_invoice(
            item_name="Payroll Expense",
            supplier=setting_supplier,
            company=acc["company"],
            cost_center=setting_cost_center,
            total=total_sdl,
            salary_account=acc["account"],
            currency=acc["currency"],
            expense_account=acc["account"],
            custom_payroll_period = f"{month} {year}",
            custom_from_payroll = 1
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "SDL Purchase Invoice Creation Failed")

        return f"Error creating Salary Purchase Invoice: {str(e)}"

    return f"Payroll created for {len(employees)} employees for {month} {year}."



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
def add_sdl_report(employee=None,date=None, amount=None):
    """
    Adds an SDL Report record if one for the same employee and date doesn't exist.
    
    Args:
        employee (str): Employee ID
        employee_name (str): Employee full name
        date (str): Month-Year format, e.g., "June 2026"
        amount (float): SDL amount
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
        {"employee": emp.name},
        ["name", "total_days"],
        as_dict=True
    )

    if existing_allocation:
        # Add to total_days
        new_total = (existing_allocation["total_days"] or 0) + float(days_to_add)
        frappe.db.set_value("Havano Annual Leave Allocation", existing_allocation["name"], "total_days", new_total)
        frappe.db.commit()
        return new_total
    else:
        # Create new record
        new_doc = frappe.get_doc({
            "doctype": "Havano Annual Leave Allocation",
            "employee": emp.name,
            "havano_employee": emp.employee_name,
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
        "cost_center": settings.cost_center
    }

@frappe.whitelist()
def update_havano_leave_balances(employee):
    """
    Ensures all standard leave types exist for the employee in 'Havano Leave Balances'.
    If a type exists, skip it — except 'Annual Leave', which always increases by 2.5 days.
    """

    # Define the default leave types and their default balances
    default_leave_types = {
        "Annual Leave": 2.5,
        "Study Leave": 10.0,
        "Special Leave": 12.0,
        "Bereavement Leave": 12.0,
        "Sick Leave": 90.0,
        "Maternity Leave": 90.0
    }

    # Get employee details
    emp = frappe.get_doc("havano_employee", employee)

    # Loop over each leave type
    for leave_type, balance in default_leave_types.items():
        existing_record = frappe.db.get_value(
            "Havano Leave Balances",
            {"employee": emp.name, "havano_leave_type": leave_type},
            "name"
        )

        if existing_record:
            # If it already exists, only modify Annual Leave
            if leave_type == "Annual Leave":
                leave_doc = frappe.get_doc("Havano Leave Balances", existing_record)
                leave_doc.leave_balance = (leave_doc.leave_balance or 0) + 2.5
                leave_doc.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.logger().info(f"Added 2.5 days to Annual Leave for {emp.name}")
            else:
                frappe.logger().info(f"{leave_type} already exists for {emp.name}, skipped.")
        else:
            # Create new leave record
            new_doc = frappe.get_doc({
                "doctype": "Havano Leave Balances",
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "havano_leave_type": leave_type,
                "leave_balance": balance
            })
            new_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"Created {leave_type} for {emp.name}")

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
    currency=None
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
    currency=None
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
    prepayments_zwg_column=None
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
    wcif_zwg
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

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": f"Payroll Summary created for {first_name} {surname}"}

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Payroll Summary Creation Failed")
        return {"status": "error", "message": str(e)}


from frappe.utils.pdf import get_pdf
import frappe
import os
import frappe
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
        fields=["name","first_name"]
    )

    if not payroll_entries:
        return f"No submitted payroll found for {month} {year}."

    # Print entries to the server log
    for entry in payroll_entries:
        print(f"Payroll: {entry['name']}, Employee: {entry['first_name']},Reason: {reason}")
        cancel_payroll_purchase_invoices(f"{month} {int(year)}")
        delete_sdl_for_period(f"{month} {int(year)}")
        delete_nassa_reports_for_period(f"{month} {int(year)}")
        delete_salary_summary_for_period(f"{month} {int(year)}")
        delete_havano_payroll_entries(f"{month} {int(year)}")

    return f"{len(payroll_entries)} payroll entries for {month} {year} with reason: {reason}."

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

