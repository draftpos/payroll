import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate


def main(self):
	default_currency = frappe.db.get_value("Company", self.company, "default_currency")
	self.salary_currency = default_currency

	# Initialize---------------tax credits
	tax_credits_usd = 0
	tax_credits_zwg = 0

	# frappe.msgprint(str(exchange_rate))
	self.tax_credits = []

	exchange_rate = flt(
		frappe.db.get_value(
			"Currency Exchange", {"from_currency": "USD", "to_currency": "ZWL"}, "exchange_rate"
		)
		or 1
	)

	# Elderly
	if getattr(self, "is_elderly", 0):
		tax_credits_usd += 75
		tax_credits_zwg += 75 * exchange_rate
		self.elderly = 75
	else:
		self.elderly = 0

	# Blind
	if getattr(self, "is_blind", 0):
		tax_credits_usd += 75
		tax_credits_zwg += 75 * exchange_rate
		self.blind = 75
	else:
		self.blind = 0

	# Disabled
	if getattr(self, "is_disabled", 0):
		tax_credits_usd += 75
		tax_credits_zwg += 75 * exchange_rate
		self.disabled = 75
	else:
		self.disabled = 0

	# --- Create or Update havano_salary_structure ---
	if self.salary_structure:
		# Try to load existing
		try:
			salary_structure = frappe.get_doc("havano_salary_structure", self.salary_structure)
			print(f"Updating existing havano_salary_structure: {self.salary_structure}")
		except frappe.DoesNotExistError:
			salary_structure = frappe.new_doc("havano_salary_structure")
			# Assign a name since it may be Prompt autoname
			salary_structure.name = f"HSS-{self.name}-{now_datetime().strftime('%Y%m%d%H%M%S')}"
	else:
		# Create new
		salary_structure = frappe.new_doc("havano_salary_structure")
		salary_structure.name = f"HSS-{self.name}-{now_datetime().strftime('%Y%m%d%H%M%S')}"

	# --- Fill in fields ---
	salary_structure.company = self.company
	salary_structure.payroll_frequency = getattr(self, "payroll_frequency", "Monthly")

	# Clear existing child tables
	salary_structure.earnings = []
	salary_structure.deductions = []

	# Populate earnings
	# ---------------- Populate Earnings ----------------
	total_amount_basic_and_bonus_and_allowances_usd = 0
	total_amount_basic_and_bonus_and_allowances_zwg = 0
	total_ensuarable_earnings_usd = 0
	total_ensuarable_earnings_zwg = 0
	basic_salary_usd = 0
	basic_salary_zwg = 0

	for e in self.employee_earnings:
		# Capture Basic Salary
		if e.components == "Basic Salary":
			basic_salary_zwg += flt(e.amount_zwg)
			basic_salary_usd += flt(e.amount_usd)

		salary_structure.append(
			"earnings",
			{
				"components": e.components,
				"amount_zwg": e.amount_zwg,
				"amount_usd": e.amount_usd,
				"is_tax_applicable": bool(e.is_tax_applicable),
				"amount_currency": "BOTH-NO RELATION",
			},
		)
		total_amount_basic_and_bonus_and_allowances_zwg += flt(e.amount_zwg)
		total_amount_basic_and_bonus_and_allowances_usd += flt(e.amount_usd)

		if bool(e.is_tax_applicable):
			total_ensuarable_earnings_zwg += flt(e.amount_zwg)
			total_ensuarable_earnings_usd += flt(e.amount_usd)

	# frappe.msgprint(str(total_amount_basic_and_bonus_and_allowances))
	self.total_income_usd = total_amount_basic_and_bonus_and_allowances_usd
	self.total_income_zwg = total_amount_basic_and_bonus_and_allowances_zwg
	self.total_ensuarable_earnings_usd = total_ensuarable_earnings_usd
	self.total_ensuarable_earnings_zwg = total_ensuarable_earnings_zwg
	self.total_deduction_usd = 0
	self.total_deduction_zwg = 0
	medical_usd = 0
	medical_zwg = 0

	# ---------------- Populate Deductions ----------------
	total_allowable_deductions_usd = 0
	total_allowable_deductions_zwg = 0

	for d in self.employee_deductions:
		# Get the related component document
		component_doc = frappe.get_doc("havano_salary_component", d.components)

		# If NSSA, calculate 4.5% of Basic Salary
		if d.components == "NSSA":
			if flt(self.total_ensuarable_earnings_usd) >= component_doc.usd_ceiling:
				nassa_usd = component_doc.usd_ceiling_amount
			else:
				nassa_usd = flt(self.total_ensuarable_earnings_usd) * 0.045
			if flt(self.total_ensuarable_earnings_zwg) >= component_doc.zwg_ceiling:
				nassa_zwg = component_doc.zwg_ceiling_amount
			else:
				nassa_zwg = flt(self.total_ensuarable_earnings_zwg) * 0.045

			d.amount_usd = nassa_usd
			d.amount_zwg = nassa_zwg

			self.total_deduction_usd += flt(nassa_usd)
			self.total_deduction_zwg += flt(nassa_zwg)

		# If Medical Aid, apply employer percentage
		elif d.components.upper() in ["MEDICAL AID", "CIMAS"]:
			medical_zwg = flt(d.amount_zwg)
			medical_usd = flt(d.amount_usd)

			emp_cimas_usd = medical_usd * flt(self.cimas_employee_) / 100
			emp_cimas_zwg = medical_zwg * flt(self.cimas_employee_) / 100

			# 50% of employee contribution as tax credit
			tax_credits_usd += emp_cimas_usd * 0.5
			tax_credits_zwg += emp_cimas_zwg * 0.5
			self.medical_aid_tax_credit = (emp_cimas_usd * 0.5) + (emp_cimas_zwg * 0.5)

			self.total_deduction_usd += emp_cimas_usd
			self.total_deduction_zwg += emp_cimas_zwg

		elif d.components.upper() == "NEC":
			self.nec_usd = basic_salary_usd * 0.015
			self.nec_zwg = basic_salary_zwg * 0.015

			d.amount_usd = self.nec_usd
			d.amount_zwg = self.nec_zwg

			self.total_deduction_usd += flt(self.nec_usd)
			self.total_deduction_zwg += flt(self.nec_zwg)

		elif d.components.upper() == "PAYEE":
			d.amount_usd = 0
			d.amount_zwg = 0

		elif d.components.upper() == "AIDS LEVY":
			d.amount_usd = 0
			d.amount_zwg = 0

		else:
			self.total_deduction_usd += flt(d.amount_usd)
			self.total_deduction_zwg += flt(d.amount_zwg)

		# Check if it is an allowable deduction (deductible for tax)
		if component_doc.is_tax_applicable:
			total_allowable_deductions_usd += flt(d.amount_usd)
			total_allowable_deductions_zwg += flt(d.amount_zwg)

		salary_structure.append(
			"deductions",
			{
				"components": d.components,
				"amount_zwg": d.amount_zwg,
				"amount_usd": d.amount_usd,
				"is_tax_applicable": bool(d.is_tax_applicable),
				"amount_currency": "ZWG" if d.amount_zwg else "USD",
			},
		)

	self.total_allowable_deductions_usd = total_allowable_deductions_usd
	print(f"total_allowable_deductions_usd {total_allowable_deductions_usd}")
	self.total_allowable_deductions_zwg = total_allowable_deductions_zwg
	self.total_earnings_usd = total_amount_basic_and_bonus_and_allowances_usd
	self.total_earnings_zwg = total_amount_basic_and_bonus_and_allowances_zwg
	self.total_taxable_income_usd = self.total_earnings_usd - self.total_allowable_deductions_usd
	self.total_taxable_income_zwg = self.total_earnings_zwg - self.total_allowable_deductions_zwg
	payee_usd = max(
		payee_against_slab_usd(self.total_taxable_income_usd, getattr(self, "payroll_frequency", "Monthly"))
		- tax_credits_usd,
		0,
	)
	payee_zwg = max(
		payee_against_slab_zwg(self.total_taxable_income_zwg, getattr(self, "payroll_frequency", "Monthly"))
		- tax_credits_zwg,
		0,
	)

	# Calculate AIDS Levy (3% of net PAYE)
	aids_levy_usd = payee_usd * 0.03
	aids_levy_zwg = payee_zwg * 0.03

	# Calculate SDL (5% of Gross)
	sdl_usd = self.total_earnings_usd * 0.05
	sdl_zwg = self.total_earnings_zwg * 0.05

	frappe.msgprint(
		f"<b>Payroll Calc (Split):</b><br>USD Taxable: {self.total_taxable_income_usd}<br>ZWG Taxable: {self.total_taxable_income_zwg}<br>Payee USD: {payee_usd}<br>Payee ZWG: {payee_zwg}<br>SDL USD: {sdl_usd}"
	)

	# Update summary fields on employee record
	self.payee_usd = payee_usd
	self.payee_zwg = payee_zwg
	self.aids_levy_usd = aids_levy_usd
	self.aids_levy_zwg = aids_levy_zwg
	self.payee = payee_usd + payee_zwg
	self.aids_levy = aids_levy_usd + aids_levy_zwg
	self.total_tax_credits_usd = tax_credits_usd
	self.total_tax_credits_zwg = tax_credits_zwg
	self.total_tax_credits = tax_credits_usd + tax_credits_zwg

	# Update child table rows for PAYEE, AIDS LEVY, and SDL
	for d in self.employee_deductions:
		if d.components.upper() == "PAYEE":
			d.amount_usd = payee_usd
			d.amount_zwg = payee_zwg
		elif d.components.upper() == "AIDS LEVY":
			d.amount_usd = aids_levy_usd
			d.amount_zwg = aids_levy_zwg
		elif d.components.upper() == "SDL":
			d.amount_usd = sdl_usd
			d.amount_zwg = sdl_zwg

	self.total_deduction_usd += payee_usd + aids_levy_usd
	self.total_deduction_zwg += payee_zwg + aids_levy_zwg
	self.total_net_income_usd = self.total_earnings_usd - self.total_deduction_usd
	self.total_net_income_zwg = self.total_earnings_zwg - self.total_deduction_zwg
	# Net Pay = Total Earnings - Total Deductions (unified field)
	self.net_income = self.total_net_income_usd + self.total_net_income_zwg
	self.total_income = self.total_earnings_usd + self.total_earnings_zwg
	self.total_deductions = self.total_deduction_usd + self.total_deduction_zwg

	# Save it_
	salary_structure.save()
	print(f"havano_salary_structure saved: {salary_structure.name}")
	# Link back to employee
	self.salary_structure = salary_structure.name


