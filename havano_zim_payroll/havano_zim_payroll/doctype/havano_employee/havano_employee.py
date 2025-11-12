import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import flt
from . import base_currency,split_currency

class havano_employee(Document):
    def before_save(self):
        company = self.company
        payslip_type = frappe.db.get_value("Company", company, "custom_payslip_type")
        self.payslip_type=payslip_type
        print(f"-------------------------{payslip_type}")

        if payslip_type == "Base Currency":
            base_currency.main(self)
        elif payslip_type == "Split Currency":
            split_currency.main(self)
        

       