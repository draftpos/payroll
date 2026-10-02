import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('erp49.havano.cloud', port=9419, username='frappe', password='Farai@#$1234')
    stdin, stdout, stderr = ssh.exec_command('ls -1 /home/frappe/frappe-bench/sites')
    print('ALL SITES:')
    print(stdout.read().decode())
except Exception as e:
    print(e)
