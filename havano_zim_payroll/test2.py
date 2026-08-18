import frappe
from collections import defaultdict

def run():
    year = 2026

    # Fetch all Salary Slips for Jan-Jun 2026
    slips = frappe.db.sql("""
        SELECT name, employee, start_date, currency
        FROM `tabSalary Slip`
        WHERE docstatus < 2 AND YEAR(start_date) = %s AND MONTH(start_date) BETWEEN 1 AND 6
    """, (year,), as_dict=True)

    print(f"Found {len(slips)} Salary Slips for Jan-Jun {year}")

    # Get Taxable Components from settings
    taxable_components = [c.name for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]
    if not taxable_components:
        taxable_components = ['Basic Salary']
    taxable_format = ','.join(['%s'] * len(taxable_components))

    # Aggregate by employee, month, and currency
    aggregated = defaultdict(lambda: {"usd": 0.0, "zwg": 0.0})

    for s in slips:
        emp = s.employee
        month_num = s.start_date.month
        
        # Taxable Earnings
        t_query = frappe.db.sql(f"""
            SELECT SUM(amount)
            FROM `tabSalary Detail`
            WHERE parent = %s AND salary_component IN ({taxable_format})
        """, [s.name] + taxable_components)
        t_amount = float(t_query[0][0] or 0)
        
        # Allowable Deductions
        a_query = frappe.db.sql("""
            SELECT SUM(amount)
            FROM `tabSalary Detail`
            WHERE parent = %s 
              AND UPPER(salary_component) IN ('NSSA', 'CIMAS', 'PENSION', 'MEDICAL AID', 'CIMAS MEDICAL')
        """, (s.name,))
        a_amount = float(a_query[0][0] or 0)
        
        taxable = max(0, t_amount - a_amount)
        
        key = (emp, month_num)
        if s.currency == 'USD':
            aggregated[key]["usd"] += taxable
        elif s.currency in ('ZWG', 'ZWL'):
            aggregated[key]["zwg"] += taxable

    updated_count = 0
    employees_updated = set()

    for (emp, month_num), data in aggregated.items():
        hist = frappe.get_all("Havano Historical PAYE", filters={"employee": emp, "tax_year": year}, limit=1)
        if hist:
            doc = frappe.get_doc("Havano Historical PAYE", hist[0].name)
            changed = False
            
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
                employees_updated.add(emp)

    frappe.db.commit()
    print(f"Successfully updated Taxable Income for {len(employees_updated)} employees across {updated_count} months.")
