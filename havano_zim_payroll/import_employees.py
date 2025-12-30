import frappe
import csv
from frappe.utils import getdate,flt


@frappe.whitelist()
def import_employees(file_url):
    """
    Enqueue payroll in background and return job info.
    """
    job = frappe.enqueue(
        "havano_zim_payroll.import_employees.employees_import",
        file_url=file_url,
        queue="long",
        timeout=15000
    )

    # Return only simple data — avoid returning the Job object itself
    return {
        "message": f"Employee import job queued",
        "job_id": job.id
    }
@frappe.whitelist()
def employees_import(file_url):
    """
    Import employees with salary components.
    CSV columns:
        ID, First Name, Last Name, Gender, Date of Birth, Date of Joining, Status, Company,
        Salary Mode, Employee Number, Mobile, Offer Date, Confirmation Date, Bank Name,
        Payment Account, Payroll Frequency, Salary Currency, BankAccountNo.,
        <Salary Components starting from Basic Salary>
    """

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path() 

    imported = 0
    errors = []

    # Get all salary components from DB
    components = frappe.get_all("havano_salary_component", fields=["name", "type"])
    type_map = {c["name"]: c["type"] for c in components}
    with open(file_path, newline='', encoding='latin-1') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Normalize headers
        reader.fieldnames = [fn.strip().replace('\ufeff','') for fn in reader.fieldnames]
        
        # Optional: create a map for flexible lookup
        header_map = {fn.strip().lower().replace(' ', ''): fn for fn in reader.fieldnames}

        for idx, row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v for k, v in row.items()}
                
                # Flexible lookup
                first_name = row.get(header_map.get("firstname")) or row.get(header_map.get("first"))
                last_name = row.get(header_map.get("lastname")) or row.get(header_map.get("last"))

                if not first_name:
                    raise ValueError("Missing First Name or Employee ID")
                

                # Skip if employee exists
                emp_exists = frappe.db.exists("havano_employee", {"first_name": first_name, "last_name": last_name})
                if emp_exists:
                    continue

                # Create employee
                emp_doc = frappe.get_doc({
                    "doctype": "havano_employee",
                    "first_name": first_name,
                    "last_name": last_name,
                    "gender": row.get("Gender"),
                    "date_of_birth": getdate(row.get("Date of Birth")) if row.get("Date of Birth") else None,
                    "date_of_joining": getdate(row.get("Date of Joining")) if row.get("Date of Joining") else None,
                    "status": row.get("Status"),
                    "company": row.get("Company"),
                    "salary_mode": row.get("Salary Mode"),
                    "mobile": row.get("Mobile"),
                    "bank_name": row.get("Bank Name"),
                    "payment_account": row.get("Payment Account"),
                    "payroll_frequency": row.get("Payroll Frequency"),
                    "salary_currency": row.get("Salary Currency"),
                    "bank_ac_no": row.get("BankAccountNo"),
                    "total_days_worked":26
                })

                                # # Add salary components to child tables-----------------------------

              
                                # Columns that are NOT salary components
                NON_COMPONENT_COLUMNS = {
                    "ID", "First Name", "Last Name", "Gender",
                    "Date of Birth", "Date of Joining", "Status", "Company",
                    "Salary Mode", "Employee Number", "Mobile",
                    "Offer Date", "Confirmation Date",
                    "Bank Name", "Payment Account",
                    "Payroll Frequency", "Salary Currency", "BankAccountNo","Employee"
                }

                for column, value in row.items():
                    print(f"Processing column: {column} with value: {value}")
                    # Skip non-component columns
                    if column in NON_COMPONENT_COLUMNS:
                        continue

                    # Skip empty values
                    if not value or not str(value).strip():
                        continue

                    component_name = column.strip()
                    component_type = type_map.get(component_name)

                    # Component not found in havano_salary_component
                    if not component_type:
                        frappe.log_error(
                            f"Unknown salary component in CSV: {component_name}",
                            "Employee CSV Import"
                        )
                        continue
                    amount = flt(value)

                    # Route to correct child table
                    if component_type.lower() == "earning":
                        emp_doc.append("employee_earnings", {
                            "components": component_name,
                            "is_tax_applicable" : 1 if component_name.lower() == "basic salary" else 0,
                            "amount_usd": amount
                        })

                    elif component_type.lower() == "deduction":
                        emp_doc.append("employee_deductions", {
                            "components": component_name,
                            "amount_usd": amount
                        })

                emp_doc.insert(ignore_permissions=True)
                frappe.log_error(
                    f"Employee {first_name} {last_name} imported successfully.",
                    "Employee CSV Import"
                )
                imported += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

    msg = f"{imported} employees imported successfully."
    if errors:
        msg += "\n\nErrors:\n" + "\n".join(errors)
    return msg
