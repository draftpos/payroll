# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt

class HavanoPayrollEntry(Document):
    def on_submit(self):
        self.update_historical_paye(cancel=False)
        
    def on_cancel(self):
        self.update_historical_paye(cancel=True)
        
    def update_historical_paye(self, cancel=False):
        if not self.date:
            return
            
        pe_date = getdate(self.date)
        tax_year = str(pe_date.year)
        month_num = pe_date.month
        
        # Calculate PAYE from this entry
        paye_usd = 0.0
        paye_zwg = 0.0
        for d in self.employee_deductions:
            if (d.components or "").upper() == "PAYE":
                paye_usd += flt(d.amount_usd)
                paye_zwg += flt(d.amount_zwg)
                
        if paye_usd == 0 and paye_zwg == 0:
            return
            
        # Find the Employee
        if not self.first_name:
            return
            
        # Try to resolve employee Link if they don't have it directly on the entry
        # The report uses first_name + last_name
        emp = frappe.get_all("havano_employee", filters={"first_name": self.first_name, "last_name": self.last_name or ""}, limit=1)
        if not emp:
            return
            
        emp_name = emp[0].name
        
        existing = frappe.get_all("Havano Historical PAYE", filters={"employee": emp_name, "tax_year": tax_year}, limit=1)
        
        if existing:
            doc = frappe.get_doc("Havano Historical PAYE", existing[0].name)
        elif not cancel:
            doc = frappe.new_doc("Havano Historical PAYE")
            doc.employee = emp_name
            doc.tax_year = tax_year
        else:
            return
            
        current_usd = flt(doc.get(f"month_{month_num}_usd"))
        current_zwg = flt(doc.get(f"month_{month_num}_zwg"))
        
        if cancel:
            doc.set(f"month_{month_num}_usd", max(0, current_usd - paye_usd))
            doc.set(f"month_{month_num}_zwg", max(0, current_zwg - paye_zwg))
        else:
            doc.set(f"month_{month_num}_usd", current_usd + paye_usd)
            doc.set(f"month_{month_num}_zwg", current_zwg + paye_zwg)
            
        doc.flags.ignore_permissions = True
        doc.save()
