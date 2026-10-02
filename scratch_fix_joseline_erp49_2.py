import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_joseline_payroll_erp49_2.py
import frappe

def run():
    try:
        first_name = "JOSELINE"
        last_name = "CHITSINDE"
        
        pes = frappe.get_all("Havano Payroll Entry", 
            filters={"first_name": first_name, "last_name": last_name, "payroll_period": ["like", "%sept%"]}, 
            order_by="modified desc")
            
        if not pes:
            pes = frappe.get_all("Havano Payroll Entry", 
                filters={"first_name": first_name, "last_name": last_name}, 
                order_by="modified desc", limit=1)
                
        if pes:
            pe = pes[0]
            doc = frappe.get_doc("Havano Payroll Entry", pe.name)
            
            doc.leave_balances = "7.5"
            
            # Unlock
            summaries = frappe.get_all('Salary Summary On Payroll Run', filters={'completed': 'yes'})
            locked_docs = []
            for s in summaries:
                sdoc = frappe.get_doc('Salary Summary On Payroll Run', s.name)
                sdoc.completed = 'no'
                sdoc.save(ignore_permissions=True)
                locked_docs.append(sdoc)
            frappe.db.commit()
            
            # Save PE
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            # Relock
            for sdoc in locked_docs:
                sdoc.completed = 'yes'
                sdoc.save(ignore_permissions=True)
            frappe.db.commit()
            
            print("Successfully updated Joseline's leave balance to 7.5 on PE: " + pe.name)
        else:
            print("Error: No Payroll Entry found for " + first_name + " " + last_name)
            
    except Exception as e:
        print("Error: " + str(e))
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_joseline_payroll_erp49_2.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    print('OUTPUT:', output)
except Exception as e:
    print(e)
