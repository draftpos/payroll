import paramiko
import json
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_10.py
import frappe
import json

def run():
    try:
        emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
        if not emps:
            emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
            
        emp_name = emps[0].name
        emp_doc = frappe.get_doc("havano_employee", emp_name)
        
        first_name = emp_doc.first_name
        last_name = emp_doc.last_name
        
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
            
            leave_balance = getattr(emp_doc, "leave_balance", 0.0)
            
            if getattr(doc, "leave_balances", None) != leave_balance:
                doc.leave_balances = leave_balance
                
                # Unlock
                summaries = frappe.get_all('Salary Summary On Payroll Run', filters={'completed': 'yes'})
                locked_docs = []
                for s in summaries:
                    sdoc = frappe.get_doc('Salary Summary On Payroll Run', s.name)
                    sdoc.completed = 'no'
                    sdoc.save(ignore_permissions=True)
                    locked_docs.append(sdoc)
                frappe.db.commit()
                
                # Save
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                
                # Relock
                for sdoc in locked_docs:
                    sdoc.completed = 'yes'
                    sdoc.save(ignore_permissions=True)
                frappe.db.commit()
                
                print(json.dumps({"success": True, "message": f"Updated {pe.name} leave_balances to {leave_balance}"}))
            else:
                print(json.dumps({"success": True, "message": f"{pe.name} already has leave_balances {leave_balance}"}))
        else:
            print(json.dumps({"error": f"No Payroll Entry found for {first_name} {last_name}"}))
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_10.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
