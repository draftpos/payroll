import frappe

def main():
    frappe.init(site='v15.local')
    frappe.connect()

    pf = frappe.get_doc('Print Format', 'Havano Employee Payslip')
    html = pf.html
    
    # We replace the whole "else" block inside the Deductions Column logic
    old_block = '''                    {% else %}
                        <td>{{ "%.2f"|format(ded.amount_usd or 0) }}</td>
                        <td>{{ "%.2f"|format(ded.amount_zwg or 0) }}</td>
                        {% set totals.ded_usd = (totals.ded_usd + (ded.amount_usd or 0)) | round(2, 'common') %}
                        {% set totals.ded_zwg = (totals.ded_zwg + (ded.amount_zwg or 0)) | round(2, 'common') %}
                    {% endif %}'''
                    
    new_block = '''                    {% else %}
                        <td>{{ "%.2f"|format(ded.amount_usd or 0) }}</td>
                        <td>{{ "%.2f"|format(ded.amount_zwg or 0) }}</td>
                        
                        {% if ded.components in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE"] and doc.cimas_employee_ == 0 %}
                            {# Do not add to totals because employer pays 100% #}
                        {% else %}
                            {% set totals.ded_usd = (totals.ded_usd + (ded.amount_usd or 0)) | round(2, 'common') %}
                            {% set totals.ded_zwg = (totals.ded_zwg + (ded.amount_zwg or 0)) | round(2, 'common') %}
                        {% endif %}
                    {% endif %}'''
                    
    if old_block in html:
        pf.html = html.replace(old_block, new_block)
        pf.save()
        frappe.db.commit()
        print("Patched Havano Employee Payslip successfully!")
    else:
        print("Could not find block in Havano Employee Payslip.")

