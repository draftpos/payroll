import frappe
from frappe.utils import flt

def get_month_name(month_num):
    months = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }
    return months.get(month_num)

def execute():
    year = 2026
    historical_records = frappe.get_all("Havano Historical PAYE", filters={"year": year})
    
    updated_count = 0
    for h in historical_records:
        doc = frappe.get_doc("Havano Historical PAYE", h.name)
        emp = doc.employee
        changed = False
        
        for month_num in range(1, 7):
            month_name = get_month_name(month_num)
            usd = 0.0
            zwg = 0.0
            
            # Check standard Salary Slip first
            taxable_usd_from_slips = frappe.db.sql("""
                SELECT SUM(sd.amount) 
                FROM `tabSalary Detail` sd
                JOIN `tabSalary Slip` ss ON ss.name = sd.parent
                JOIN `tabSalary Component` sc ON sc.name = sd.salary_component
                WHERE ss.employee = %s 
                  AND ss.docstatus = 1 
                  AND YEAR(ss.start_date) = %s 
                  AND MONTH(ss.start_date) = %s 
                  AND sc.is_tax_applicable = 1
                  AND ss.currency = 'USD'
            """, (emp, year, month_num))
            
            if taxable_usd_from_slips and taxable_usd_from_slips[0][0] is not None:
                usd = flt(taxable_usd_from_slips[0][0])
                
            taxable_zwg_from_slips = frappe.db.sql("""
                SELECT SUM(sd.amount) 
                FROM `tabSalary Detail` sd
                JOIN `tabSalary Slip` ss ON ss.name = sd.parent
                JOIN `tabSalary Component` sc ON sc.name = sd.salary_component
                WHERE ss.employee = %s 
                  AND ss.docstatus = 1 
                  AND YEAR(ss.start_date) = %s 
                  AND MONTH(ss.start_date) = %s 
                  AND sc.is_tax_applicable = 1
                  AND ss.currency IN ('ZWG', 'ZWL')
            """, (emp, year, month_num))
            
            if taxable_zwg_from_slips and taxable_zwg_from_slips[0][0] is not None:
                zwg = flt(taxable_zwg_from_slips[0][0])
                
            # If nothing in standard slip, check Havano Payroll Entry
            if usd == 0 and zwg == 0:
                hpe = frappe.db.sql("""
                    SELECT total_taxable_income_usd, total_taxable_income_zwg
                    FROM `tabHavano Payroll Entry`
                    WHERE employee = %s AND month = %s AND year = %s AND docstatus = 1
                    LIMIT 1
                """, (emp, month_name, year), as_dict=True)
                
                if hpe:
                    usd = flt(hpe[0].total_taxable_income_usd)
                    zwg = flt(hpe[0].total_taxable_income_zwg)

            # Check if missing or incorrect
            current_usd = flt(doc.get(f"month_{month_num}_income_usd"))
            current_zwg = flt(doc.get(f"month_{month_num}_income_zwg"))
            
            if abs(current_usd - usd) > 0.01 or abs(current_zwg - zwg) > 0.01:
                doc.set(f"month_{month_num}_income_usd", usd)
                doc.set(f"month_{month_num}_income_zwg", zwg)
                changed = True
                
        if changed:
            doc.save(ignore_permissions=True)
            updated_count += 1
            
    frappe.db.commit()
    print(f"Updated {updated_count} historical PAYE records for Jan-Jun {year}")
