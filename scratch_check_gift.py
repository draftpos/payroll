import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_check_gift.py
import frappe
import json

def run():
    try:
        # Find employee Gift
        emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%Gift%"]}, fields=["name", "employee_name"])
        if not emps:
            print(json.dumps({"error": "Employee Gift not found"}))
            return
            
        emp = emps[0]
        emp_doc = frappe.get_doc("havano_employee", emp.name)
        
        # Check Payroll Entries for Sept
        pes = frappe.get_all("havano_payroll_entry", filters={"employee": emp.name, "salary_month": "September"}, fields=["name", "salary_month", "leave_balance"])
        
        print("JSON_START")
        print(json.dumps({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "havano_employee_leave_balance": getattr(emp_doc, "leave_balance", "Not found"),
            "payroll_entries": pes
        }))
        print("JSON_END")
    except Exception as e:
        import traceback
        print("JSON_START")
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
        print("JSON_END")
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_check_gift.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
except Exception as e:
    print(e)
