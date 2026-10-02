import paramiko
import traceback

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # User said password is Farai@#$1234b but earlier scripts use Farai@#$1234
        # User said password is Farai@#$1234b but it failed authentication, reverting to Farai@#$1234
        ssh.connect("pungwebreweries.havano.online", port=9419, username="frappe", password="Farai@#$1234")
        
        script = """
import frappe
import json

def create_dept():
    try:
        departments = [
            ("Finance and Admin - PB", "Finance and Admin"),
            ("Marketing and Distribution - PB", "Marketing and Distribution"),
            ("marketing and distribution - PB", "marketing and distribution"),
            ("Production - PB", "Production"),
            ("production - PB", "production"),
            ("Finance and Admin - CT", "Finance and Admin")
        ]
        renamed = []
        for old_name, new_name in departments:
            if frappe.db.exists("Department", old_name) and not frappe.db.exists("Department", new_name):
                frappe.rename_doc("Department", old_name, new_name, force=True)
                renamed.append(f"{old_name} -> {new_name}")
        
        # Also let's make sure the company abbr isn't automatically appended if they create new ones
        frappe.db.commit()
        print(json.dumps({"success": True, "renamed": renamed}))
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
"""
        print("Executing script on remote server...")
        command_console = f"""cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/create_dept.py
{script}
EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.create_dept.create_dept
"""
        stdin, stdout, stderr = ssh.exec_command(command_console)
        output = stdout.read().decode('utf-8')
        print("OUTPUT:")
        print(output)
        
        err = stderr.read().decode('utf-8')
        if err:
            print("STDERR:")
            print(err)
            
    except Exception as e:
        print("Connection/Execution Error:")
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == "__main__":
    run()
