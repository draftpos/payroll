import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('pungwebreweries.havano.online', port=9419, username='frappe', password='Farai@#$1234')
    sftp = ssh.open_sftp()
    remote_path = '/home/frappe/frappe-bench/apps/cash_book/cash_book/cah_book/report/statement_of_profit_or_loss_and_comprehensive_income/statement_of_profit_or_loss_and_comprehensive_income.py'
    local_path = 'Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/statement_of_profit_or_loss_and_comprehensive_income.py'
    sftp.put(local_path, remote_path)
    sftp.close()
    print("Report uploaded successfully.")
except Exception as e:
    print(e)
