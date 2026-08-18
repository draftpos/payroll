import frappe

def run():
    year = 2026
    historical_records = frappe.get_all("Havano Historical PAYE", filters={"tax_year": year})
    updated_count = 0

    taxable_components = [c.name for c in frappe.get_all("havano_salary_component", filters={"is_tax_applicable": 1})]

    allowable_components = [c.name for c in frappe.get_all("havano_salary_component", filters={"type": "Deduction"}) if "allowable" in (frappe.get_value("havano_salary_component", c.name, "component_mode") or "").lower()]
    if not frappe.db.get_single_value("Havano Payroll Settings", "include_nssa_in_taxable_income"):
        if "NSSA" not in allowable_components:
            allowable_components.append("NSSA")

    if taxable_components:
        taxable_format = ','.join(['%s'] * len(taxable_components))
    else:
        taxable_format = "''"

    if allowable_components:
        allowable_format = ','.join(['%s'] * len(allowable_components))
    else:
        allowable_format = "''"

    for h in historical_records:
        doc = frappe.get_doc("Havano Historical PAYE", h.name)
        fname = doc.first_name or ""
        lname = doc.last_name or ""
        changed = False
        
        for month_num in range(1, 7):
            t_usd = 0.0
            t_zwg = 0.0
            if taxable_components:
                # We use docstatus = 0 because Havano Payroll Entry is not a submittable doctype
                taxable_usd_query = frappe.db.sql(f"""
                    SELECT SUM(sd.amount_usd) 
                    FROM `tabhavano_payroll_earnings` sd
                    JOIN `tabHavano Payroll Entry` ss ON ss.name = sd.parent
                    WHERE ss.first_name = %s AND ss.last_name = %s AND ss.docstatus = 0 
                      AND YEAR(ss.date) = %s AND MONTH(ss.date) = %s 
                      AND sd.components IN ({taxable_format}) AND sd.parentfield = 'employee_earnings'
                """, [fname, lname, year, month_num] + taxable_components)
                t_usd = float(taxable_usd_query[0][0] or 0)
                    
                taxable_zwg_query = frappe.db.sql(f"""
                    SELECT SUM(sd.amount_zwg) 
                    FROM `tabhavano_payroll_earnings` sd
                    JOIN `tabHavano Payroll Entry` ss ON ss.name = sd.parent
                    WHERE ss.first_name = %s AND ss.last_name = %s AND ss.docstatus = 0 
                      AND YEAR(ss.date) = %s AND MONTH(ss.date) = %s 
                      AND sd.components IN ({taxable_format}) AND sd.parentfield = 'employee_earnings'
                """, [fname, lname, year, month_num] + taxable_components)
                t_zwg = float(taxable_zwg_query[0][0] or 0)
            
            a_usd = 0.0
            a_zwg = 0.0
            if allowable_components:
                allowable_usd_query = frappe.db.sql(f"""
                    SELECT SUM(sd.amount_usd)
                    FROM `tabhavano_payroll_earnings` sd
                    JOIN `tabHavano Payroll Entry` ss ON ss.name = sd.parent
                    WHERE ss.first_name = %s AND ss.last_name = %s AND ss.docstatus = 0 
                      AND YEAR(ss.date) = %s AND MONTH(ss.date) = %s
                      AND sd.components IN ({allowable_format}) AND sd.parentfield = 'employee_deductions'
                """, [fname, lname, year, month_num] + allowable_components)
                a_usd = float(allowable_usd_query[0][0] or 0)
                
                allowable_zwg_query = frappe.db.sql(f"""
                    SELECT SUM(sd.amount_zwg)
                    FROM `tabhavano_payroll_earnings` sd
                    JOIN `tabHavano Payroll Entry` ss ON ss.name = sd.parent
                    WHERE ss.first_name = %s AND ss.last_name = %s AND ss.docstatus = 0 
                      AND YEAR(ss.date) = %s AND MONTH(ss.date) = %s
                      AND sd.components IN ({allowable_format}) AND sd.parentfield = 'employee_deductions'
                """, [fname, lname, year, month_num] + allowable_components)
                a_zwg = float(allowable_zwg_query[0][0] or 0)
            
            usd = max(0, t_usd - a_usd)
            zwg = max(0, t_zwg - a_zwg)
                    
            current_usd = float(doc.get(f"month_{month_num}_income_usd") or 0)
            current_zwg = float(doc.get(f"month_{month_num}_income_zwg") or 0)
            
            if abs(current_usd - usd) > 0.01 or abs(current_zwg - zwg) > 0.01:
                doc.set(f"month_{month_num}_income_usd", usd)
                doc.set(f"month_{month_num}_income_zwg", zwg)
                changed = True
                
        if changed:
            doc.save(ignore_permissions=True)
            updated_count += 1

    frappe.db.commit()
    print(f"Updated {updated_count} Taxable Income records for Jan-Jun {year}")
