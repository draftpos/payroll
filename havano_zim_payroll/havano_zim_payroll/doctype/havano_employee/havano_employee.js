// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

frappe.ui.form.on("havano_employee", {
	refresh(frm) {
		update_net_income(frm);
		update_medical_aid_tax_credit(frm);
	},
	total_income(frm) {
		update_net_income(frm);
	},
	total_deductions(frm) {
		update_net_income(frm);
	},
	cimas_employee_(frm) {
		update_medical_aid_tax_credit(frm);
	}
});

frappe.ui.form.on("havano_payroll_earnings", {
	amount_usd(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.parentfield === "employee_deductions" && (row.components || "").toUpperCase() === "CIMAS") {
			update_medical_aid_tax_credit(frm);
		}
	},
	amount_zwg(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.parentfield === "employee_deductions" && (row.components || "").toUpperCase() === "CIMAS") {
			update_medical_aid_tax_credit(frm);
		}
	},
	components(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.parentfield === "employee_deductions" && (row.components || "").toUpperCase() === "CIMAS") {
			update_medical_aid_tax_credit(frm);
		}
	}
});

function update_net_income(frm) {
	const total_earnings = flt(frm.doc.total_income);
	const total_deductions = flt(frm.doc.total_deductions);
	frm.set_value("net_income", total_earnings - total_deductions);
}

function update_medical_aid_tax_credit(frm) {
	let cimas_row = (frm.doc.employee_deductions || []).find(d => (d.components || "").toUpperCase() === "CIMAS");
	if (cimas_row) {
		let total_cimas = flt(cimas_row.amount_usd) + flt(cimas_row.amount_zwg);
		let employee_contribution = total_cimas * flt(frm.doc.cimas_employee_) / 100;
		// Medical Aid Tax Credit is 50% of employee contribution
		frm.set_value("medical_aid_tax_credit", employee_contribution * 0.5);
	} else {
		frm.set_value("medical_aid_tax_credit", 0);
	}
}
