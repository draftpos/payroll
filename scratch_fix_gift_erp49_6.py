import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_6.py
import frappe
import json

def run():
    try:
        pes = frappe.get_all("Havano Payroll Entry", order_by="modified desc", limit=1)
        if not pes:
            print("No Payroll Entry found")
            return
            
        pe = pes[0]
        doc = frappe.get_doc("Havano Payroll Entry", pe.name)
        
        emp_list = []
        for df in doc.meta.get("fields", {"fieldtype": "Table"}):
            if df.fieldtype == "Table":
                for row in doc.get(df.fieldname):
                    emp_list.append(getattr(row, "employee", "None") + " - " + getattr(row, "employee_name", "None"))
                    
        print(f"Employees in {pe.name}:")
        print(json.dumps(emp_list, indent=2))
    except Exception as e:
        import traceback
        print(f"Error: {e}")
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_6.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
