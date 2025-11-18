import frappe

@frappe.whitelist()
def insert_items():
    items = [
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
        "FUEL EXPENSE",
        "Expenses",
        "Expenses",
        "Expenses",
        "FUEL EXPENSE",
        "Expenses",
        "Expenses",
        "Expenses",
        "Expenses",
    ]

    # dedupe but keep order
    unique_items = list(dict.fromkeys(items))

    for item_name in unique_items:
        # Item Code == Item Name (if that's your logic)
        if not frappe.db.exists("Item", {"item_code": item_name}):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_name,
                "item_name": item_name,
                "item_group": "All Item Groups",   # or whatever group you want
                "stock_uom": "Nos",                # or your preferred UOM
                "is_stock_item": 0
            })
            item.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Inserted → {item_name}")
        else:
            print(f"Skipped (already exists) → {item_name}")
