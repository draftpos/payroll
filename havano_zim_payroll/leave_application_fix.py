import frappe
from frappe import _
from frappe.utils import flt

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
            
            # Create Ledger Entry
            try:
                ledger = frappe.new_doc("Havano Leave Ledger Entry")
                ledger.employee = doc.employee
                ledger.posting_date = getattr(doc, "posting_date", None) or frappe.utils.today()
                ledger.transaction_type = "Leave Application"
                ledger.transaction_name = doc.name
                ledger.days_added = 0.0
                ledger.days_deducted = total_days
                ledger.balance_after_transaction = new_balance
                ledger.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to create Havano Leave Ledger Entry: {str(e)}", "Leave Ledger Error")

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

def on_cancel(doc, method=None):
    """Restore leave days to Havano Leave Balances on cancellation."""
    if doc.doctype == "Leave Application":
        total_days = getattr(doc, "total_leave_days", 0)
        leave_type = getattr(doc, "leave_type", "Annual Leave")
        
        balance = frappe.db.get_value("Havano Leave Balances", 
            {"employee": doc.employee, "havano_leave_type": leave_type}, 
            ["name", "leave_balance"], as_dict=True)
        
        if balance:
            new_balance = (balance.leave_balance or 0) + total_days
            frappe.db.set_value("Havano Leave Balances", balance.name, "leave_balance", new_balance)
            
            # Create Ledger Entry for Reversal
            try:
                ledger = frappe.new_doc("Havano Leave Ledger Entry")
                ledger.employee = doc.employee
                ledger.posting_date = getattr(doc, "posting_date", None) or frappe.utils.today()
                ledger.transaction_type = "Leave Reversal"
                ledger.transaction_name = f"Cancelled: {doc.name}"
                ledger.days_added = total_days
                ledger.days_deducted = 0.0
                ledger.balance_after_transaction = new_balance
                ledger.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to create Havano Leave Ledger Entry: {str(e)}", "Leave Ledger Error")

            frappe.msgprint(_("Havano Leave Balance restored. New balance: {0}").format(new_balance))

def validate_leave_balance(doc, method=None):
    """Refuse to save if leave balance exceeds configured maximum."""
    if doc.doctype == "Havano Leave Balances":
        settings = frappe.get_single("Havano Payroll Settings")
        max_days = None
        leave_type_lower = doc.havano_leave_type.lower() if doc.havano_leave_type else ""
        
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
            
        if max_days is not None and flt(doc.leave_balance) > max_days:
            frappe.throw(_("Maximum {0} balance allowed is {1} days. You cannot save a balance of {2}.").format(doc.havano_leave_type, max_days, doc.leave_balance))
