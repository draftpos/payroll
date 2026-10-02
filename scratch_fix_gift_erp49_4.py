import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_4.py
import frappe
import json

def run():
    try:
        # Find employee Gift
        emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
        if not emps:
            emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
        if not emps:
            print(json.dumps({"error": "Employee Gift not found in havano_employee"}))
            return
            
        emp_name = emps[0].name
        emp_doc = frappe.get_doc("havano_employee", emp_name)
        
        # Get the leave balance from havano_employee
        leave_balance = getattr(emp_doc, "leave_balance", 0.0)
        
        pes = frappe.get_all("Havano Payroll Entry", order_by="modified desc", limit=1)
        if not pes:
            print(json.dumps({"error": "No Payroll Entry found"}))
            return
            
        pe = pes[0]
        doc = frappe.get_doc("Havano Payroll Entry", pe.name)
        
        found_gift = False
        updated = False
        for df in doc.meta.get("fields", {"fieldtype": "Table"}):
            if df.fieldtype == "Table":
                for row in doc.get(df.fieldname):
                    if getattr(row, "employee", "") == emp_name:
                        found_gift = True
                        if getattr(row, "leave_balance", None) != leave_balance:
                            row.leave_balance = leave_balance
                            updated = True
                        break
                if found_gift:
                    break
        
        if not found_gift:
            print(json.dumps({"success": False, "message": f"{emp_name} not found in Payroll Entry {pe.name}"}))
            return
            
        if updated:
            summaries = frappe.get_all('Salary Summary On Payroll Run', filters={'completed': 'yes'})
            locked_docs = []
            for s in summaries:
                sdoc = frappe.get_doc('Salary Summary On Payroll Run', s.name)
                sdoc.completed = 'no'
                sdoc.save(ignore_permissions=True)
                locked_docs.append(sdoc)
            frappe.db.commit()
            
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            for sdoc in locked_docs:
                sdoc.completed = 'yes'
                sdoc.save(ignore_permissions=True)
            frappe.db.commit()
            
            print(json.dumps({"success": True, "message": f"Updated leave balance for {emp_name} in PE {pe.name} to {leave_balance}"}))
        else:
            print(json.dumps({"success": True, "message": f"{emp_name} leave balance already correct ({leave_balance}) in PE {pe.name}."}))
        
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_4.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
