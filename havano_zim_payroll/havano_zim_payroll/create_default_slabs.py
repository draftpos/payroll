import frappe

def set_default_tax_slabs():
    """
    Insert default tax brackets in Havano Tax Slab after install for USD and ZWG
    """
    slabs_usd = [
        (0.00, 100.00, 0.0, 0.00),
        (100.01, 300.00, 20.0, 20.00),
        (300.01, 1000.00, 25.0, 35.00),
        (1000.01, 2000.00, 30.0, 85.00),
        (2000.01, 3000.00, 35.0, 185.00),
        (3000.01, 1000000.00, 40.0, 335.00),
    ]

    slabs_zwg = [
        (0.00, 2800.00, 0.0, 0.00),
        (2800.01, 8400.00, 0.20, 560.00),
        (8400.01, 28000.00, 0.25, 980.00),
        (28000.01, 56000.00, 0.30, 2380.00),
        (56000.01, 84000.00, 0.35, 5180.00),
        (84000.01, 1000000.00, 0.40, 9380.00),
    ]

    default_slabs = {
        "USD": slabs_usd,
        "ZWL": slabs_zwg
    }

    for currency, slab_list in default_slabs.items():
        if not frappe.db.exists("Havano Tax Slab", currency):
            slab_doc = frappe.get_doc({
                "doctype": "Havano Tax Slab",
                "currency": currency,
                "tax_brackets": []
            })

            for lower, upper, percent, fixed in slab_list:
                slab_doc.append("tax_brackets", {
                    "lower_limit": lower,
                    "upper_limit": upper,
                    "percent": percent,
                    "fixed_amount": fixed
                })

            slab_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Inserted default tax slabs for currency: {currency}")