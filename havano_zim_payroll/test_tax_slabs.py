import frappe

def execute():
    try:
        slab = frappe.get_doc("Havano Tax Slab", "USD-Monthly")
        print("USD-Monthly Brackets:")
        for b in slab.tax_brackets:
            print(f"{b.lower_limit} - {b.upper_limit}: {b.percent}% (Deduct {b.fixed_amount})")
    except Exception as e:
        print("Error fetching USD-Monthly:", e)

    try:
        slab = frappe.get_doc("Havano Tax Slab", "USD-Annual")
        print("\nUSD-Annual Brackets:")
        for b in slab.tax_brackets:
            print(f"{b.lower_limit} - {b.upper_limit}: {b.percent}% (Deduct {b.fixed_amount})")
    except Exception as e:
        print("Error fetching USD-Annual:", e)
