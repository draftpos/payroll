import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = "touch /home/frappe/frappe-bench/sites/restart.txt"
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
