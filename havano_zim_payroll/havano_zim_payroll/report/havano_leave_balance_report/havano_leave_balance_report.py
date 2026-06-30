import frappe
from frappe.utils import get_last_day, getdate, formatdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "havano_employee", "width": 150},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "as_on_date", "label": "As On Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "leave_balance", "label": "Exact Leave Balance", "fieldtype": "Float", "width": 150},
        {"fieldname": "last_transaction", "label": "Last Transaction Details", "fieldtype": "Data", "width": 250}
    ]

def get_data(filters):
    conditions = ""
    if filters and filters.get("employee"):
        conditions = f" AND name = '{filters.get('employee')}'"

    # Determine 'as_on_date'
    as_on_date = None
    if filters and filters.get("as_on_month") and filters.get("as_on_year"):
        # Calculate the last day of the selected month
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
            "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
        }
        month_num = month_map.get(filters.get("as_on_month"))
        year = int(filters.get("as_on_year"))
        if month_num:
            as_on_date = get_last_day(getdate(f"{year}-{month_num}-01"))

    employees = frappe.db.sql(f"""
        SELECT name, first_name, last_name 
        FROM `tabhavano_employee` 
        WHERE status = 'Active' {conditions}
    """, as_dict=True)

    data = []
    
    for emp in employees:
        emp_name = f"{emp.first_name} {emp.last_name or ''}".strip()
        
        if as_on_date:
            # Get the LATEST ledger entry on or before the as_on_date
            latest_entry = frappe.db.sql("""
                SELECT posting_date, transaction_type, transaction_name, balance_after_transaction
                FROM `tabHavano Leave Ledger Entry`
                WHERE employee = %s AND posting_date <= %s
                ORDER BY posting_date DESC, creation DESC
                LIMIT 1
            """, (emp.name, as_on_date), as_dict=True)
            
            if latest_entry:
                entry = latest_entry[0]
                data.append({
                    "employee": emp.name,
                    "employee_name": emp_name,
                    "as_on_date": as_on_date,
                    "leave_balance": entry.balance_after_transaction,
                    "last_transaction": f"{entry.transaction_type} ({entry.transaction_name})"
                })
            else:
                # No history before that date
                data.append({
                    "employee": emp.name,
                    "employee_name": emp_name,
                    "as_on_date": as_on_date,
                    "leave_balance": 0.0,
                    "last_transaction": "No History"
                })
        else:
            # No date filter, just show current balance from the Allocation table
            alloc = frappe.db.get_value("Havano Annual Leave Allocation", {"employee": emp.name}, "total_days") or 0.0
            data.append({
                "employee": emp.name,
                "employee_name": emp_name,
                "as_on_date": None,
                "leave_balance": alloc,
                "last_transaction": "Current Allocation"
            })
            
    return data
