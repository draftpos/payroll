import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    sftp = ssh.open_sftp()
    base_remote = '/home/frappe/frappe-bench/apps/havano_zim_payroll/havano_zim_payroll/havano_zim_payroll/doctype/havano_employee/'
    
    sftp.put(
        'Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/havano_zim_payroll/havano_zim_payroll/doctype/havano_employee/split_currency.py',
        base_remote + 'split_currency.py'
    )
    print("split_currency.py uploaded.")
    
    sftp.put(
        'Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/havano_zim_payroll/havano_zim_payroll/doctype/havano_employee/base_currency.py',
        base_remote + 'base_currency.py'
    )
    print("base_currency.py uploaded.")
    
    sftp.close()
    
    # Clear pycache
    stdin, stdout, stderr = ssh.exec_command(
        'rm -rf /home/frappe/frappe-bench/apps/havano_zim_payroll/havano_zim_payroll/havano_zim_payroll/doctype/havano_employee/__pycache__'
    )
    stdout.read()
    print("Pycache cleared.")
    
    # Kill gunicorn to force reload
    stdin, stdout, stderr = ssh.exec_command('pkill gunicorn')
    stdout.read()
    print("Gunicorn restarted.")
    
    ssh.close()
except Exception as e:
    print(e)
