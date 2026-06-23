import frappe
from havano_zim_payroll.havano_zim_payroll.report.fds_paye_report.fds_paye_report import get_data
def execute():
    res = get_data({"year": "2026"})
    print(res)
