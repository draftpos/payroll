// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

// Components that are controlled by "Always Calculate" checkbox on havano_salary_component
const ALWAYS_CALC_COMPONENTS = ["NSSA", "PAYEE", "AIDS LEVY"];

frappe.ui.form.on("havano_employee", {
	refresh(frm) {
		update_net_income(frm);
		update_tax_credits(frm);
		sync_always_calculate_deductions(frm);
	},
	total_income(frm) {
		update_net_income(frm);
	},
	total_deductions(frm) {
		update_net_income(frm);
	},
	payroll_frequency(frm) {
		calculate_totals_server(frm);
	},
	cimas_employee_(frm) {
		calculate_totals_server(frm);
	},
	is_blind(frm) {
		calculate_totals_server(frm);
	},
	is_disabled(frm) {
		calculate_totals_server(frm);
	},
	is_elderly(frm) {
		calculate_totals_server(frm);
	},
	native_employee_id(frm) {
		calculate_totals_server(frm);
	}
});

frappe.ui.form.on("havano_payroll_earnings", {
	amount_usd(frm, cdt, cdn) {
		calculate_totals_server(frm);
	},
	amount_zwg(frm, cdt, cdn) {
		calculate_totals_server(frm);
	},
	components(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.components) {
			frappe.db.get_value('havano_salary_component', row.components, 'is_tax_applicable')
				.then(r => {
					if (r && r.message) {
						frappe.model.set_value(cdt, cdn, 'is_tax_applicable', r.message.is_tax_applicable);
					}
					calculate_totals_server(frm);
				});
		} else {
			calculate_totals_server(frm);
		}
	},
	is_tax_applicable(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.components) {
			frappe.db.set_value('havano_salary_component', row.components, 'is_tax_applicable', row.is_tax_applicable);
		}
		calculate_totals_server(frm);
	},
	employee_earnings_remove(frm) {
		calculate_totals_server(frm);
	}
});

frappe.ui.form.on("havano_payroll_deductions", {
	amount_usd(frm, cdt, cdn) {
		calculate_totals_server(frm);
	},
	amount_zwg(frm, cdt, cdn) {
		calculate_totals_server(frm);
	},
	components(frm, cdt, cdn) {
		calculate_totals_server(frm);
	},
	employee_deductions_remove(frm) {
		calculate_totals_server(frm);
	}
});

function calculate_totals_server(frm) {
	if (frm.doc.company) {
		frappe.call({
			doc: frm.doc,
			method: "calculate_totals",
			callback: function(r) {
				if (r.message) {
					// Update the form fields with calculated values
					frm.refresh_fields([
						"payee", "aids_levy", "sdl", "net_income", 
						"total_income", "total_deductions", "total_tax_credits",
						"total_income_usd", "total_income_zwg",
						"total_deduction_usd", "total_deduction_zwg",
						"total_net_income_usd", "total_net_income_zwg",
						"employee_earnings", "employee_deductions",
						"blind", "disabled", "elderly", "medical_aid_tax_credit",
						"ensuarable_earnings", "allowable_deductions", "basic_salary_calculated",
						"total_taxable_income", "total_taxable_income_usd", "total_taxable_income_zwg",
						"total_ensuarable_earnings_usd", "total_ensuarable_earnings_zwg"
					]);
				}
			}
		});
	}
}

function update_tax_credits_if_needed(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.parentfield === "employee_deductions") {
		const comp = (row.components || "").toUpperCase();
		if (comp === "CIMAS" || comp === "MEDICAL AID") {
			update_tax_credits(frm);
		}
	}
}

function update_net_income(frm) {
	const total_earnings = flt(frm.doc.total_income);
	const total_deductions = flt(frm.doc.total_deductions);
	frm.set_value("net_income", total_earnings - total_deductions);
}

function update_tax_credits(frm) {
	// First, calculate Medical Aid Tax Credit
	let medical_aid_credit = 0;
	let cimas_row = (frm.doc.employee_deductions || []).find(d => 
		["CIMAS", "MEDICAL AID"].includes((d.components || "").toUpperCase())
	);
	if (cimas_row) {
		let total_cimas = flt(cimas_row.amount_usd) + flt(cimas_row.amount_zwg);
		let employee_contribution = total_cimas * flt(frm.doc.cimas_employee_) / 100;
		medical_aid_credit = employee_contribution * 0.5;
	}
	frm.set_value("medical_aid_tax_credit", medical_aid_credit);

	// Then, handle Blind, Disabled, Elderly credits
	// Use frappe.call to get exchange rate for ZWG or ZWL
	let target_currency = "ZWG"; 
	
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Currency Exchange",
			filters: { from_currency: "USD", to_currency: ["in", ["ZWG", "ZWL"]] },
			fieldname: "exchange_rate"
		},
		callback: function(r) {
			let rate = flt(r.message ? r.message.exchange_rate : 1);
			let is_usd = (frm.doc.salary_currency === "USD");
			
			let blind_val = frm.doc.is_blind ? (is_usd ? 75 : 75 * rate) : 0;
			let disabled_val = frm.doc.is_disabled ? (is_usd ? 75 : 75 * rate) : 0;
			let elderly_val = frm.doc.is_elderly ? (is_usd ? 75 : 75 * rate) : 0;

			frm.set_value("blind", blind_val);
			frm.set_value("disabled", disabled_val);
			frm.set_value("elderly", elderly_val);

			let total = medical_aid_credit + blind_val + disabled_val + elderly_val;
			frm.set_value("total_tax_credits", total);
			
			// If in split currency mode, we might want to set total_tax_credits_usd/zwg too
			if (frm.doc.payslip_type === "Split Currency") {
				// Simplified: Assigning full credits to USD for display if available, 
				// or ZWG if that's the main currency.
				// The backend handles the exact split.
				frm.set_value("total_tax_credits_usd", is_usd ? total : total / rate);
				frm.set_value("total_tax_credits_zwg", is_usd ? total * rate : total);
			}
		}
	});
}

/**
 * Sync the employee_deductions table based on always_calculate flag.
 * - Adds NSSA, PAYEE, AIDS LEVY rows when always_calculate = 1.
 * - Removes those rows when always_calculate = 0.
 * Uses case-insensitive matching so "Aids Levy", "AIDS LEVY" etc. all work.
 */
function sync_always_calculate_deductions(frm) {
	// Fetch ALL deduction-type components (no name filter — avoids case mismatch)
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "havano_salary_component",
			filters: [
				["type", "=", "Deduction"]
			],
			fields: ["salary_component", "always_calculate"],
			limit_page_length: 50
		},
		callback: function(r) {
			if (!r.message) return;

			// Only keep components whose name matches ALWAYS_CALC_COMPONENTS (case-insensitive)
			let controlled = r.message.filter(c =>
				ALWAYS_CALC_COMPONENTS.includes((c.salary_component || "").toUpperCase())
			);

			if (!controlled.length) return;

			let changed = false;

			// Map: exact DB name → always_calculate value
			let should_add = new Set(
				controlled.filter(c => c.always_calculate == 1).map(c => c.salary_component)
			);

			let deductions = frm.doc.employee_deductions || [];
			let existing_upper = new Set(deductions.map(d => (d.components || "").toUpperCase()));

			// Add rows that are missing (case-insensitive check for existing)
			should_add.forEach(comp_name => {
				if (!existing_upper.has(comp_name.toUpperCase())) {
					frm.add_child("employee_deductions", { components: comp_name });
					changed = true;
				}
			});

			if (changed) {
				frm.refresh_field("employee_deductions");
			}
		}
	});
}
