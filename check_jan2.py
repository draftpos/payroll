import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_check_jan2.py
import frappe
def run():
    print("Jan Floor Cleaner:")
    print(frappe.db.get_list('Stock Ledger Entry', filters={'item_code': 'FLOOR CLEANER (kgs)', 'warehouse': 'Stores - PB', 'posting_date': '2026-01-31', 'is_cancelled': 0}, fields=['voucher_type', 'voucher_no', 'qty_after_transaction'], limit=1))
    print("Jan Tank Cleaner:")
    print(frappe.db.get_list('Stock Ledger Entry', filters={'item_code': 'TANK CLEANER (LTRS )', 'warehouse': 'Stores - PB', 'posting_date': '2026-01-31', 'is_cancelled': 0}, fields=['voucher_type', 'voucher_no', 'qty_after_transaction'], limit=1))
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_check_jan2.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
