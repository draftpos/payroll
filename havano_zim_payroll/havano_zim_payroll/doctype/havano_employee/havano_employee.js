// Copyright (c) 2025, Havano and contributors
// For license information, please see license.txt

// Components that are controlled by "Always Calculate" checkbox on havano_salary_component
const ALWAYS_CALC_COMPONENTS = ["NSSA", "PAYEE", "AIDS LEVY"];

function apply_overtime_visibility(frm) {
	let is_both = frm.doc.overtime === 'Time & Half and Double Time';
	['hours', 'overtime_amount'].forEach(f => {
		frm.toggle_display(f, !is_both);
	});
	['hours_half', 'hours_double', 'half_amount', 'double_amount'].forEach(f => {
		frm.toggle_display(f, is_both);
	});
}

frappe.ui.form.on("havano_employee", {
	refresh(frm) {
		sync_always_calculate_deductions(frm);
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
	employee_deductions_remove(frm) {
		calculate_totals_server(frm);
	}
});

function calculate_totals_server(frm) {
        if (frm.doc.company) {
                // Sync fields from locals into frm.doc before sending to server
                // (Child table edits live in locals[] not frm.doc until grid blur)
                ["employee_earnings", "employee_deductions"].forEach(function(table) {
                        (frm.doc[table] || []).forEach(function(row) {
                                if (locals[row.doctype] && locals[row.doctype][row.name]) {
                                        let l = locals[row.doctype][row.name];
                                        row.is_tax_applicable = l.is_tax_applicable;
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
                                        // Sync scalar fields
                                        const scalar_fields = [
                                                "payee", "aids_levy", "sdl", "net_income",
                                                "total_income", "total_deductions", "total_tax_credits",
                                                "total_income_usd", "total_income_zwg",
                                                "total_deduction_usd", "total_deduction_zwg",
                                                "total_net_income_usd", "total_net_income_zwg",
                                                "blind", "disabled", "elderly", "medical_aid_tax_credit",
                                                "cimas_employee", "cimas_employer", "funeral_employee", "funeral_employer",
                                                "ensuarable_earnings", "allowable_deductions", "basic_salary_calculated",
                                                "overtime_amount", "hourly_rate", "cash_in_lieu_amount", "half_amount", "double_amount", "hours_half", "hours_double",
                                                "total_taxable_income", "total_taxable_income_usd", "total_taxable_income_zwg",
                                                "total_ensuarable_earnings_usd", "total_ensuarable_earnings_zwg"
                                        ];
                                        scalar_fields.forEach(function(f) {
                                                if (r.message[f] !== undefined) {
                                                        frm.doc[f] = r.message[f];
                                                }
                                        });
                                        // Reload child tables from server response
                                        ["employee_earnings", "employee_deductions"].forEach(function(table) {
                                                if (r.message[table]) {
                                                        let server_rows = r.message[table];
                                                        
                                                        // Fallback mapping for temporary rows: if server wiped the "new-..." name,
                                                        // map it back using the component name or row idx so we don't unnecessarily delete and recreate the row.
                                                        server_rows.forEach(s_row => {
                                                                if (!s_row.name || s_row.name.startsWith('new-')) {
                                                                                let match = frm.doc[table].find(c_row => 
                                                                                        c_row.name && c_row.name.startsWith('new-') && 
                                                                                        ((c_row.components && c_row.components === s_row.components) || (!c_row.components && !s_row.components && c_row.idx === s_row.idx))
                                                                                );
                                                                        if (match) {
                                                                                s_row.name = match.name;
                                                                        }
                                                                }
                                                        });

                                                        let server_names = server_rows.map(row => row.name).filter(Boolean);
                                                        
                                                        // Remove rows not present in server response
                                                        let i = frm.doc[table].length;
                                                        while (i--) {
                                                                if (frm.doc[table][i].name && !server_names.includes(frm.doc[table][i].name)) {
                                                                        frappe.model.clear_doc(frm.doc[table][i].doctype, frm.doc[table][i].name);
                                                                        frm.doc[table].splice(i, 1);
                                                                }
                                                        }
                                                        
                                                        // Add or update rows, preserving the user's is_tax_applicable
                                                        // IMPORTANT: preserve user-set is_tax_applicable — never let server overwrite it
                                                        server_rows.forEach(row_data => {
                                                                let existing = row_data.name ? frm.doc[table].find(r => r.name === row_data.name) : null;
                                                                if (existing) {
                                                                        // Grab value from locals (what user actually has ticked)
                                                                        let live_tax = (locals[existing.doctype] && locals[existing.doctype][existing.name])
                                                                                ? locals[existing.doctype][existing.name].is_tax_applicable
                                                                                : existing.is_tax_applicable;
                                                                        live_tax = live_tax ? 1 : 0;
                                                                        Object.assign(existing, row_data);
                                                                        existing.is_tax_applicable = live_tax;
                                                                        if (locals[existing.doctype] && locals[existing.doctype][existing.name]) {
                                                                                locals[existing.doctype][existing.name].is_tax_applicable = live_tax;
                                                                        }
                                                                } else {
                                                                        let new_row = frappe.model.add_child(frm.doc, table);
                                                                        Object.assign(new_row, row_data);
                                                                        if (new_row.is_tax_applicable !== undefined) {
                                                                                new_row.is_tax_applicable = new_row.is_tax_applicable ? 1 : 0;
                                                                        }
                                                                }
                                                        });
                                                        
                                                        frm.refresh_field(table);
                                                }
                                        });
                                        frm.refresh_fields();
                                        // Re-apply overtime visibility after field refresh
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
