import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import flt
from . import base_currency,split_currency

class havano_employee(Document):
    def before_save(self):
        if self.payslip_type == "Base Currency":
            base_currency.main(self)
        elif self.payslip_type == "Split Currency":
            split_currency.main(self)
        

       