import frappe

def execute():
    """Update Havano Tax Slabs with latest ZIMRA 2025 tables for USD-Monthly and USD-Annual."""
    
    usd_monthly_brackets = [
        {"lower_limit": 0, "upper_limit": 100, "percent": 0.0, "fixed_amount": 0},
        {"lower_limit": 100, "upper_limit": 300, "percent": 20.0, "fixed_amount": 20},
        {"lower_limit": 300, "upper_limit": 1000, "percent": 25.0, "fixed_amount": 35},
        {"lower_limit": 1000, "upper_limit": 2000, "percent": 30.0, "fixed_amount": 85},
        {"lower_limit": 2000, "upper_limit": 3000, "percent": 35.0, "fixed_amount": 185},
        {"lower_limit": 3000, "upper_limit": 0, "percent": 40.0, "fixed_amount": 335}
    ]

    usd_annual_brackets = [
        {"lower_limit": 0, "upper_limit": 1200, "percent": 0.0, "fixed_amount": 0},
        {"lower_limit": 1200, "upper_limit": 3600, "percent": 20.0, "fixed_amount": 240},
        {"lower_limit": 3600, "upper_limit": 12000, "percent": 25.0, "fixed_amount": 420},
        {"lower_limit": 12000, "upper_limit": 24000, "percent": 30.0, "fixed_amount": 1020},
        {"lower_limit": 24000, "upper_limit": 36000, "percent": 35.0, "fixed_amount": 2220},
        {"lower_limit": 36000, "upper_limit": 0, "percent": 40.0, "fixed_amount": 4020}
    ]

    for slab_name, brackets in [("USD-Monthly", usd_monthly_brackets), ("USD-Annual", usd_annual_brackets)]:
        if frappe.db.exists("Havano Tax Slab", slab_name):
            doc = frappe.get_doc("Havano Tax Slab", slab_name)
            doc.tax_brackets = []
        else:
            doc = frappe.new_doc("Havano Tax Slab")
            doc.currency = slab_name

        for b in brackets:
            doc.append("tax_brackets", {
                "lower_limit": b["lower_limit"],
                "upper_limit": b["upper_limit"],
                "percent": b["percent"],
                "fixed_amount": b["fixed_amount"]
            })
            
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Updated {slab_name}")
