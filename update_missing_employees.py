import paramiko
import csv
import json
import traceback
from datetime import datetime

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Assuming DD/MM/YYYY format based on sample data
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            # Fallback if some dates are MM/DD/YYYY or similar
            return datetime.strptime(date_str.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

def update_employees():
    csv_file = r"C:\Users\Ashley\OneDrive\Desktop\Master_Contact_Directory_ Havano Template3578a7.csv"
    
    csv_employees = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_employees.append(row)
            
    print(f"Loaded {len(csv_employees)} employees from CSV.")

    # Prepare payload for remote script
    payload = []
    for row in csv_employees:
        salary_str = row.get("Basic Salary", "").replace(",", "").strip()
        salary = float(salary_str) if salary_str else 0.0
        
        payload.append({
            "first_name": row.get("First Name", "").strip(),
            "last_name": row.get("Last Name", "").strip(),
            "gender": row.get("Gender", "").strip(),
            "company": row.get("Company", "").strip(),
            "status": row.get("Status", "").strip(),
            "date_of_joining": parse_date(row.get("Date of Joining")),
            "date_of_birth": parse_date(row.get("Date of Birth")),
            "cell_number": row.get("Mobile", "").strip(),
            "ctc": salary,
            "salary_mode": row.get("Salary Mode", "").strip(),
            "bank_ac_no": row.get("Payment Account", "").strip(),
        })

    payload_json = json.dumps(payload)

    print("Connecting to server via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("erp1591.havano.cloud", port=9419, username="frappe", password="Farai@#$1234")
        
        script = f"""
import frappe
import json

def update_data():
    try:
        payload = json.loads(r'''{payload_json}''')
        
        # Get existing employees
        existing_emps = frappe.get_all("Employee", fields=["name", "first_name", "last_name", "ctc"])
        emp_map = {{}}
        for e in existing_emps:
            full_name = f"{{e.first_name or ''}} {{e.last_name or ''}}".strip().lower()
            emp_map[full_name] = e
            
        updated = 0
        created = 0
        errors = []
        
        for data in payload:
            full_name = f"{{data['first_name']}} {{data['last_name']}}".strip().lower()
            
            if not data['first_name']:
                continue
                
            try:
                if full_name in emp_map:
                    # Update existing if needed
                    emp = emp_map[full_name]
                    if data['ctc'] and not emp.ctc:
                        doc = frappe.get_doc("Employee", emp.name)
                        doc.ctc = data['ctc']
                        doc.save(ignore_permissions=True)
                        updated += 1
                else:
                    # Create new employee
                    doc = frappe.new_doc("Employee")
                    doc.first_name = data['first_name']
                    doc.last_name = data['last_name']
                    doc.gender = data['gender'] or "Female"
                    doc.company = data['company'] or "Cairde Trading"
                    doc.status = data['status'] or "Active"
                    
                    if data['date_of_joining']:
                        doc.date_of_joining = data['date_of_joining']
                    if data['date_of_birth']:
                        doc.date_of_birth = data['date_of_birth']
                        
                    doc.cell_number = data['cell_number']
                    doc.ctc = data['ctc']
                    doc.salary_mode = data['salary_mode']
                    doc.bank_ac_no = data['bank_ac_no']
                    
                    doc.insert(ignore_permissions=True, ignore_mandatory=True)
                    created += 1
            except Exception as ex:
                errors.append(f"Error for {{data['first_name']}} {{data['last_name']}}: {{str(ex)}}")
                
        frappe.db.commit()
        
        print("JSON_START")
        print(json.dumps({{"updated": updated, "created": created, "errors": errors}}))
        print("JSON_END")
    except Exception as e:
        print("JSON_START")
        print(json.dumps({{"error": str(e)}}))
        print("JSON_END")
"""
        print("Executing update script on remote server... This may take a moment.")
        command_console = f"""cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/update_emp.py
{script}
EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.update_emp.update_data
"""
        stdin, stdout, stderr = ssh.exec_command(command_console)
        output = stdout.read().decode('utf-8')
        
        is_json = False
        json_str = ""
        for line in output.split('\n'):
            if "JSON_START" in line:
                is_json = True
                continue
            if "JSON_END" in line:
                is_json = False
                continue
            if is_json:
                json_str += line
                
        if json_str:
            try:
                result = json.loads(json_str)
                if "error" in result:
                    print("Remote script error:", result["error"])
                else:
                    print(f"Successfully created: {result.get('created', 0)} employees.")
                    print(f"Successfully updated: {result.get('updated', 0)} employees.")
                    if result.get('errors'):
                        print("\nErrors encountered:")
                        for err in result['errors']:
                            print(err)
            except Exception as e:
                print("JSON parsing error:", e)
        else:
            print("Failed to find JSON data in output.")
            
    except Exception as e:
        print("Error:")
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == "__main__":
    update_employees()
