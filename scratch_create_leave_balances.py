import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    command = """cat << 'EOF' > /home/frappe/frappe-bench/apps/frappe/frappe/agent_create_leave_balances_erp49.py
import frappe

def run():
    try:
        # Gift
        gift = frappe.get_all("havano_employee", filters={"first_name": ["like", "%gift%"]})
        if gift:
            gift_name = gift[0].name
            lb = frappe.get_all("Havano Leave Balances", filters={"employee": gift_name, "havano_leave_type": "Annual Leave"})
            if not lb:
                doc = frappe.new_doc("Havano Leave Balances")
                doc.employee = gift_name
                doc.havano_leave_type = "Annual Leave"
                doc.leave_balance = 7.0
                doc.save(ignore_permissions=True)
                print(f"Created Leave Balance for Gift (7.0)")
            else:
                doc = frappe.get_doc("Havano Leave Balances", lb[0].name)
                doc.leave_balance = 7.0
                doc.save(ignore_permissions=True)
                print(f"Updated Leave Balance for Gift to 7.0")
        else:
            print("Gift not found")

        # Josiline
        jos = frappe.get_all("havano_employee", filters={"first_name": ["like", "%joseline%"]})
        if jos:
            jos_name = jos[0].name
            lb = frappe.get_all("Havano Leave Balances", filters={"employee": jos_name, "havano_leave_type": "Annual Leave"})
            if not lb:
                doc = frappe.new_doc("Havano Leave Balances")
                doc.employee = jos_name
                doc.havano_leave_type = "Annual Leave"
                doc.leave_balance = 7.5
                doc.save(ignore_permissions=True)
                print(f"Created Leave Balance for Josiline (7.5)")
            else:
                doc = frappe.get_doc("Havano Leave Balances", lb[0].name)
                doc.leave_balance = 7.5
                doc.save(ignore_permissions=True)
                print(f"Updated Leave Balance for Josiline to 7.5")
        else:
            print("Josiline not found")
            
        frappe.db.commit()
    except Exception as e:
        import traceback
        print("Error: " + traceback.format_exc())
EOF
cd /home/frappe/frappe-bench && bench --site erp49.havano.cloud execute frappe.agent_create_leave_balances_erp49.run
"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    print('OUTPUT:', output)
except Exception as e:
    print(e)
