import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_list_josiline_erp49.py
import frappe
import json

def run():
    emps = frappe.get_all("havano_employee", fields=["name", "first_name", "last_name", "employee_name"])
    found = []
    for emp in emps:
        for val in emp.values():
            if val and "jos" in str(val).lower():
                found.append(emp)
                break
    print(json.dumps(found, indent=2))
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_list_josiline_erp49.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    print('OUTPUT:', output)
except Exception as e:
    print(e)