# ------------------------------------------------------------------splt currecy--------------------------------------------------------------------------------------


# ------------------------------------------------------------------splt currecy--------------------------------------------------------------------------------------


def payee_against_slab_usd(amount, mode="Monthly"):
	payee = 0.0
	try:
		# Try name variants: 'USD-Monthly' then 'USD'
		slab_name = f"USD-{mode}"
		if not frappe.db.exists("Havano Tax Slab", slab_name):
			slab_name = "USD"
			
		slab_doc = frappe.get_doc("Havano Tax Slab", slab_name)
		for slab in slab_doc.tax_brackets:
			if flt(slab.lower_limit) <= flt(amount) <= flt(slab.upper_limit):
				payee = (flt(amount) * (flt(slab.percent) / 100)) - flt(slab.fixed_amount)
				break
	except Exception as e:
		frappe.log_error(f"PAYE Slab Error [USD]: {e}", "PAYE Calculation")
	return max(flt(payee), 0.0)


def payee_against_slab_zwg(amount, mode="Monthly"):
	payee = 0.0
	try:
		# Try name variants: 'ZWG-Monthly' then 'ZWG' then 'ZWL'
		slab_name = f"ZWG-{mode}"
		if not frappe.db.exists("Havano Tax Slab", slab_name):
			slab_name = "ZWG"
		if not frappe.db.exists("Havano Tax Slab", slab_name):
			slab_name = "ZWL"
			
		slab_doc = frappe.get_doc("Havano Tax Slab", slab_name)
		for slab in slab_doc.tax_brackets:
			if flt(slab.lower_limit) <= flt(amount) <= flt(slab.upper_limit):
				payee = (flt(amount) * (flt(slab.percent) / 100)) - flt(slab.fixed_amount)
				break
	except Exception as e:
		frappe.log_error(f"PAYE Slab Error [ZWG]: {e}", "PAYE Calculation")
	return max(flt(payee), 0.0)
