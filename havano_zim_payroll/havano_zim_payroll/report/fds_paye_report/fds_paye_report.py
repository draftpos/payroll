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
        
    employees = {}
    
    # Fetch PAYE from the single source of truth: Havano Historical PAYE
    historical_query = f"""
        SELECT 
            first_name, 
            last_name,
            month_1_usd, month_1_zwg,
            month_2_usd, month_2_zwg,
            month_3_usd, month_3_zwg,
            month_4_usd, month_4_zwg,
            month_5_usd, month_5_zwg,
            month_6_usd, month_6_zwg,
            month_7_usd, month_7_zwg,
            month_8_usd, month_8_zwg,
            month_9_usd, month_9_zwg,
            month_10_usd, month_10_zwg,
            month_11_usd, month_11_zwg,
            month_12_usd, month_12_zwg
        FROM `tabHavano Historical PAYE`
        WHERE tax_year = %s
    """
    historical_results = frappe.db.sql(historical_query, (year,), as_dict=True)
    
    for row in historical_results:
        key = f"{row.first_name} {row.last_name}"
        if key not in employees:
            employees[key] = {
                "first_name": row.first_name,
                "last_name": row.last_name,
                "ytd_usd": 0.0,
                "ytd_zwg": 0.0
            }
            for i in range(1, 13):
                employees[key][f"month_{i}_usd"] = 0.0
                employees[key][f"month_{i}_zwg"] = 0.0
                
        for i in range(1, 13):
            usd = frappe.utils.flt(row.get(f"month_{i}_usd"))
            zwg = frappe.utils.flt(row.get(f"month_{i}_zwg"))
            employees[key][f"month_{i}_usd"] += usd
            employees[key][f"month_{i}_zwg"] += zwg
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
