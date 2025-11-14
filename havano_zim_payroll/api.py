import frappe

@frappe.whitelist()
def run_payroll(month, year):
    """Runs payroll for all employees immediately (synchronous)."""
    employees = frappe.get_all("havano_employee", fields=["name", "first_name", "last_name","net_income"])

    if not employees:
        return "No employees found."

    for emp in employees:
        emp_doc = frappe.get_doc("havano_employee", emp.name)
        # Create new Payroll Entry
        payroll = frappe.new_doc("Havano Payroll Entry")
        payroll.first_name = emp_doc.first_name
        payroll.surname = emp_doc.last_name
        payroll.payroll_period = f"{month} {year}"
        nssa_usd=0
        nssa_zwg=0
        try:
            emp_netpay = emp.net_income
        except AttributeError as e:
            print(f"Net income not found for employee {emp.employee}: {e}")


        # Copy Earnings
        if hasattr(emp_doc, "employee_earnings"):
            for e in emp_doc.employee_earnings:

                if e.components == "Backpay":
                    emp_netpay -=e.amount_usd

                    print("--------0000000000000000000000000000")
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
        update_havano_leave_balances(emp.name)
        a=update_employee_annual_leave(emp.name,payroll_period=f"{month} {year}")
        frappe.db.set_value("havano_employee", emp.name, "total_leave_allocated", a)
        frappe.db.commit()
        
        print(f"----------------leave allocation {a}")
        if emp_doc.salary_currency == "USD" and emp_doc.payslip_type =="Base Currency":
            create_nssa_p4_report_store(surname=emp_doc.last_name,first_name=emp_doc.first_name,total_insuarable_earnings_zwg=0,total_insuarable_earnings_usd=emp_doc.total_taxable_income, current_contributions_usd=nssa_usd,current_contributions_zwg=0,total_payment_usd=nssa_usd,total_payment_zwg=0)
            create_zimra_p2form(employer_name="DPT",trade_name="DPT",tax_period=f"{month} {year}",total_renumeration=emp_doc.total_income,gross_paye=emp_doc.payee,aids_levy=emp_doc.aids_levy,total_tax_due = float(emp_doc.aids_levy or 0) + float(emp_doc.payee or 0),currency="USD")
            a=create_zimra_itf16(surname=emp_doc.last_name,first_name=emp_doc.first_name,employee_id=emp_doc.name,gross_paye=emp_doc.total_income,payee=emp_doc.payee,aids_levy=emp_doc.aids_levy,currency="USD",dob=emp_doc.date_of_birth,start_date=emp_doc.final_confirmation_date,end_date=emp_doc.contract_end_date)
        elif  emp_doc.salary_currency == "ZWL" and emp_doc.payslip_type =="Base Currency":
            create_nssa_p4_report_store(surname=emp_doc.last_name,first_name=emp_doc.first_name,total_insuarable_earnings_zwg=emp_doc.total_taxable_income,total_insuarable_earnings_usd=0, current_contributions_usd=0,current_contributions_zwg=nssa_zwg,total_payment_usd=nssa_usd,total_payment_zwg=nssa_zwg)
            create_zimra_p2form(employer_name="DPT",trade_name="DPT",tax_period=f"{month} {year}",total_renumeration=emp_doc.total_income,gross_paye=emp_doc.payee,aids_levy=emp_doc.aids_levy,total_tax_due = float(emp_doc.aids_levy or 0) + float(emp_doc.payee or 0),currency="ZWG")
            a=create_zimra_itf16(surname=emp_doc.last_name,first_name=emp_doc.first_name,employee_id=emp_doc.name,gross_paye=emp_doc.total_income,payee=emp_doc.payee,aids_levy=emp_doc.aids_levy,currency="ZWG",dob=emp_doc.date_of_birth,start_date=emp_doc.final_confirmation_date,end_date=emp_doc.contract_end_date)

    return f"Payroll created for {len(employees)} employees for {month} {year}."



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
    """Create a new ZIMRA ITF16 document"""
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
