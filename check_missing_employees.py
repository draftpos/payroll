import paramiko
import csv
import json
import traceback

def check_employees():
    csv_file = r"C:\Users\Ashley\OneDrive\Desktop\Master_Contact_Directory_ Havano Template3578a7.csv"
    
    csv_employees = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_employees.append(row)
            
    print(f"Loaded {len(csv_employees)} employees from CSV.")

    print("Connecting to server via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("erp1591.havano.cloud", port=9419, username="frappe", password="Farai@#$1234")
        
        script = """
import frappe
import json

def get_data():
    try:
        employees = frappe.get_all("Employee", fields=["name", "employee_name", "first_name", "last_name", "status", "ctc"])
            
        print("JSON_START")
        print(json.dumps(employees, default=str))
        print("JSON_END")
    except Exception as e:
        print("JSON_START")
        print(json.dumps({"error": str(e)}))
        print("JSON_END")
"""
        print("Executing script on remote server...")
        command_console = f"""cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/check_emp.py
{script}
EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.check_emp.get_data
"""
        stdin, stdout, stderr = ssh.exec_command(command_console)
        output = stdout.read().decode('utf-8')
        
        remote_data = []
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
                remote_data = json.loads(json_str)
                if isinstance(remote_data, dict) and "error" in remote_data:
                    print("Remote script error:", remote_data["error"])
                    return
                print(f"Loaded {len(remote_data)} employees from ERPNext.")
            except Exception as e:
                print("JSON parsing error:", e)
                return
        else:
            print("Failed to find JSON data in output.")
            return

        print("\n--- Missing or Incomplete Employees ---")
        remote_names = [f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip().lower() for e in remote_data]
        
        missing_count = 0
        incomplete_count = 0
        
        with open("C:/Users/Ashley/OneDrive/Desktop/Missing_Employees_Report.txt", "w", encoding='utf-8') as report:
            for row in csv_employees:
                fname = row.get("First Name", "").strip()
                lname = row.get("Last Name", "").strip()
                full_name = f"{fname} {lname}".strip().lower()
                csv_salary = row.get("Basic Salary", "").strip()
                
                if full_name not in remote_names:
                    msg = f"Missing completely: {fname} {lname}"
                    print(msg)
                    report.write(msg + "\n")
                    missing_count += 1
                else:
                    remote_emp = next((e for e in remote_data if f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip().lower() == full_name), None)
                    if remote_emp:
                        # Check CTC
                        has_salary = bool(remote_emp.get("ctc"))
                        
                        if csv_salary and not has_salary:
                            msg = f"Missing basic salary in ERPNext for: {fname} {lname} (CSV Salary: {csv_salary})"
                            print(msg)
                            report.write(msg + "\n")
                            incomplete_count += 1
                            
            msg = f"\nTotal missing completely: {missing_count}\nTotal missing basic salary: {incomplete_count}"
            print(msg)
            report.write(msg + "\n")
            
        print("A report was also saved to your Desktop: Missing_Employees_Report.txt")

    except Exception as e:
        print("Error:")
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == "__main__":
    check_employees()
