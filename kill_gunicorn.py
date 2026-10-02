import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    command = "pkill gunicorn"
    stdin, stdout, stderr = ssh.exec_command(command)
    print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
    print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(e)
