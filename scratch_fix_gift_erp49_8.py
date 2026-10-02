import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_8.py
import frappe
import json

def run():
    try:
        # Find employee Gift
        emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
        if not emps:
            emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
            
        emp_name = emps[0].name
        
        # Get Havano Payroll Entry for this employee
        pes = frappe.get_all("Havano Payroll Entry", filters={"employee": emp_name})
        if pes:
            pe = pes[0]
            doc = frappe.get_doc("Havano Payroll Entry", pe.name)
            
            # Fetch the leave balance from havano_employee
            emp_doc = frappe.get_doc("havano_employee", emp_name)
            leave_balance = getattr(emp_doc, "leave_balance", 0.0)
            
            if getattr(doc, "leave_balance", None) != leave_balance:
                doc.leave_balance = leave_balance
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                print(json.dumps({"success": True, "message": f"Updated {pe.name} leave_balance to {leave_balance}"}))
            else:
                print(json.dumps({"success": True, "message": f"{pe.name} already has leave_balance {leave_balance}"}))
        else:
            print(json.dumps({"error": f"No Payroll Entry found for {emp_name}"}))
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_8.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
