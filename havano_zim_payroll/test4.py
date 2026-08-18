import frappe
from collections import defaultdict

def run():
    year = 2026

    slips = frappe.db.sql("""
        SELECT name, employee, employee_name, start_date, currency
        FROM `tabSalary Slip`
        WHERE docstatus < 2 AND YEAR(start_date) = %s AND MONTH(start_date) BETWEEN 1 AND 6
    """, (year,), as_dict=True)

    taxable_components = [c.name for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
    if not taxable_components:
        taxable_components = ['Basic Salary']
    taxable_format = ','.join(['%s'] * len(taxable_components))

    # We will aggregate by Employee Name (ignoring case/spaces) and Month
    aggregated = defaultdict(lambda: {"usd": 0.0, "zwg": 0.0})

    def normalize_name(name):
        return "".join(name.lower().split()) if name else ""

    for s in slips:
        emp_name = normalize_name(s.employee_name)
        month_num = s.start_date.month
        
        t_query = frappe.db.sql(f"""
            SELECT SUM(amount)
            FROM `tabSalary Detail`
            WHERE parent = %s AND salary_component IN ({taxable_format})
        """, [s.name] + taxable_components)
        t_amount = float(t_query[0][0] or 0)
        
        a_query = frappe.db.sql("""
            SELECT SUM(amount)
            FROM `tabSalary Detail`
            WHERE parent = %s 
              AND UPPER(salary_component) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (s.name,))
        a_amount = float(a_query[0][0] or 0)
        
        taxable = max(0, t_amount - a_amount)
        
        key = (emp_name, month_num)
        if s.currency == 'USD':
            aggregated[key]["usd"] += taxable
        elif s.currency in ('ZWG', 'ZWL'):
            aggregated[key]["zwg"] += taxable

    historical_records = frappe.get_all("Havano Historical PAYE", filters={"tax_year": year})
    updated_count = 0

    for h in historical_records:
        doc = frappe.get_doc("Havano Historical PAYE", h.name)
        
        # Try to match the employee name exactly as it appears in the slips
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
    print(f"Successfully updated Taxable Income for {updated_count} employees!")
