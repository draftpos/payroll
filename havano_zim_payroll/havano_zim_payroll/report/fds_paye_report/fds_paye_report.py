import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    columns = [
        {"label": _("First Name"), "fieldname": "first_name", "fieldtype": "Data", "width": 120},
        {"label": _("Surname"), "fieldname": "last_name", "fieldtype": "Data", "width": 120},
    ]
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i, month in enumerate(months):
        columns.append({"label": _(f"{month} PAYE (USD)"), "fieldname": f"month_{i+1}_usd", "fieldtype": "Currency", "width": 130})
        columns.append({"label": _(f"{month} PAYE (ZWG)"), "fieldname": f"month_{i+1}_zwg", "fieldtype": "Currency", "width": 130})
        
    columns.append({"label": _("YTD PAYE (USD)"), "fieldname": "ytd_usd", "fieldtype": "Currency", "width": 140})
    columns.append({"label": _("YTD PAYE (ZWG)"), "fieldname": "ytd_zwg", "fieldtype": "Currency", "width": 140})
    
    return columns

def get_data(filters):
    year = filters.get("year")
    if not year:
        year = frappe.utils.nowdate()[:4]
        
    conditions = "YEAR(pe.date) = %s AND ded.components = 'PAYEE'"
    values = [year]
    
    # We query from the child table `tabhavano_payroll_earnings` which stores deductions for `Havano Payroll Entry`
    query = f"""
        SELECT 
            pe.first_name, 
            pe.last_name, 
            MONTH(pe.date) as month_num,
            SUM(ded.amount_usd) as paye_usd,
            SUM(ded.amount_zwg) as paye_zwg
        FROM `tabHavano Payroll Entry` pe
        JOIN `tabhavano_payroll_earnings` ded 
            ON ded.parent = pe.name AND ded.parentfield = 'employee_deductions' AND ded.parenttype = 'Havano Payroll Entry'
        WHERE {conditions}
        GROUP BY pe.first_name, pe.last_name, MONTH(pe.date)
    """
    
    results = frappe.db.sql(query, tuple(values), as_dict=True)
    
    # Organize data by employee (first_name + last_name)
    employees = {}
    for row in results:
        key = f"{row.first_name} {row.last_name}"
        if key not in employees:
            employees[key] = {
                "first_name": row.first_name,
                "last_name": row.last_name,
                "ytd_usd": 0.0,
                "ytd_zwg": 0.0
            }
            # Initialize months
            for i in range(1, 13):
                employees[key][f"month_{i}_usd"] = 0.0
                employees[key][f"month_{i}_zwg"] = 0.0
                
        month = row.month_num
        usd = frappe.utils.flt(row.paye_usd)
        zwg = frappe.utils.flt(row.paye_zwg)
        
        employees[key][f"month_{month}_usd"] += usd
        employees[key][f"month_{month}_zwg"] += zwg
        
        employees[key]["ytd_usd"] += usd
        employees[key]["ytd_zwg"] += zwg
        
    # Check if a specific employee is filtered
    employee_filter = filters.get("employee")
    if employee_filter:
        emp_doc = frappe.get_doc("havano_employee", employee_filter)
        emp_key = f"{emp_doc.first_name} {emp_doc.last_name}"
        if emp_key in employees:
            return [employees[emp_key]]
        else:
            return []

    return list(employees.values())
