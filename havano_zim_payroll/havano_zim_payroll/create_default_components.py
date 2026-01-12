import frappe
from frappe import defaults


@frappe.whitelist(allow_guest=True)
def create_salary_components():

    components = [
        # {
        #     "name": "Loan Repayment",
        #     "type": "Earning",
        #     "code": "LR",
        #     "component_mode": "",
        #     "is_tax_applicable": 0,
        #     "employee_percentage": 0,
        #     "employer_percentage": 0,
        #     "usd_ceiling": 0,
        #     "zwg_ceiling_amount": 0,
        #     "accounts": [
        #         {
        #             "account": "Loan Intrest - ",
        #             "item": "Payroll Expense",
        #             "supplier": "Winfiled 7"
        #         }
        #     ]
        # },
        {
            "name": "PAYEE",
            "type": "Deduction",
            "code": "PY",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Payee",
                    "item": "Payroll Expense",
                    "supplier": "ZIMRA"
                }
            ]
        },
        {
            "name": "Aids Levy",
            "type": "Deduction",
            "code": "AL",
            "component_mode": "",
            "is_tax_applicable": 1,
            "accounts": [
                {
                    "account": "Aids Levy",
                    "item": "Payroll Expense",
                    "supplier": "ZIMRA"
                }
            ]
        },
        {
            "name": "Overtime Short",
            "type": "Earning",
            "code": "OS",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries-Overtime-Finishing",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Basic Salary",
            "type": "Earning",
            "code": "BS",
            "component_mode": "daily rate",
            "is_tax_applicable": 1,
            "accounts": [
                {
                    "account": "Salaries & Wages",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
              {
            "name": "NSSA",
            "type": "Deduction",
            "code": "NS",
            "component_mode": "",
            "is_tax_applicable": 0,
            "employee_percentage": 0,
            "employer_percentage": 0,
            "usd_ceiling": 700,
            "zwg_ceiling_amount": 225.49,
            "accounts": [
                {
                    "account": "Nssa",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Data Deduc",
            "type": "Deduction",
            "code": "DD",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Airtime & Data_Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Overtime Double",
            "type": "Earning",
            "code": "OD",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Airtime & Data_Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "LAPF",
            "type": "Deduction",
            "code": "LF",
            "component_mode": "",
            "is_tax_applicable": 0,
            "employee_percentage": 6,
            "employer_percentage": 17.3,
            "accounts": [
                {
                    "account": "LAPF",
                    "item": "Payroll Expense",
                    "supplier": "LAPF"
                }
            ]
        },
        {
            "name": "Data Non Tax",
            "type": "Earning",
            "code": "DNT",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Airtime & Data_Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Airtime Data",
            "type": "Earning",
            "code": "AD",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Airtime & Data_Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
                {
            "name": "Acting Allowance",
            "type": "Earning",
            "code": "AA",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Acting Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Fuel",
            "type": "Earning",
            "code": "FL",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Fuel & Mileage_Allowance",
                    "item": "FUEL EXPENSE",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Airtime Non-taxed",
            "type": "Earning",
            "code": "AN",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Airtime & Data_Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Housing Allowance",
            "type": "Earning",
            "code": "HA",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Housing Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "cash in lieu of leave",
            "type": "Earning",
            "code": "CLL",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Cash in Lieu of Leave",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "Fuel Deduc",
            "type": "Deduction",
            "code": "FD",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Fuel & Mileage_Allowance",
                    "item": "FUEL EXPENSE",
                    "supplier": "Fuel"
                }
            ]
        },
        {
            "name": "UFAWUZ",
            "type": "Deduction",
            "code": "UFAWUZ",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "UFAWUZ",
                    "item": "Payroll Expense",
                    "supplier": "UFAWUZ"
                }
            ]
        },
        {
            "name": "Funeral Policy",
            "type": "Deduction",
            "code": "FP",
            "component_mode": "allowable_deduction",
            "is_tax_applicable": 0,
            "employee_percentage": 25,
            "employer_percentage": 75,
            "accounts": [
                {
                    "account": "Salaries_Funeral",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
            "name": "ZiBAWU",
            "type": "Deduction",
            "code": "ZB",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "ZiBAWU",
                    "item": "Payroll Expense",
                    "supplier": "ZiBAWU"
                }
            ]
        },
        {
            "name": "Airtime Deduc",
            "type": "Deduction",
            "code": "AD",
            "component_mode": "",
            "is_tax_applicable": 0,
            "accounts": [
                {
                    "account": "Salaries_Airtime & Data_Allowance",
                    "item": "Payroll Expense",
                    "supplier": "Employees"
                }
            ]
        },
        {
        "name": "SDL",
        "type": "Deduction",
        "code": "SDL",
        "component_mode": "",
        "is_tax_applicable": 0,
        "accounts": [
            {
                "account": "",
                "item": "Payroll Expense",
                "supplier": "SDL"
            }
            ]
        },
        {
        "name": "ZESCWU",
        "type": "Deduction",
        "code": "ZESCWU",
        "component_mode": "allowable_deduction",
        "is_tax_applicable": 0,
        "accounts": [
            {
                "account": "",
                "item": "Payroll Expense",
                "supplier": "ZESCWU"
            }
            ]
        },
        {
        "name": "NECWEI",
        "type": "Deduction",
        "code": "NECWEI",
        "component_mode": "allowable_deduction",
        "is_tax_applicable": 0,
        "accounts": [
            {
                "account": "",
                "item": "Payroll Expense",
                "supplier": "NECWEI"
            }
            ]
        },
         {
        "name": "Loan Repayment",
        "type": "Deduction",
        "code": "LR",
        "component_mode": "",
        "is_tax_applicable": 0,
        "accounts": [
            {
                "account": "",
                "item": "Payroll Expense",
                "supplier": "Employees"
            }
            ]
        },
        {
        "name": "Loan Interest",
        "type": "Earning",
        "code": "LI",
        "component_mode": "",
        "is_tax_applicable": 0,
        "accounts": [
            {
                "account": "",
                "item": "Payroll Expense",
                "supplier": "Employees"
            }
            ]
        },
        {
        "name": "CIMAS",
        "type": "Deduction",
        "code": "CIMAS",
        "component_mode": "",
        "is_tax_applicable": 0,
        "accounts": [
            {
                "account": "",
                "item": "Payroll Expense",
                "supplier": "Employees"
            }
            ]
        }

    ]
    company = defaults.get_defaults().get("company")
    if not company:
        frappe.throw("Default company not set in site defaults.")

    for comp in components:
        if not frappe.db.exists("havano_salary_component", comp["name"]):

            # Create parent doc
            doc = frappe.new_doc("havano_salary_component")
            doc.salary_component = comp["name"]
            doc.type = comp["type"]
            doc.code = comp["code"]
            doc.component_mode = comp.get("component_mode", "")
            doc.is_tax_applicable = comp.get("is_tax_applicable", 0)
            doc.employee_percentage = comp.get("employee_percentage", 0)
            doc.employer_percentage = comp.get("employer_percentage", 0)
            doc.usd_ceiling = comp.get("usd_ceiling", 0)
            doc.zwg_ceiling_amount = comp.get("zwg_ceiling_amount", 0)

            # Add ONE child row (this is correct)
            acc = comp["accounts"][0]      # first row only
            doc.append("accounts", {        # child table fieldname = account
                "account": get_account(acc["account"]),
                "company": acc.get("company", company),
                "item": get_item_code(acc["item"]),
                "supplier": acc.get("supplier"),
                "cost_center": acc.get("cost_center", get_cost_center()),
            })

            # Insert parent (automatically inserts child table too)
            doc.insert()
            frappe.db.commit()

            print(f"Created Salary Component: {comp['name']}")

        else:
            print(f"Salary Component already exists: {comp['name']}")

def get_account(prefix):
    accounts = frappe.db.get_all(
        "Account",
        filters={"account_name": ["like", f"{prefix}%"]},
        pluck="name"
    )
    print(f"---------account {accounts}-------------")

    # return first match, even if there are multiple
    return accounts[0] if accounts else None

def get_item_code(name):
    item = frappe.db.get_value(
        "Item",
        {"item_name": name},
        "item_code"
    )
    return item

def get_cost_center(prefix="Main"):
    company = defaults.get_defaults().get("company")
    if not company:
        frappe.throw("Default company not set in site defaults.")
    
    filters = {"cost_center_name": ["like", f"{prefix}%"]}
    
    if company:
        filters["company"] = company

    cost_centers = frappe.db.get_all(
        "Cost Center",
        filters=filters,
        pluck="name"
    )
    
    print(f"---------cost center {cost_centers}-------------")

    # return the first match only
    return cost_centers[0] if cost_centers else None

