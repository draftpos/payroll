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
        columns.append({"label": _(f"{month} Taxable Income (USD)"), "fieldname": f"month_{i+1}_income_usd", "fieldtype": "Currency", "width": 140})
        columns.append({"label": _(f"{month} Taxable Income (ZWG)"), "fieldname": f"month_{i+1}_income_zwg", "fieldtype": "Currency", "width": 140})
        
    columns.append({"label": _("YTD Taxable Income (USD)"), "fieldname": "ytd_income_usd", "fieldtype": "Currency", "width": 150})
    columns.append({"label": _("YTD Taxable Income (ZWG)"), "fieldname": "ytd_income_zwg", "fieldtype": "Currency", "width": 150})
    
    return columns

def get_data(filters):
    year = filters.get("year")
    if not year:
        year = frappe.utils.nowdate()[:4]
        
    department_filter = ""
    query_args = [year]
    if filters and filters.get("department"):
        department_filter = " AND EXISTS (SELECT 1 FROM `tabhavano_employee` emp WHERE emp.first_name = `tabHavano Historical PAYE`.first_name AND emp.last_name = `tabHavano Historical PAYE`.last_name AND emp.department = %s)"
        query_args.append(filters.get("department"))
        
    employees = {}
    
    # Fetch Taxable Income from the single source of truth: Havano Historical PAYE
    historical_query = f"""
        SELECT 
            first_name, 
            last_name,
            month_1_income_usd, month_1_income_zwg,
            month_2_income_usd, month_2_income_zwg,
            month_3_income_usd, month_3_income_zwg,
            month_4_income_usd, month_4_income_zwg,
            month_5_income_usd, month_5_income_zwg,
            month_6_income_usd, month_6_income_zwg,
            month_7_income_usd, month_7_income_zwg,
            month_8_income_usd, month_8_income_zwg,
            month_9_income_usd, month_9_income_zwg,
            month_10_income_usd, month_10_income_zwg,
            month_11_income_usd, month_11_income_zwg,
            month_12_income_usd, month_12_income_zwg
        FROM `tabHavano Historical PAYE`
        WHERE tax_year = %s {department_filter}
    """
    historical_results = frappe.db.sql(historical_query, tuple(query_args), as_dict=True)
    
    for row in historical_results:
        key = f"{row.first_name} {row.last_name}"
        if key not in employees:
            employees[key] = {
                "first_name": row.first_name,
                "last_name": row.last_name,
                "ytd_income_usd": 0.0,
                "ytd_income_zwg": 0.0
            }
            for i in range(1, 13):
                employees[key][f"month_{i}_income_usd"] = 0.0
                employees[key][f"month_{i}_income_zwg"] = 0.0
                
        for i in range(1, 13):
            usd = frappe.utils.flt(row.get(f"month_{i}_income_usd"))
            zwg = frappe.utils.flt(row.get(f"month_{i}_income_zwg"))
            employees[key][f"month_{i}_income_usd"] += usd
            employees[key][f"month_{i}_income_zwg"] += zwg
            employees[key]["ytd_income_usd"] += usd
            employees[key]["ytd_income_zwg"] += zwg
            
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
