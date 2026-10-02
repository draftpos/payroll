import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_5.py
import frappe
import json

def run():
    try:
        # Find employee Gift
        emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
        if not emps:
            emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
            
        emp_name = emps[0].name
        
        # Search all Payroll Entries to see where Gift is
        pes = frappe.get_all("Havano Payroll Entry", order_by="modified desc", limit=5)
        
        found = []
        for pe in pes:
            doc = frappe.get_doc("Havano Payroll Entry", pe.name)
            for df in doc.meta.get("fields", {"fieldtype": "Table"}):
                if df.fieldtype == "Table":
                    for row in doc.get(df.fieldname):
                        emp_val = getattr(row, "employee", "")
                        emp_name_val = getattr(row, "employee_name", "")
                        if emp_name in [emp_val, emp_name_val] or "gift" in emp_val.lower() or "gift" in emp_name_val.lower():
                            found.append({"pe": pe.name, "emp_val": emp_val, "emp_name_val": emp_name_val})
                            
        print(json.dumps({"employee": emp_name, "found_in": found}))
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_5.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
