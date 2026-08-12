import frappe

def fix_zgw_slabs():
    frappe.init(site="v15.local")
    frappe.connect()
    
    slabs = frappe.get_all("Havano Tax Brackets", filters={"parent": "ZWL"}, fields=["name", "percent"])
    for slab in slabs:
        if slab.percent < 1.0 and slab.percent > 0: # It's like 0.2, 0.25
            new_percent = slab.percent * 100
            frappe.db.set_value("Havano Tax Brackets", slab.name, "percent", new_percent)
            print(f"Updated {slab.name}: {slab.percent} -> {new_percent}")
    
    frappe.db.commit()
    print("Fixed ZWL percentages.")

if __name__ == "__main__":
    fix_zgw_slabs()
