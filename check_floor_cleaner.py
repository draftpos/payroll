import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_check_fc.py
import frappe
def run():
    print("FLOOR CLEANER:")
    print(frappe.db.get_list('Stock Ledger Entry', filters={'item_code': 'FLOOR CLEANER (kgs)', 'warehouse': 'Stores - PB'}, fields=['posting_date', 'qty_after_transaction'], order_by='posting_date desc', limit=1))
    print("TANK CLEANER:")
    print(frappe.db.get_list('Stock Ledger Entry', filters={'item_code': 'TANK CLEANER (LTRS )', 'warehouse': 'Stores - PB'}, fields=['posting_date', 'qty_after_transaction'], order_by='posting_date desc', limit=1))
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_check_fc.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
