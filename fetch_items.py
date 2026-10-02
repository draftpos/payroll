import paramiko
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_check_items.py
import frappe
import json

def run():
    try:
        items = frappe.get_all("Item", fields=["name", "item_name", "stock_uom"])
        warehouses = frappe.get_all("Warehouse", fields=["name", "warehouse_name"])
        with open('/tmp/agent_items.json', 'w') as f:
            json.dump({"items": items, "warehouses": warehouses}, f)
    except Exception as e:
        pass
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_check_items.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read()
    
    sftp = ssh.open_sftp()
    sftp.get('/tmp/agent_items.json', 'Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/erpnext_items.json')
    sftp.close()
    
    print("File downloaded to erpnext_items.json")
    
except Exception as e:
    print(e)
