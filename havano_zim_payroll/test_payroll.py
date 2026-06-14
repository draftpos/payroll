import frappe
from havano_zim_payroll.havano_zim_payroll.api import run_payroll

def run():
    try:
        res = run_payroll('June', '2026', None, 0)
        print('SUCCESS:', res)
    except Exception as e:
        print('ERROR:', e)
        import traceback
        traceback.print_exc()
