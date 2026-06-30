// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

// Components that are controlled by "Always Calculate" checkbox on havano_salary_component
const ALWAYS_CALC_COMPONENTS = ["NSSA", "PAYE", "AIDS LEVY"];

function apply_overtime_visibility(frm) {
	let overtime = frm.doc.overtime || '';
	let is_both = overtime.indexOf('and') !== -1;
	let is_single = overtime !== '' && !is_both;
	console.log("OVERTIME SCRIPT RUNNING: v5", "is_single:", is_single, "is_both:", is_both, "value:", overtime);

	let single_fields = ['hours', 'overtime_amount'];
	let both_fields = ['hours_half', 'hours_double', 'half_amount', 'double_amount'];

	single_fields.forEach(f => frm.set_df_property(f, 'hidden', is_single ? 0 : 1));
	both_fields.forEach(f => frm.set_df_property(f, 'hidden', is_both ? 0 : 1));
}


function check_fds_and_set_annual(frm) {
	if (!frm.doc.date_of_joining) return;
	frappe.db.get_single_value("Havano Payroll Settings", "allow_forecast_fds_method").then(allow_fds => {
		frappe.db.get_single_value("Havano Payroll Settings", "allow_averaging_fds_method").then(allow_avg => {
			if (allow_fds || allow_avg) {
				let doj_year = new Date(frm.doc.date_of_joining).getFullYear();
				let current_year = new Date().getFullYear();
				if (doj_year < current_year) {
					if (frm.doc.payroll_frequency !== "Annual") {
						frm.set_value("payroll_frequency", "Annual");
					}
				}
			}
		});
	});
}

frappe.ui.form.on("havano_employee", {
	refresh(frm) {
		sync_always_calculate_deductions(frm);
		check_fds_and_set_annual(frm);
		// Fetch Leave Balance from Havano Leave Balances
		if (frm.doc.name) {
			frappe.db.get_value('Havano Leave Balances',
				{'employee': frm.doc.name, 'havano_leave_type': 'Annual Leave'},
				'leave_balance', (r) => {
					if (r && r.leave_balance !== undefined) {
						frm.set_value('total_leave_allocated', r.leave_balance);
					}
				}
			);
		}
		apply_overtime_visibility(frm);
	},
	date_of_joining(frm) {
		check_fds_and_set_annual(frm);
	},
	total_leave_allocated(frm) {
		// When user enters a value, create/update Havano Leave Balances
		if (!frm.doc.total_leave_allocated || !frm.doc.name) return;
		frappe.db.get_value('Havano Leave Balances',
			{'employee': frm.doc.name, 'havano_leave_type': 'Annual Leave'},
			'name', (r) => {
				if (r && r.name) {
					frappe.db.set_value('Havano Leave Balances', r.name, 'leave_balance', flt(frm.doc.total_leave_allocated));
				} else {
					frappe.call({
						method: 'frappe.client.insert',
						args: {
							doc: {
								doctype: 'Havano Leave Balances',
								employee: frm.doc.name,
								employee_name: frm.doc.employee_name,
								havano_leave_type: 'Annual Leave',
								leave_balance: flt(frm.doc.total_leave_allocated)
							}
						},
						callback: (res) => {
							if (!res.exc) frappe.show_alert({message: __('Leave Balance record created'), indicator: 'green'});
						}
					});
				}
			}
		);
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
	cimas_employer_(frm) {
		calculate_totals_server(frm);
	},
	cimas_amount(frm) {
		calculate_totals_server(frm);
	},
	funeral_policy_employee_(frm) {
		calculate_totals_server(frm);
	},
	funeral_policy_employer_(frm) {
		calculate_totals_server(frm);
	},
	funeral_amount(frm) {
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
	},
	national_id(frm) {
		let val = frm.doc.national_id;
		if (val) {
			// Remove spaces and hyphens, convert to uppercase
			val = val.replace(/[\s-]/g, '').toUpperCase();
			
			// Auto generate hyphen after first 2 numbers
			if (val.length > 2) {
				val = val.substring(0, 2) + '-' + val.substring(2);
			}
			
			if (val !== frm.doc.national_id) {
				frappe.model.set_value(frm.doctype, frm.docname, 'national_id', val);
			}

			// Validate: 2 numbers, hyphen, 6 numbers, 1 letter, 2 numbers
			let regex = /^\d{2}-\d{6}[A-Z]\d{2}$/;
			if (val.length >= 12 && !regex.test(val)) {
				frappe.msgprint({
					title: __('Invalid National ID'),
					indicator: 'orange',
					message: __('National ID must have 2 numbers, a hyphen, 6 numbers, a letter, and 2 numbers (e.g., 12-345678A12)')
				});
			}
		}
	},
	overtime(frm) {
		apply_overtime_visibility(frm);
		calculate_totals_server(frm);
	},
	hours(frm) {
		calculate_totals_server(frm);
	},
	hours_half(frm) {
		calculate_totals_server(frm);
	},
	hours_double(frm) {
		calculate_totals_server(frm);
	},
	validate(frm) {
		if (frm.doc.national_id) {
			let regex = /^\d{2}-\d{6}[A-Z]\d{2}$/;
			if (!regex.test(frm.doc.national_id)) {
				frappe.msgprint({
					title: __('Invalid National ID'),
					indicator: 'red',
					message: __('National ID must have 2 numbers, a hyphen, 6 numbers, a letter, and 2 numbers (e.g., 12-345678A12)')
				});
				frappe.validated = false;
			}
		}
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
					if (r && r.message && r.message.is_tax_applicable !== undefined && r.message.is_tax_applicable !== row.is_tax_applicable) {
						frappe.model.set_value(cdt, cdn, 'is_tax_applicable', r.message.is_tax_applicable)
							.then(() => calculate_totals_server(frm));
					} else {
						calculate_totals_server(frm);
					}
				});
		} else {
			calculate_totals_server(frm);
		}
	},
	is_tax_applicable(frm, cdt, cdn) {
		calculate_totals_server(frm);
	},
	employee_earnings_remove(frm) {
		calculate_totals_server(frm);
	},
	employee_deductions_remove(frm) {
		calculate_totals_server(frm);
	}
});



