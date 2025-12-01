# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class havano_salary_component(Document):
		
	def validate(self):
			if self.type == "Deduction" and self.track_nassa == 1:  # make sure field name is correct
				frappe.throw("NASSA cannot be tracked on Deduction components.")