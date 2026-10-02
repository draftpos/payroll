import paramiko
import json

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
        print(json.dumps({"items": items, "warehouses": warehouses}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_check_items.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("STDERR:", err)
except Exception as e:
    print(e)
