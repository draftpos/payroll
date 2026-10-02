import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_cancel_recon.py
import frappe
def run():
    frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
    frappe.db.commit()
    
    recons = [f"MAT-RECO-2026-0007{i}" for i in range(2, 10)] + []
    for r in recons:
        try:
            doc = frappe.get_doc("Stock Reconciliation", r)
            if doc.docstatus == 1:
                doc.cancel()
                print(f"Cancelled {r}")
        except Exception as e:
            print(f"Could not cancel {r}: {e}")
            
    frappe.db.commit()
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_cancel_recon.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
    err = stderr.read().decode('utf-8', errors='ignore')
    if err:
        print("STDERR:", err)
except Exception as e:
    print(e)
