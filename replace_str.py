path = '/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/havano_zim_payroll/api.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('period_name = f"{month_name} {year}"', 'PERIOD_NAME_ASSIGNMENT_PLACEHOLDER')
content = content.replace('f"{month_name} {year}"', 'period_name')
content = content.replace('PERIOD_NAME_ASSIGNMENT_PLACEHOLDER', 'period_name = f"{month_name} {year}"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
