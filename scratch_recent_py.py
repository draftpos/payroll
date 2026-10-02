import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    stdin, stdout, stderr = ssh.exec_command('find /home/frappe/frappe-bench -name "*.py" -type f -mtime -5')
    print('RECENT PYTHON FILES:')
    print(stdout.read().decode())
except Exception as e:
    print(e)
