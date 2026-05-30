import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt

class HavanoLeaveBalances(Document):
    def validate(self):
        self.validate_leave_limit()

    def validate_leave_limit(self):
        settings = frappe.get_single("Havano Payroll Settings")
        max_days = None
        leave_type_lower = self.havano_leave_type.lower() if self.havano_leave_type else ""
        
        if "annual" in leave_type_lower:
            max_days = flt(settings.max_annual_leave_days) or 90.0
        elif "sick" in leave_type_lower:
            max_days = flt(settings.max_sick_leave_days) or 90.0
        elif "maternity" in leave_type_lower:
            max_days = flt(settings.max_maternity_leave_days) or 90.0
        elif "study" in leave_type_lower:
            max_days = flt(settings.max_study_leave_days) or 10.0
        elif "special" in leave_type_lower:
            max_days = flt(settings.max_special_leave_days) or 12.0
        elif "bereavement" in leave_type_lower:
            max_days = flt(settings.max_bereavement_leave_days) or 12.0
            
        if max_days is not None and flt(self.leave_balance) > max_days:
            frappe.throw(_("Maximum {0} balance allowed is {1} days. You cannot save a balance of {2}.").format(self.havano_leave_type, max_days, self.leave_balance))
