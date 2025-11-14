import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import flt
from . import base_currency,split_currency

class havano_employee(Document):
    def before_save(self):
        company = self.company
        
        # Set payslip type from company
        payslip_type = frappe.db.get_value("Company", company, "custom_payslip_type")
        self.payslip_type = payslip_type
        print(f"-------------------------{payslip_type}")

        if payslip_type == "Base Currency":
            base_currency.main(self)
        elif payslip_type == "Split Currency":
            split_currency.main(self)

        # -----------------------------
        # Create ERPNext Employee if not exists
        # -----------------------------
        if not frappe.db.exists("Employee", {"employee_number": self.name}):
            employee_doc = frappe.get_doc({
                "doctype": "Employee",
                "first_name": self.first_name,
                "last_name":self.last_name,
                "gender": self.gender,
                "company": self.company,
                "status": "Active",
                "date_of_birth": self.date_of_birth,
                "date_of_joining": self.date_of_joining
            })
            employee_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"ERPNext Employee created for {self.name}")
