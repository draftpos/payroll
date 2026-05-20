# Copyright (c) 2025, Havano and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class Testhavano_employee(FrappeTestCase):
    def test_nssa_allowable_deductions_toggle(self):
        # Ensure a Company exists
        companies = frappe.get_all("Company", limit=1)
        if not companies:
            company_doc = frappe.get_doc({
                "doctype": "Company",
                "company_name": "Test Payroll Company",
                "default_currency": "USD"
            }).insert(ignore_permissions=True)
            company_name = company_doc.name
        else:
            company_name = companies[0].name
            company_doc = frappe.get_doc("Company", company_name)
        
        orig_payslip_type = company_doc.custom_payslip_type
        orig_default_currency = company_doc.default_currency

        # Ensure NSSA and Basic Salary components exist
        if not frappe.db.exists("havano_salary_component", "NSSA"):
            frappe.get_doc({
                "doctype": "havano_salary_component",
                "salary_component": "NSSA",
                "component_type": "Deduction",
                "always_calculate": 1
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("havano_salary_component", "Basic Salary"):
            frappe.get_doc({
                "doctype": "havano_salary_component",
                "salary_component": "Basic Salary",
                "component_type": "Earning",
                "always_calculate": 1
            }).insert(ignore_permissions=True)

        # Ensure test employee exists
        employees = frappe.get_all("havano_employee", filters={"company": company_name}, limit=1)
        if not employees:
            emp_doc = frappe.get_doc({
                "doctype": "havano_employee",
                "first_name": "Test",
                "last_name": "Employee",
                "company": company_name,
                "status": "Active",
                "payroll_frequency": "Monthly",
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            }).insert(ignore_permissions=True)
        else:
            emp_doc = frappe.get_doc("havano_employee", employees[0].name)

        # Clean and setup earnings & deductions
        emp_doc.employee_earnings = []
        emp_doc.employee_deductions = []
        
        emp_doc.append("employee_earnings", {
            "components": "Basic Salary",
            "amount_usd": 1000.0,
            "amount_zwg": 1000.0,
            "is_tax_applicable": 1
        })
        emp_doc.append("employee_deductions", {
            "components": "NSSA",
            "amount_usd": 0.0,
            "amount_zwg": 0.0
        })
        emp_doc.save(ignore_permissions=True)
        frappe.db.commit()

        settings = frappe.get_single("Havano Payroll Settings")
        
        try:
            # =====================================================================
            # 1. BASE CURRENCY PAYSLIP TYPE
            # =====================================================================
            frappe.db.set_value("Company", company_name, {
                "custom_payslip_type": "Base Currency",
                "default_currency": "USD"
            })
            frappe.db.commit()

            # --- Case A: Exclude NSSA (default) ---
            settings.include_nssa_in_taxable_income = 0
            settings.save(ignore_permissions=True)
            frappe.db.commit()

            emp_doc.reload()
            emp_doc.calculate_totals()
            
            nssa_ded = next((d for d in emp_doc.employee_deductions if d.components == "NSSA"), None)
            nssa_val = flt(nssa_ded.amount_usd) if nssa_ded else 0.0
            allowable_val = flt(emp_doc.allowable_deductions)
            
            self.assertEqual(nssa_val, 31.5)
            self.assertTrue(allowable_val >= 31.5)

            # --- Case B: Include NSSA ---
            settings.include_nssa_in_taxable_income = 1
            settings.save(ignore_permissions=True)
            frappe.db.commit()

            emp_doc.reload()
            emp_doc.calculate_totals()
            
            nssa_ded = next((d for d in emp_doc.employee_deductions if d.components == "NSSA"), None)
            nssa_val = flt(nssa_ded.amount_usd) if nssa_ded else 0.0
            allowable_val = flt(emp_doc.allowable_deductions)
            
            self.assertEqual(nssa_val, 31.5)
            self.assertEqual(allowable_val, 0.0)

            # =====================================================================
            # 2. SPLIT CURRENCY PAYSLIP TYPE
            # =====================================================================
            frappe.db.set_value("Company", company_name, "custom_payslip_type", "Split Currency")
            frappe.db.commit()

            # --- Case A: Exclude NSSA (default) ---
            settings.include_nssa_in_taxable_income = 0
            settings.save(ignore_permissions=True)
            frappe.db.commit()

            emp_doc.reload()
            emp_doc.calculate_totals()
            
            nssa_ded = next((d for d in emp_doc.employee_deductions if d.components == "NSSA"), None)
            nssa_usd = flt(nssa_ded.amount_usd) if nssa_ded else 0.0
            allowable_usd = flt(emp_doc.total_allowable_deductions_usd)
            
            self.assertEqual(nssa_usd, 31.5)
            self.assertTrue(allowable_usd >= 31.5)

            # --- Case B: Include NSSA ---
            settings.include_nssa_in_taxable_income = 1
            settings.save(ignore_permissions=True)
            frappe.db.commit()

            emp_doc.reload()
            emp_doc.calculate_totals()
            
            nssa_ded = next((d for d in emp_doc.employee_deductions if d.components == "NSSA"), None)
            nssa_usd = flt(nssa_ded.amount_usd) if nssa_ded else 0.0
            allowable_usd = flt(emp_doc.total_allowable_deductions_usd)
            
            self.assertEqual(nssa_usd, 31.5)
            self.assertEqual(allowable_usd, 0.0)

        finally:
            # Restore original configurations
            frappe.db.set_value("Company", company_name, {
                "custom_payslip_type": orig_payslip_type,
                "default_currency": orig_default_currency
            })
            settings.include_nssa_in_taxable_income = 0
            settings.save(ignore_permissions=True)
            frappe.db.commit()
