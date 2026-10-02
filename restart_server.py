import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
stdin, stdout, stderr = ssh.exec_command("echo 'Farai@#$1234' | sudo -S supervisorctl restart all")
print(stdout.read().decode('utf-8', errors='ignore'))
print(stderr.read().decode('utf-8', errors='ignore'))
ssh.close()
print('Done.')
