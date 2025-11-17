import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import flt
from . import base_currency,split_currency

class havano_employee(Document):
    def before_save(self):
        print(self.native_employee_id)
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
        existing_emp = frappe.db.exists("Employee", self.native_employee_id)

        if existing_emp:
            # UPDATE EMPLOYEE
            employee_doc = frappe.get_doc("Employee", existing_emp)

            employee_doc.first_name = self.first_name
            employee_doc.last_name = self.last_name
            employee_doc.gender = self.gender
            employee_doc.status = self.status
            employee_doc.company = self.company
            employee_doc.date_of_birth = self.date_of_birth
            employee_doc.date_of_joining = self.date_of_joining

            employee_doc.save(ignore_permissions=True)
            frappe.db.commit()

            # frappe.msgprint(f"Updated Employee: {employee_doc.name}")


        else:
            # CREATE EMPLOYEE
            employee_doc = frappe.get_doc({
                "doctype": "Employee",
                "name": self.native_employee_id,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "gender": self.gender,
                "company": self.company,
                "status": "Active",
                "date_of_birth": self.date_of_birth,
                "date_of_joining": self.date_of_joining
            })

            employee_doc.insert(ignore_permissions=True)
            frappe.db.commit()

            self.native_employee_id = employee_doc.name
            #frappe.msgprint(f"Created Employee: {employee_doc.name}")
