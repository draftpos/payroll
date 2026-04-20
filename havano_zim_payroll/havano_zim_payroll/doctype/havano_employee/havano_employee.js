// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("havano_employee", {
	refresh(frm) {
		update_net_income(frm);
		update_tax_credits(frm);
	},
	total_income(frm) {
		update_net_income(frm);
	},
	total_deductions(frm) {
		update_net_income(frm);
	},
	salary_currency(frm) {
		update_tax_credits(frm);
	},
	cimas_employee_(frm) {
		update_tax_credits(frm);
	},
	is_blind(frm) {
		update_tax_credits(frm);
	},
	is_disabled(frm) {
		update_tax_credits(frm);
	},
	is_elderly(frm) {
		update_tax_credits(frm);
	}
});

frappe.ui.form.on("havano_payroll_earnings", {
	amount_usd(frm, cdt, cdn) {
		update_tax_credits_if_needed(frm, cdt, cdn);
	},
	amount_zwg(frm, cdt, cdn) {
		update_tax_credits_if_needed(frm, cdt, cdn);
	},
	components(frm, cdt, cdn) {
		update_tax_credits_if_needed(frm, cdt, cdn);
	},
	employee_deductions_remove(frm) {
		update_tax_credits(frm);
	}
});

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