let calc_timeout = null;

function calculate_totals_server(frm) {
	if (calc_timeout) clearTimeout(calc_timeout);
	calc_timeout = setTimeout(() => {
		_calculate_totals_server_now(frm);
	}, 400);
}

function _calculate_totals_server_now(frm) {
	if (frm.doc.company) {
		// ── STEP 1: Snapshot state for ALL rows BEFORE server call ──
		let snapshot = {};
		["employee_earnings", "employee_deductions"].forEach(function(table) {
			(frm.doc[table] || []).forEach(function(row) {
				let l = (locals[row.doctype] && locals[row.doctype][row.name]) ? locals[row.doctype][row.name] : row;
				snapshot[row.name] = {
					is_tax_applicable: cint(l.is_tax_applicable),
					amount_usd: l.amount_usd,
					amount_zwg: l.amount_zwg,
					components: l.components
				};
			});
		});

		// ── STEP 2: Sync editable fields into frm.doc before sending ──
		["employee_earnings", "employee_deductions"].forEach(function(table) {
			(frm.doc[table] || []).forEach(function(row) {
				if (locals[row.doctype] && locals[row.doctype][row.name]) {
					let l = locals[row.doctype][row.name];
					row.is_tax_applicable = cint(l.is_tax_applicable);
					if (l.amount_usd !== undefined) row.amount_usd = l.amount_usd;
					if (l.amount_zwg !== undefined) row.amount_zwg = l.amount_zwg;
					if (l.components !== undefined) row.components = l.components;
				}
			});
		});

		frappe.call({
			doc: frm.doc,
			method: "calculate_totals",
			callback: function(r) {
				if (r.message) {
					// ── STEP 3: Sync scalar fields ──
					const scalar_fields = [
						"payee", "aids_levy", "sdl", "net_income",
						"total_income", "total_deductions", "total_tax_credits",
						"total_income_usd", "total_income_zwg",
						"total_deduction_usd", "total_deduction_zwg",
						"total_net_income_usd", "total_net_income_zwg",
						"blind", "disabled", "elderly", "medical_aid_tax_credit",
						"cimas_employee", "cimas_employer", "funeral_employee", "funeral_employer",
						"ensuarable_earnings", "allowable_deductions", "basic_salary_calculated",
						"overtime_amount", "hourly_rate", "cash_in_lieu_amount",
						"half_amount", "double_amount", "hours_half", "hours_double",
						"total_taxable_income", "total_taxable_income_usd", "total_taxable_income_zwg",
						"total_ensuarable_earnings_usd", "total_ensuarable_earnings_zwg"
					];
					scalar_fields.forEach(function(f) {
						if (r.message[f] !== undefined) {
							frm.doc[f] = r.message[f];
						}
					});

					// ── STEP 4: Sync child tables, avoiding race conditions ──
					["employee_earnings", "employee_deductions"].forEach(function(table) {
						if (r.message[table]) {
							let server_rows = r.message[table];
							let matched_local_names = [];

							server_rows.forEach(s_row => {
								let exactly_matches = frm.doc[table].find(c_row => c_row.name === s_row.name);
								if (!exactly_matches) {
									let match = frm.doc[table].find(c_row =>
										c_row.name && c_row.name.startsWith('new-') &&
										!matched_local_names.includes(c_row.name) &&
										((c_row.components && c_row.components === s_row.components) ||
										 (!c_row.components && !s_row.components && c_row.idx === s_row.idx))
									);
									if (match) {
										s_row.name = match.name;
										matched_local_names.push(match.name);
									} else {
										delete s_row.name;
									}
								} else {
									matched_local_names.push(exactly_matches.name);
								}
							});

							let server_names = server_rows.map(row => row.name).filter(Boolean);

							// Remove rows not present in server response
							let server_components = server_rows.map(r => (r.components || "").toUpperCase());
							let i = frm.doc[table].length;
							while (i--) {
								let cur = frm.doc[table][i];
								if (cur.name && !cur.name.startsWith('new-') && !server_names.includes(cur.name)) {
									let comp_upper = (cur.components || "").toUpperCase();
									if (!server_components.includes(comp_upper)) {
										frappe.model.clear_doc(cur.doctype, cur.name);
										frm.doc[table].splice(i, 1);
									}
								}
							}

							server_rows.forEach(row_data => {
								let existing = row_data.name
									? frm.doc[table].find(r => r.name === row_data.name)
									: null;

								if (existing) {
									let snap = snapshot[existing.name] || {};
									
									// Anti-Race Condition: If server just echoed what we sent, DO NOT overwrite it.
									// This allows the user's actively typing keystrokes (which changed the local value while in-flight) to survive.
									if (row_data.amount_usd === snap.amount_usd) delete row_data.amount_usd;
									if (row_data.amount_zwg === snap.amount_zwg) delete row_data.amount_zwg;
									if (row_data.components === snap.components) delete row_data.components;

									let preserved_tax = (snap.is_tax_applicable !== undefined)
										? snap.is_tax_applicable
										: cint(row_data.is_tax_applicable);

									Object.assign(existing, row_data);
									existing.is_tax_applicable = preserved_tax;

									if (locals[existing.doctype] && locals[existing.doctype][existing.name]) {
										locals[existing.doctype][existing.name].is_tax_applicable = preserved_tax;
									}
								} else {
									// It's not in local anymore. Did we send it?
									let was_sent = false;
									if (row_data.name && snapshot[row_data.name]) {
										was_sent = true;
									}
									
									if (!was_sent) {
										// Server generated a brand new row (e.g. NSSA, Overtime Double)
										let new_row = frappe.model.add_child(frm.doc, table);
										delete row_data.name;
										Object.assign(new_row, row_data);
										new_row.is_tax_applicable = cint(new_row.is_tax_applicable);
										
										// Add to snapshot for future calls
										snapshot[new_row.name] = {
											is_tax_applicable: new_row.is_tax_applicable,
											amount_usd: new_row.amount_usd,
											amount_zwg: new_row.amount_zwg,
											components: new_row.components
										};
									}
								}
							});

							frm.refresh_field(table);
						}
					});

					frm.refresh_fields();
					apply_overtime_visibility(frm);
				}
			}
		});
	}
}

function update_tax_credits_if_needed(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.parentfield === "employee_deductions") {
		const comp = (row.components || "").toUpperCase();
		const custom_medical_aid = (frm.doc.medical_aid_display_name || "Medical Aid").toUpperCase();
		
		if (comp === "CIMAS" || comp === "MEDICAL AID" || comp === "MEDICAL AID EXPENSE" || comp === custom_medical_aid) {
			update_tax_credits(frm);
		}
	}
}

function update_net_income(frm) {
	// Let the server handle this during calculate_totals
}

function update_tax_credits(frm) {
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
 * - Adds NSSA, PAYE, AIDS LEVY rows when always_calculate = 1.
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
