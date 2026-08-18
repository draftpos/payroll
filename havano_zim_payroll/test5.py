import frappe
from collections import defaultdict

def run():
    year = 2026

    taxable_components = [c.name for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
    if not taxable_components:
        taxable_components = ['Basic Salary']
    taxable_format = ','.join(['%s'] * len(taxable_components))

    aggregated = defaultdict(lambda: {"usd": 0.0, "zwg": 0.0})

    def normalize_name(name):
        return "".join(name.lower().split()) if name else ""

    months_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, 
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }

    # 1. Aggregate from Salary Slips (standard)
    slips = frappe.db.sql("""
        SELECT name, employee_name, start_date, currency
        FROM `tabSalary Slip`
        WHERE docstatus < 2 AND YEAR(start_date) = %s AND MONTH(start_date) BETWEEN 1 AND 6
    """, (year,), as_dict=True)

    for s in slips:
        emp_name = normalize_name(s.employee_name)
        month_num = s.start_date.month
        
        t_query = frappe.db.sql(f"""
            SELECT SUM(amount) FROM `tabSalary Detail`
            WHERE parent = %s AND salary_component IN ({taxable_format})
        """, [s.name] + taxable_components)
        t_amount = float(t_query[0][0] or 0)
        
        a_query = frappe.db.sql("""
            SELECT SUM(amount) FROM `tabSalary Detail`
            WHERE parent = %s AND UPPER(salary_component) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (s.name,))
        a_amount = float(a_query[0][0] or 0)
        
        taxable = max(0, t_amount - a_amount)
        
        key = (emp_name, month_num)
        if s.currency == 'USD':
            aggregated[key]["usd"] += taxable
        elif s.currency in ('ZWG', 'ZWL'):
            aggregated[key]["zwg"] += taxable

    # 2. Aggregate from Havano Payroll Entry (custom)
    h_entries = frappe.db.sql("""
        SELECT name, first_name, last_name, month
        FROM `tabHavano Payroll Entry`
        WHERE docstatus < 2 AND year = %s
    """, (str(year),), as_dict=True)

    for h in h_entries:
        emp_name = normalize_name(f"{h.first_name or ''} {h.last_name or ''}")
        month_num = months_map.get(h.month)
        if not month_num or month_num > 6:
            continue
            
        t_usd_query = frappe.db.sql(f"""
            SELECT SUM(amount_usd) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_earnings' AND components IN ({taxable_format})
        """, [h.name] + taxable_components)
        t_usd = float(t_usd_query[0][0] or 0)
        
        t_zwg_query = frappe.db.sql(f"""
            SELECT SUM(amount_zwg) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_earnings' AND components IN ({taxable_format})
        """, [h.name] + taxable_components)
        t_zwg = float(t_zwg_query[0][0] or 0)
        
        a_usd_query = frappe.db.sql("""
            SELECT SUM(amount_usd) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_deductions' 
              AND UPPER(components) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (h.name,))
        a_usd = float(a_usd_query[0][0] or 0)
        
        a_zwg_query = frappe.db.sql("""
            SELECT SUM(amount_zwg) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_deductions' 
              AND UPPER(components) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (h.name,))
        a_zwg = float(a_zwg_query[0][0] or 0)
        
        taxable_usd = max(0, t_usd - a_usd)
        taxable_zwg = max(0, t_zwg - a_zwg)
        
        key = (emp_name, month_num)
        if aggregated[key]["usd"] == 0.0:
            aggregated[key]["usd"] += taxable_usd
        if aggregated[key]["zwg"] == 0.0:
            aggregated[key]["zwg"] += taxable_zwg

    # 3. Update the Report
    historical_records = frappe.get_all("Havano Historical PAYE", filters={"tax_year": year})
    updated_count = 0

    for h in historical_records:
        doc = frappe.get_doc("Havano Historical PAYE", h.name)
        hist_name = normalize_name(f"{doc.first_name or ''} {doc.last_name or ''}")
        changed = False
        
        for month_num in range(1, 7):
            data = aggregated.get((hist_name, month_num))
            if not data:
                continue
                
            current_usd = float(doc.get(f"month_{month_num}_income_usd") or 0)
            if abs(current_usd - data["usd"]) > 0.01:
                doc.set(f"month_{month_num}_income_usd", data["usd"])
                changed = True
                
            current_zwg = float(doc.get(f"month_{month_num}_income_zwg") or 0)
            if abs(current_zwg - data["zwg"]) > 0.01:
                doc.set(f"month_{month_num}_income_zwg", data["zwg"])
                changed = True
                
        if changed:
            doc.save(ignore_permissions=True)
            updated_count += 1

    frappe.db.commit()
    print(f"Successfully backfilled missing months and updated {updated_count} employees!")
