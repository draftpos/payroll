# havano_zim_payroll/hooks.py

fixtures = [
    # Client Scripts for your module
    {
        "doctype": "Client Script",
        "filters": [
            ["module", "=", "Havano Zim Payroll"]
        ]
    },
    # Print Formats for your module
    {
        "doctype": "Print Format",
        "filters": [
            ["module", "=", "Havano Zim Payroll"]
        ]
    },
    # Salary Components
    {
        "doctype": "havano_salary_component",
        "filters": [["name", "in", ["Basic Salary", "PAYEE", "NSSA", "NEC", "Aids Levy"]]]
    },
    # Custom Field for Company
    {
        "doctype": "Custom Field",
        "filters": [["name", "in", ["custom_payslip_type-company"]]]
    },
    # Havano Leave Types
    {
        "doctype": "Havano Leave Type",
        "filters": [["name", "in", ["Maternity Leave", "Annual Leave", "Sick Leave", "Bereavement Leave", "Special Leave", "Study Leave"]]]
    }
]
