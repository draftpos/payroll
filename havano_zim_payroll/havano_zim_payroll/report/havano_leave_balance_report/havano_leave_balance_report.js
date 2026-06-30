frappe.query_reports["Havano Leave Balance Report"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "havano_employee",
			"width": "80"
		},
		{
			"fieldname": "as_on_month",
			"label": __("As On Month"),
			"fieldtype": "Select",
			"options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
			"width": "80"
		},
		{
			"fieldname": "as_on_year",
			"label": __("As On Year"),
			"fieldtype": "Select",
			"options": "\n2025\n2026\n2027\n2028\n2029\n2030",
			"width": "80"
		}
	]
};
