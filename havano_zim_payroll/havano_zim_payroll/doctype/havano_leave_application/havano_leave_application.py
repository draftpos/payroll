import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, getdate
from frappe import _

class havano_leave_application(Document):
    def validate(self):
        self.calculate_total_days()
        self.check_leave_balance()

    def calculate_total_days(self):
        if self.from_date and self.to_date:
            self.total_leave_days = date_diff(self.to_date, self.from_date) + 1
            if self.half_day:
                self.total_leave_days -= 0.5
        else:
            self.total_leave_days = 0

    def check_leave_balance(self):
        if self.employee and self.leave_type:
            balance = frappe.db.get_value("Havano Leave Balances", 
                {"employee": self.employee, "havano_leave_type": self.leave_type}, 
                "leave_balance")
            self.leave_balance = balance or 0
            
            if frappe.utils.flt(self.total_leave_days) > frappe.utils.flt(self.leave_balance):
                # We can throw a warning or error here if we want to prevent negative balances
                # For now just informational
                pass

    def before_save(self):
        # Auto-fill approver if not set
        if not self.leave_approver and self.employee:
            approver = frappe.db.get_value("havano_employee", self.employee, "leave_approver")
            if approver:
                self.leave_approver = approver

        # Update balance if status is changed to Approved and saved
        if self.status == "Approved" and not self.leave_balance_updated:
            self.update_leave_balance(-1 * self.total_leave_days)
            self.leave_balance_updated = 1
        # Restore balance if status is changed from Approved to something else
        elif self.status != "Approved" and self.leave_balance_updated:
            self.update_leave_balance(self.total_leave_days)
            self.leave_balance_updated = 0

    def on_submit(self):
        # Ensure balance is updated if it wasn't already done during save
        if self.status == "Approved" and not self.leave_balance_updated:
            self.update_leave_balance(-1 * self.total_leave_days)
            self.leave_balance_updated = 1
        elif self.status != "Approved":
            frappe.msgprint(_("Leave Application submitted but status is not 'Approved'. Balance not deducted."))

    def on_cancel(self):
        # Restore balance if it was previously deducted
        if self.leave_balance_updated:
            self.update_leave_balance(self.total_leave_days)
            self.leave_balance_updated = 0

    def update_leave_balance(self, days):
        balance_name = frappe.db.get_value("Havano Leave Balances", 
            {"employee": self.employee, "havano_leave_type": self.leave_type}, "name")
        
        if balance_name:
            current_balance = frappe.db.get_value("Havano Leave Balances", balance_name, "leave_balance")
            new_balance = (current_balance or 0) + days
            frappe.db.set_value("Havano Leave Balances", balance_name, "leave_balance", new_balance)
            frappe.msgprint(_("Havano Leave Balance updated for {0}. New balance: {1}").format(self.leave_type, new_balance))
        else:
            frappe.msgprint(_("Warning: No Leave Balance record found for {0} to update.").format(self.leave_type))

    def before_insert(self):
        # This is now handled in before_save, but keeping it for safety on first insert if needed
        pass
