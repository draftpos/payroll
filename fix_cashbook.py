import paramiko
import json

def fix_all_tables_custom_type():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("pungwebreweries.havano.online", port=9419, username="frappe", password="Farai@#$1234")
        
        script = """
import frappe
import json

def fix():
    try:
        updated_gle = 0
        
        # 2. Fix GL Entry (since modified wasn't updated, we find by account and empty custom_type)
        gle_rows = frappe.get_all("GL Entry", 
            filters={
                "account": "Hiring Balances - PB"
            }, 
            fields=["name", "custom_type"]
        )
        for r in gle_rows:
            if not r.custom_type or r.custom_type != "Administrative Expenses":
                frappe.db.set_value("GL Entry", r.name, "custom_type", "Administrative Expenses", update_modified=False)
                updated_gle += 1

        frappe.db.commit()
        
        print("JSON_START")
        print(json.dumps({"success": True, "updated_gle": updated_gle}))
        print("JSON_END")
    except Exception as e:
        frappe.db.rollback()
        print("JSON_START")
        print(json.dumps({"error": str(e)}))
        print("JSON_END")
"""
        command_console = f"""cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/fix_cbe.py
{script}
EOF
cd /home/frappe/frappe-bench && bench --site pungwebreweries.havano.online execute frappe.fix_cbe.fix
"""
        stdin, stdout, stderr = ssh.exec_command(command_console)
        output = stdout.read().decode('utf-8')
        is_json = False
        json_str = ""
        for line in output.split('\n'):
            if "JSON_START" in line: is_json = True; continue
            if "JSON_END" in line: is_json = False; continue
            if is_json: json_str += line
        if json_str:
            print(json.loads(json_str))
        else:
            print("Output:", output[:500])
    except Exception as e:
        print("Error:", e)
    finally:
        ssh.close()

if __name__ == "__main__":
    fix_all_tables_custom_type()
