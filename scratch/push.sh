#!/bin/bash
cd /home/ashley/frappe-bench-v15/apps/havano_zim_payroll
git add havano_zim_payroll/api.py
git commit -m "fix: Prevent validation errors and child table overwrites from crashing payroll loop for employees with cash in lieu"
git push
