import frappe
import openpyxl

def execute(file_path):
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    
    # Mapping month strings to month numbers
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    
    # Temporary store to aggregate data per employee per year
    # Structure: {(employee_tin, tax_year): { 'month_1_usd': X, ... }}
    aggregated_data = {}
    
    # Read rows skipping header
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
            
        emp_tin = str(row[0]).strip()
        name = row[1]
        tax_year = str(row[2]).strip()
        tax_period = str(row[3]).strip()
        # Get only the USD amount as requested
        tax_usd = frappe.utils.flt(row[4])
        
        month_num = month_map.get(tax_period)
        if not month_num:
            continue
            
        key = (emp_tin, tax_year)
        if key not in aggregated_data:
            aggregated_data[key] = {
                "name": name,
                "months": {}
            }
            
        aggregated_data[key]["months"][month_num] = {
            "usd": tax_usd
        }
        
    # Insert or update into Havano Historical PAYE
    for (emp_tin, tax_year), data in aggregated_data.items():
        # Find employee
        emp = frappe.get_all("havano_employee", filters={"employee_number": emp_tin}, limit=1)
        if not emp:
            # Let's try matching by name
            first_name = data["name"].split(" ")[0]
            emp = frappe.get_all("havano_employee", filters={"first_name": ["like", f"%{first_name}%"]}, limit=1)
            
        if not emp:
            print(f"Could not find employee for TIN {emp_tin} / Name {data['name']}")
            continue
            
        emp_name = emp[0].name
        
        # Check if record exists
        existing = frappe.get_all("Havano Historical PAYE", filters={"employee": emp_name, "tax_year": tax_year}, limit=1)
        if existing:
            doc = frappe.get_doc("Havano Historical PAYE", existing[0].name)
        else:
            doc = frappe.new_doc("Havano Historical PAYE")
            doc.employee = emp_name
            doc.tax_year = tax_year
            
        for month_num, amounts in data["months"].items():
            doc.set(f"month_{month_num}_usd", amounts["usd"])
            
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
    print("Import successfully completed!")
