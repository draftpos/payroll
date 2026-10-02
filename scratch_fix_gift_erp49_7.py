import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_7.py
import frappe
import json

def run():
    try:
        pes = frappe.get_all("Havano Payroll Entry", order_by="modified desc", limit=1)
        pe = pes[0]
        doc = frappe.get_doc("Havano Payroll Entry", pe.name)
        
        table_meta = None
        for df in doc.meta.get("fields", {"fieldtype": "Table"}):
            if df.fieldtype == "Table":
                table_meta = frappe.get_meta(df.options)
                print(f"Table Name: {df.fieldname}")
                print(f"Fields: {[f.fieldname for f in table_meta.fields]}")
                break
                
        # Find employee Gift
        emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
        if not emps:
            emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
            
        emp_name = emps[0].name
        
        lbs = frappe.get_all("Havano Leave Balances", filters={"employee": emp_name}, fields=["havano_leave_type", "leave_balance"])
        
        found = False
        for df in doc.meta.get("fields", {"fieldtype": "Table"}):
            if df.fieldtype == "Table":
                for row in doc.get(df.fieldname):
                    if getattr(row, "havano_employee", "") == emp_name or getattr(row, "employee", "") == emp_name:
                        found = True
                        if hasattr(row, "leave_balance") and lbs:
                            row.leave_balance = lbs[0].leave_balance
                            
        if found:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            print("Successfully updated Gift's leave balance in Payroll Entry!")
        else:
            print("Gift not found in Payroll Entry even after checking correct fields.")
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_7.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
