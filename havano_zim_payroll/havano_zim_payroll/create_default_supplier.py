import frappe

@frappe.whitelist()
def insert_suppliers():
    suppliers = [
        "Winfield 7",
        "ZIMRA",
        "LAPF",
        "Fuel",
        "UFAWUZ",
        "Employees",
        "ZiBAWU",
        "SDL",
        "NECWEI",
        "ZESCWU"
    ]

    # dedupe but keep order
    unique_suppliers = list(dict.fromkeys(suppliers))

    for supplier_name in unique_suppliers:
        if not frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
            supplier = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": supplier_name,
                "supplier_type": "Company",  # or "Individual" if appropriate
            })
            supplier.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Inserted → {supplier_name}")
        else:
            print(f"Skipped (already exists) → {supplier_name}")
