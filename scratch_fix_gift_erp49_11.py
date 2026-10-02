import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_11.py
import frappe
import json

def run():
    emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
    if not emps:
        emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
        
    emp_name = emps[0].name
    emp_doc = frappe.get_doc("havano_employee", emp_name)
    
    first_name = emp_doc.first_name
    last_name = emp_doc.last_name
    
    pes = frappe.get_all("Havano Payroll Entry", 
        filters={"first_name": first_name, "last_name": last_name, "payroll_period": ["like", "%sept%"]}, 
        order_by="modified desc")
        
    if not pes:
        pes = frappe.get_all("Havano Payroll Entry", 
            filters={"first_name": first_name, "last_name": last_name}, 
            order_by="modified desc", limit=1)
            
    pe = pes[0]
    doc = frappe.get_doc("Havano Payroll Entry", pe.name)
    print("Leave balance is now: " + str(doc.leave_balances))
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_11.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    print('OUTPUT:', output)
except Exception as e:
    print(e)
