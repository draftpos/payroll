import frappe
from frappe.model.document import Document
from frappe import _

class HavanoLeaveBalances(Document):
    def validate(self):
        self.validate_annual_leave_limit()

    def validate_annual_leave_limit(self):
        if self.havano_leave_type == "Annual Leave":
            if frappe.utils.flt(self.leave_balance) > 90:
                frappe.throw(_("Maximum Annual Leave balance allowed is 90 days. You cannot save a balance of {0}.").format(self.leave_balance))
