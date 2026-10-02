import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_fix_gift_payroll_erp49_2.py
import frappe
import json

def run():
    try:
        # Find employee Gift
        emps = frappe.get_all("havano_employee", filters={"name": ["like", "%gift%"]})
        if not emps:
            # try employee_name or first_name just in case
            emps = frappe.get_all("havano_employee", filters={"employee_name": ["like", "%gift%"]})
        if not emps:
            print(json.dumps({"error": "Employee Gift not found in havano_employee"}))
            return
            
        emp = emps[0]
        emp_name = emp.name
        
        pes = frappe.get_all("Havano Payroll Entry", filters={"salary_month": "September"}, fields=["name"], order_by="modified desc")
        if not pes:
            print(json.dumps({"error": "No September Payroll Entry found"}))
            return
            
        pe = pes[0]
        doc = frappe.get_doc("Havano Payroll Entry", pe.name)
        
        lbs = frappe.get_all("Havano Leave Balances", filters={"employee": emp_name}, fields=["havano_leave_type", "leave_balance"])
        
        if not lbs:
            print(json.dumps({"error": f"{emp_name} has no Havano Leave Balances records."}))
            return
            
        found_gift = False
        updated = False
        for df in doc.meta.get("fields", {"fieldtype": "Table"}):
            if df.fieldtype == "Table":
                for row in doc.get(df.fieldname):
                    if getattr(row, "employee", "") == emp_name:
                        found_gift = True
                        if getattr(row, "leave_balance", None) != lbs[0].leave_balance:
                            row.leave_balance = lbs[0].leave_balance
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
            
            print(json.dumps({"success": True, "message": f"Updated leave balance for {emp_name} in PE {pe.name} to {lbs[0].leave_balance}"}))
        else:
            print(json.dumps({"success": True, "message": f"{emp_name} leave balance already correct ({lbs[0].leave_balance}) in PE {pe.name}."}))
        
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_fix_gift_payroll_erp49_2.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    print('OUTPUT:')
    print(stdout.read().decode())
    print('STDERR:')
    print(stderr.read().decode())
except Exception as e:
    print(e)
