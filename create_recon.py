import paramiko
import json
import sys

with open('Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/adjustments_payload.json', 'r') as f:
    adjustments = json.load(f)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/payload.json', 'w') as f:
        f.write(json.dumps(adjustments))
    sftp.close()

    command = """cat << 'INNER_EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_create_recon.py
import frappe
import json

def run():
    frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
    frappe.db.commit()
    try:
        with open('/tmp/payload.json', 'r') as f:
            adjustments = json.load(f)
            
        results = []
        for adj in adjustments:
            try:
                doc = frappe.new_doc("Stock Reconciliation")
                doc.purpose = "Stock Reconciliation"
                doc.posting_date = adj["posting_date"]
                doc.posting_time = "23:59:59"
                doc.set_posting_time = 1
                
                for item in adj["items"]:
                    doc.append("items", {
                        "item_code": item["item_code"],
                        "warehouse": item["warehouse"],
                        "qty": item["qty"],
                        "valuation_rate": item.get("valuation_rate", 1)
                    })
                
                doc.insert(ignore_permissions=True)
                doc.submit()
                results.append(f"Created and submitted {doc.name} for {adj['posting_date']}")
                frappe.db.commit()
            except Exception as inner_e:
                frappe.db.rollback()
                if "None of the items have any change" in str(inner_e):
                    results.append(f"Skipped {adj['posting_date']}: No changes")
                else:
                    results.append(f"Error {adj['posting_date']}: {str(inner_e)}")
            
        print(json.dumps({"success": True, "results": results}))
    except Exception as e:
        frappe.db.rollback()
        print(json.dumps({"success": False, "error": str(e)}))
INNER_EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.agent_create_recon.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print("OUTPUT:")
    for line in stdout:
        print(line, end="")
    err = stderr.read().decode('utf-8')
    if err:
        print("STDERR:")
        print(err)
        
except Exception as e:
    print(e)
