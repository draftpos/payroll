import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_12.py
import frappe
import json

def run():
    emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
    if not emps:
        emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
        
    emp_name = emps[0].name
    emp_doc = frappe.get_doc("havano_employee", emp_name)
    
    print("Fields in havano_employee related to leave:")
    for f in emp_doc.meta.fields:
        if 'leave' in f.fieldname.lower():
            print(f"{f.fieldname}: {getattr(emp_doc, f.fieldname, None)}")
            
    # Maybe it's leave_balances instead of leave_balance?
    print(f"leave_balances: {getattr(emp_doc, 'leave_balances', 'Not found')}")
    print(f"leave_balance: {getattr(emp_doc, 'leave_balance', 'Not found')}")
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_12.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    print('OUTPUT:', output)
except Exception as e:
    print(e)
