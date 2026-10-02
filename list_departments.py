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

def get_depts():
    try:
        depts = frappe.get_all("Department", fields=["name", "department_name", "company"])
        print(json.dumps({"success": True, "departments": depts}))
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
"""
        command_console = f"""cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/get_depts.py
{script}
EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.get_depts.get_depts
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
