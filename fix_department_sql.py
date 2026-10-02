import paramiko
import traceback

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("pungwebreweries.havano.online", port=9419, username="frappe", password="Farai@#$1234")
        
        script = """
import frappe
import json

def fix_department():
    try:
        # Check if the exact name exists
        if not frappe.db.exists("Department", "Finance and Admin"):
            # Insert directly via SQL to bypass autonaming suffix
            frappe.db.sql('''
                INSERT INTO `tabDepartment` (name, department_name, company, parent_department, is_group, creation, modified, modified_by, owner, docstatus)
                VALUES ('Finance and Admin', 'Finance and Admin', 'Pungwe Breweries', 'All Departments', 0, NOW(), NOW(), 'Administrator', 'Administrator', 0)
            ''')
            frappe.db.commit()
            print(json.dumps({"success": True, "message": "Created exactly 'Finance and Admin' via SQL"}))
        else:
            print(json.dumps({"success": True, "message": "Already exists"}))
            
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
"""
        command_console = f"""cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/fix_dept.py
{script}
EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.fix_dept.fix_department
"""
        stdin, stdout, stderr = ssh.exec_command(command_console)
        output = stdout.read().decode('utf-8')
        print("OUTPUT:")
        print(output)
            
    except Exception as e:
        print("Connection/Execution Error:")
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == "__main__":
    run()
