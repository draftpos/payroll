# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class havano_leave_encashment(Document):

    def before_save(self):
        # Recalculate encashment amount to keep server in sync with client
        self.encashment_amount = flt(self.days_being_encashed) * flt(self.rate_per_day)

        # Fetch current leave balance from Havano Leave Balances
        if self.employee and self.leave_type:
            balance = frappe.db.get_value(
                "Havano Leave Balances",
                {"employee": self.employee, "havano_leave_type": self.leave_type},
                "leave_balance"
            )
            self.current_leave_balance = flt(balance) if balance is not None else 0.0

        # Push the encashment amount into the employee earnings table
        self._update_employee_earnings()

    def _update_employee_earnings(self):
        """Add or update 'Cash in Lieu of Leave' in the employee's earnings table."""
        if not self.employee or not self.encashment_amount:
            return

        emp = frappe.get_doc("havano_employee", self.employee)

        # Determine which currency column to use
        company_currency = frappe.db.get_value("Company", emp.company, "default_currency") or "USD"

        # Look for an existing 'Cash in Lieu of Leave' row
        component_name = "Cash in Lieu of Leave"
        existing_row = None
        for row in emp.employee_earnings:
            if (row.components or "").strip().lower() == component_name.lower():
                existing_row = row
                break

        if existing_row:
            # Update existing row
            if company_currency == "USD":
                existing_row.amount_usd = self.encashment_amount
                existing_row.amount_zwg = 0
            else:
                existing_row.amount_usd = 0
                existing_row.amount_zwg = self.encashment_amount
            existing_row.is_tax_applicable = 1
        else:
            # Add new row
            row_data = {
                "components": component_name,
                "is_tax_applicable": 1,
                "amount_usd": self.encashment_amount if company_currency == "USD" else 0,
                "amount_zwg": self.encashment_amount if company_currency != "USD" else 0,
            }
            emp.append("employee_earnings", row_data)

        emp.save(ignore_permissions=True)
        frappe.msgprint(
            f"'Cash in Lieu of Leave' ({self.encashment_amount:.2f} {company_currency}) "
            f"has been added to {self.employee}'s earnings.",
            indicator="green",
            alert=True
        )
