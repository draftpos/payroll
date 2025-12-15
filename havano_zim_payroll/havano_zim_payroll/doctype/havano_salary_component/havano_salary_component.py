# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class havano_salary_component(Document):
	def validate(self):
		component = (self.salary_component or "").strip().upper()

		if self.type == "Deduction" and self.track_nassa:
			frappe.throw("NASSA cannot be tracked on Deduction components.")

		allowed_always_calculate = {"NSSA", "PAYEE", "AIDS LEVY"}

		if component not in allowed_always_calculate and self.always_calculate:
			frappe.throw(
				"Only NSSA, PAYE and AIDS Levy components can be set to always calculate."
			)
