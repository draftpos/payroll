import frappe
from collections import defaultdict

def run():
    year = 2026

    taxable_components = [c.name.strip() for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
    if not taxable_components:
        taxable_components = ['Basic Salary']
    taxable_format = ','.join(['%s'] * len(taxable_components))

    aggregated = defaultdict(lambda: {"usd": 0.0, "zwg": 0.0})

    def normalize_name(name):
        return "".join(name.lower().split()) if name else ""

    processed_slips = set()

    # 1. Aggregate from Salary Slips (standard)
    # Order by docstatus (Submitted > Draft > Cancelled) and then by most recently modified
    slips = frappe.db.sql("""
        SELECT name, employee_name, start_date, currency, docstatus
        FROM `tabSalary Slip`
        WHERE YEAR(start_date) = %s AND MONTH(start_date) BETWEEN 1 AND 6
        ORDER BY 
            employee_name, 
            MONTH(start_date),
            CASE docstatus WHEN 1 THEN 1 WHEN 0 THEN 2 ELSE 3 END,
            modified DESC
    """, (year,), as_dict=True)

    for s in slips:
        emp_name = normalize_name(s.employee_name)
        month_num = s.start_date.month
        key = (emp_name, month_num)
        
        # Only process ONE slip per employee per month (the most valid/recent one)
        if key in processed_slips:
            continue
        processed_slips.add(key)
        
        t_query = frappe.db.sql(f"""
            SELECT SUM(amount) FROM `tabSalary Detail`
            WHERE parent = %s AND TRIM(salary_component) IN ({taxable_format})
        """, [s.name] + taxable_components)
        t_amount = float(t_query[0][0] or 0)
        
        a_query = frappe.db.sql("""
            SELECT SUM(amount) FROM `tabSalary Detail`
            WHERE parent = %s AND TRIM(UPPER(salary_component)) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (s.name,))
        a_amount = float(a_query[0][0] or 0)
        
        taxable = max(0, t_amount - a_amount)
        
        if s.currency == 'USD':
            aggregated[key]["usd"] += taxable
        elif s.currency in ('ZWG', 'ZWL'):
            aggregated[key]["zwg"] += taxable

    processed_h = set()

    # 2. Aggregate missing months from Havano Payroll Entry (custom)
    h_entries = frappe.db.sql("""
        SELECT name, first_name, last_name, date, docstatus
        FROM `tabHavano Payroll Entry`
        WHERE YEAR(date) = %s AND MONTH(date) BETWEEN 1 AND 6
        ORDER BY 
            first_name, last_name,
            MONTH(date),
            CASE docstatus WHEN 1 THEN 1 WHEN 0 THEN 2 ELSE 3 END,
            modified DESC
    """, (year,), as_dict=True)

    for h in h_entries:
        emp_name = normalize_name(f"{h.first_name or ''} {h.last_name or ''}")
        month_num = h.date.month if h.date else None
        if not month_num or month_num > 6:
            continue
            
        key = (emp_name, month_num)
        
        # Skip if already handled by a standard slip, or if we already processed a custom entry for this month
        if key in processed_slips or key in processed_h:
            continue
        processed_h.add(key)
            
        t_usd_query = frappe.db.sql(f"""
            SELECT SUM(amount_usd) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_earnings' AND TRIM(components) IN ({taxable_format})
        """, [h.name] + taxable_components)
        t_usd = float(t_usd_query[0][0] or 0)
        
        t_zwg_query = frappe.db.sql(f"""
            SELECT SUM(amount_zwg) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_earnings' AND TRIM(components) IN ({taxable_format})
        """, [h.name] + taxable_components)
        t_zwg = float(t_zwg_query[0][0] or 0)
        
        a_usd_query = frappe.db.sql("""
            SELECT SUM(amount_usd) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_deductions' 
              AND TRIM(UPPER(components)) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (h.name,))
        a_usd = float(a_usd_query[0][0] or 0)
        
        a_zwg_query = frappe.db.sql("""
            SELECT SUM(amount_zwg) FROM `tabhavano_payroll_earnings`
            WHERE parent = %s AND parentfield = 'employee_deductions' 
              AND TRIM(UPPER(components)) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (h.name,))
        a_zwg = float(a_zwg_query[0][0] or 0)
        
        taxable_usd = max(0, t_usd - a_usd)
        taxable_zwg = max(0, t_zwg - a_zwg)
        
        aggregated[key]["usd"] += taxable_usd
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
    frappe.cache().delete_key('report_cache')
    frappe.clear_cache()
    
    print(f"Successfully processed {len(processed_slips)} valid standard slips and {len(processed_h)} custom entries!")
    print(f"Updated {updated_count} employee records in the database.")
