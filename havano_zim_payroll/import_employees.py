import frappe
import csv
from datetime import datetime

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
        except:
            return None

def execute():
    csv_file = "/mnt/c/Users/Ashley/OneDrive/Desktop/Master_Contact_Directory_ Havano Template3578a7.csv"
    try:
        with open(csv_file, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                first_name = row.get("First Name", "").strip()
                last_name = row.get("Last Name", "").strip()
                if not first_name:
                    continue
                    
                currency = row.get("Currency", "").strip()
                category = "Zig only"
                usd_perc = 0
                zig_perc = 100
                
                if "Dual" in currency:
                    category = "Both (Zig and USD)"
                    usd_perc = 50
                    zig_perc = 50
                
                doc_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "gender": row.get("Gender", "").strip(),
                    "salary_mode": row.get("Salary Mode", "").strip(),
                    "company": row.get("Company", "").strip(),
                    "status": row.get("Status", "").strip() if row.get("Status", "").strip() else "Active",
                    "date_of_joining": parse_date(row.get("Date of Joining", "")),
                    "current_address": row.get("Address", "").strip(),
                    "date_of_birth": parse_date(row.get("Date of Birth", "")),
                    "cell_number": row.get("Mobile", "").strip(),
                    "payment_account": row.get("Payment Account", "").strip(),
                    "employee_category": category,
                    "usd_percentage": usd_perc,
                    "zig_percentage": zig_perc,
                }
                
                doc_data = {k: v for k, v in doc_data.items() if v}
                
                filters = {"first_name": first_name, "last_name": last_name}
                existing = frappe.get_all("havano_employee", filters=filters, limit=1)
                
                if existing:
                    try:
                        doc = frappe.get_doc("havano_employee", existing[0].name)
                        doc.update({
                            "employee_category": category,
                            "usd_percentage": usd_perc,
                            "zig_percentage": zig_perc,
                            "salary_mode": doc_data.get("salary_mode", doc.salary_mode),
                            "payment_account": doc_data.get("payment_account", doc.payment_account)
                        })
                        doc.save(ignore_permissions=True)
                        frappe.db.commit()
                        print(f"Updated existing: {first_name} {last_name}")
                    except Exception as e:
                        print(f"Error updating {first_name} {last_name}: {e}")
                else:
                    doc_data["doctype"] = "havano_employee"
                    if "basic_salary_calculated" not in doc_data and row.get("Basic Salary"):
                        doc_data["basic_salary_calculated"] = row.get("Basic Salary")
                    
                    try:
                        doc = frappe.get_doc(doc_data)
                        doc.insert(ignore_permissions=True)
                        frappe.db.commit()
                        print(f"Inserted new: {first_name} {last_name}")
                    except Exception as e:
                        print(f"Failed to insert {first_name} {last_name}: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error reading CSV file: {e}")
