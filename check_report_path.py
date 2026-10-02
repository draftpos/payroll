import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_check_report_path.py
import frappe
import os
def run():
    report_name = 'Statement of Profit or Loss and Comprehensive Income'
    doc = frappe.get_doc('Report', report_name)
    module_path = frappe.get_module_path(doc.module)
    report_folder = os.path.join(module_path, 'report', frappe.scrub(doc.name))
    print(f"Path: {report_folder}")
    if os.path.exists(report_folder):
        print("Folder exists.")
        print(os.listdir(report_folder))
    else:
        print("Folder does not exist.")
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_check_report_path.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
