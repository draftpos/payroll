import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_13.py
import frappe
import json

def run():
    # Let's get the latest PE that is NOT Gift
    pes = frappe.get_all("Havano Payroll Entry", 
        order_by="modified desc", limit=5)
        
    for pe in pes:
        doc = frappe.get_doc("Havano Payroll Entry", pe.name)
        if doc.first_name.lower() != 'gift':
            print(f"PE: {pe.name}, First Name: {doc.first_name}, Leave Balances: {doc.leave_balances}, Total Leave Taken: {getattr(doc, 'total_leave_taken', None)}")
            break
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_13.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    print('OUTPUT:', output)
except Exception as e:
    print(e)
