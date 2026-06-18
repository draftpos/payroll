import frappe

def execute():
    frappe.flags.in_test = True # Bypasses any strict validation that might block renames
    
    doctypes = [
        "NEC Report",
        "SDL Report",
        "Reports Store NASSA",
        "NSSA P4 Report Store",
        "ZIMRA ITF16",
        "ZIMRA P2FORM"
    ]
    
    for dt in doctypes:
        print(f"\nUpdating existing records for {dt}...")
        try:
            records = frappe.get_all(dt, order_by="creation asc")
        except Exception:
            continue
            
        counter = 1
        for rec in records:
            if str(rec.name).isdigit():
                val = int(rec.name)
                if val >= counter:
                    counter = val + 1
                continue

            new_name = str(counter)
            while frappe.db.exists(dt, new_name):
                counter += 1
                new_name = str(counter)
            
            print(f"Renaming {rec.name} -> {new_name}")
            try:
                frappe.rename_doc(dt, rec.name, new_name, force=True)
            except Exception as e:
                print(f"Failed to rename {rec.name}: {e}")
            
            counter += 1
