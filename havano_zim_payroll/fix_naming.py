import frappe
from frappe.model.naming import make_autoname

def fix_naming():
    reports = {
        "NSSA P4 Report Store": "NSSAP4-.####",
        "ZIMRA P2FORM": "P2-.####",
        "Reports Store NASSA": "NSSAS-.####",
        "NEC Report": "NEC-.####",
        "ZIMRA ITF16": "ITF16-.####",
        "SDL Report": "SDL-.####",
        "Havano Payroll Entry": "HPE-.####",
        "Employee Payment Processing": "EPP-.####",
        "Havano Employee Overtime": "HEO-.####",
        "Havano Bulk Overtime Employees": "HBOE-.####",
        "Hours Worked": "HW-.####"
    }

    for doctype, autoname in reports.items():
        if not frappe.db.exists("DocType", doctype) or not frappe.db.table_exists(doctype): 
            continue
            
        prefix = autoname.split(".#")[0]
        
        # We need to make sure the DocType is updated first in DB
        doc_meta = frappe.get_doc("DocType", doctype)
        if doc_meta.autoname != autoname:
            doc_meta.autoname = autoname
            doc_meta.naming_rule = ""
            doc_meta.save(ignore_permissions=True)
            frappe.db.commit()
            
        records = frappe.get_all(doctype, fields=["name"])
        for rec in records:
            if not str(rec.name).startswith(prefix):
                new_name = make_autoname(autoname)
                print(f"Renaming {doctype} {rec.name} to {new_name}")
                try:
                    frappe.rename_doc(doctype, rec.name, new_name, force=True)
                except Exception as e:
                    if "Incorrect integer value" in str(e) or "DataError" in str(type(e)):
                        print(f"Converting name column of {doctype} to VARCHAR(140) to fix BIGINT conflict...")
                        frappe.db.sql(f"ALTER TABLE `tab{doctype}` MODIFY name VARCHAR(140);")
                        frappe.rename_doc(doctype, rec.name, new_name, force=True)
                    else:
                        raise e
                frappe.db.commit()
    
    print("Done fixing naming for existing records.")
