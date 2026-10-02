import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/disable_negative.py
import frappe
def run():
    frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)
    frappe.db.commit()
    print("Disabled negative stock.")
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.disable_negative.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
