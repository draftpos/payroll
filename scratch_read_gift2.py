import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    stdin, stdout, stderr = ssh.exec_command('cat /home/frappe/frappe-bench/apps/frappe/frappe/check_gift2.py')
    print('check_gift2.py:')
    print(stdout.read().decode())
    
    stdin, stdout, stderr = ssh.exec_command('cat /home/frappe/frappe-bench/apps/frappe/frappe/amend_pe.py')
    print('amend_pe.py:')
    print(stdout.read().decode())
except Exception as e:
    print(e)
