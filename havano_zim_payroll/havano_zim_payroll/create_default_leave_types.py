import frappe

@frappe.whitelist()
def create_leave_types():
    """
    Inserts default leave types into 'havano_leave_type' DocType
    using correct field names and default values.
    """
    leave_types = [
        {"leave_type_name": "Maternity Leave", "max_leaves_allowed": 10, "applicable_after": 10, "max_continuous_days_allowed": 10},
        {"leave_type_name": "Annual Leave", "max_leaves_allowed": 10, "applicable_after": 10, "max_continuous_days_allowed": 10},
        {"leave_type_name": "Sick Leave", "max_leaves_allowed": 10, "applicable_after": 10, "max_continuous_days_allowed": 10},
        {"leave_type_name": "Bereavement Leave", "max_leaves_allowed": 10, "applicable_after": 10, "max_continuous_days_allowed": 10},
        {"leave_type_name": "Special Leave", "max_leaves_allowed": 10, "applicable_after": 10, "max_continuous_days_allowed": 10},
        {"leave_type_name": "Study Leave", "max_leaves_allowed": 10, "applicable_after": 10, "max_continuous_days_allowed": 10},
    ]

    for lt in leave_types:
        if not frappe.db.exists("havano_leave_type", lt["leave_type_name"]):
            doc = frappe.get_doc({
                "doctype": "havano_leave_type",
                "leave_type_name": lt["leave_type_name"],
                "max_leaves_allowed": lt["max_leaves_allowed"],
                "applicable_after": lt["applicable_after"],
                "max_continuous_days_allowed": lt["max_continuous_days_allowed"]
            })
            doc.insert()
            frappe.db.commit()
            print(f"Created Leave Type: {lt['leave_type_name']}")
        else:
            print(f"Leave Type already exists: {lt['leave_type_name']}")
