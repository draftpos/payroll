import frappe

def validate_currency_conversions(doc, method):
    # Determine if dual currency feature is enabled
    enabled = frappe.db.get_single_value("Havano Payroll Settings", "dual_currency_with_conversions")
    if not enabled:
        return

    # Ensure we have an employee reference
    employee_id = doc.get("employee")
    if not employee_id:
        return

    employee = frappe.get_doc("Havano Employee", employee_id)
    category = employee.get("employee_category")

    if not category:
        return

    exchange_rate = frappe.db.get_value("Currency Exchange", 
        {"from_currency": "USD", "to_currency": "ZiG"}, "exchange_rate", order_by="date desc")
    
    if not exchange_rate:
        # Fallback to ZWL if ZiG not found
        exchange_rate = frappe.db.get_value("Currency Exchange", 
            {"from_currency": "USD", "to_currency": "ZWL"}, "exchange_rate", order_by="date desc") or 1.0

    if category == "Zig only":
        doc.salary_currency = "ZiG"
        
        # Convert amounts
        fields_to_convert = ["net_income", "basic_salary", "total_earnings", "total_deductions", "total_taxable_income", "payee", "aids_levy"]
        for field in fields_to_convert:
            if hasattr(doc, field) and getattr(doc, field):
                setattr(doc, field, getattr(doc, field) * exchange_rate)

        # Convert child tables (Earnings & Deductions)
        if hasattr(doc, "employee_earnings"):
            for row in doc.employee_earnings:
                row.amount = (row.amount or 0) * exchange_rate
                
        if hasattr(doc, "employee_deductions"):
            for row in doc.employee_deductions:
                row.amount = (row.amount or 0) * exchange_rate

    elif category == "Both (Zig and USD)":
        usd_pct = (employee.get("usd_percentage") or 0) / 100.0
        zig_pct = (employee.get("zig_percentage") or 0) / 100.0

        fields_to_split = ["net_income", "total_earnings", "total_deductions", "total_taxable_income", "payee", "aids_levy"]
        
        for field in fields_to_split:
            base_val = getattr(doc, field) or 0
            # Set USD split
            if hasattr(doc, f"{field}_usd"):
                setattr(doc, f"{field}_usd", base_val * usd_pct)
            # Set ZiG split
            if hasattr(doc, f"{field}_zwg"):
                setattr(doc, f"{field}_zwg", base_val * zig_pct * exchange_rate)
            elif hasattr(doc, f"{field}_zig"):
                setattr(doc, f"{field}_zig", base_val * zig_pct * exchange_rate)
