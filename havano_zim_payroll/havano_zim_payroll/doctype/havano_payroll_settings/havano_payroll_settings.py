# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe import _

class HavanoPayrollSettings(Document):
    def validate(self):
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc:
                old_f = old_doc.allow_forecast_fds_method
                old_a = old_doc.allow_averaging_fds_method
                new_f = self.allow_forecast_fds_method
                new_a = self.allow_averaging_fds_method

                if old_f != new_f or old_a != new_a:
                    current_year = str(getdate(nowdate()).year)
                    has_payroll = frappe.db.count('Havano Historical PAYE', {'tax_year': current_year})
                    if has_payroll > 0:
                        frappe.throw(_('You cannot change FDS or Averaging settings during the year as payroll has already been processed for {0}.').format(current_year))
