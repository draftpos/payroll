import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_check_report.py
import frappe
import json
def run():
    reports = frappe.db.get_list('Report', filters={'name': ('like', '%Profit%')}, fields=['name', 'module', 'report_type', 'is_standard'])
    print(json.dumps(reports, indent=2))
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_check_report.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
