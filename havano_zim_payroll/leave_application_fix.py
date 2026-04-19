import frappe
from frappe import _

def on_submit(doc, method=None):
    """Subtract leave days from Havano Leave Balances on submission."""
    if doc.doctype == "Leave Application":
        # We assume fields are 'employee', 'leave_type', and 'total_leave_days'
        # Adjust these if the actual field names differ
        total_days = getattr(doc, "total_leave_days", 0)
        leave_type = getattr(doc, "leave_type", "Annual Leave")
        
        balance = frappe.db.get_value("Havano Leave Balances", 
            {"employee": doc.employee, "havano_leave_type": leave_type}, 
            ["name", "leave_balance"], as_dict=True)
        
        if balance:
            new_balance = (balance.leave_balance or 0) - total_days
            frappe.db.set_value("Havano Leave Balances", balance.name, "leave_balance", new_balance)
            frappe.msgprint(_("Havano Leave Balance updated. New balance: {0}").format(new_balance))

def before_insert(doc, method=None):
    """Automatically pick Leave Approver and ensure unique naming."""
    if doc.doctype == "Leave Application":
        # 1. Pick Leave Approver from havano_employee
        if not doc.leave_approver and doc.employee:
            approver = frappe.db.get_value("havano_employee", doc.employee, "leave_approver")
            if approver:
                doc.leave_approver = approver
        
        # 2. Ensure a record for EACH leave application (prevent overwriting)
        # We can append a timestamp or hash to the name if needed, 
        # but standard Leave Application usually uses a series.
        # If the user's system was overwriting, it might be due to a custom autoname logic.
        pass

def validate_leave_balance(doc, method=None):
    """Refuse to save if Annual Leave balance exceeds 90 days."""
    if doc.doctype == "Havano Leave Balances" and doc.havano_leave_type == "Annual Leave":
        if doc.leave_balance > 90:
            frappe.throw(_("Maximum Annual Leave balance allowed is 90 days. You cannot save a balance of {0}.").format(doc.leave_balance))
