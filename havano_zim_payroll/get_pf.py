import frappe
import re

def main():
    pfs = frappe.get_all('Print Format', filters={'doc_type': 'havano_employee'}, fields=['name', 'html'])
    for pf in pfs:
        html = pf.html
        if not html: continue
        
        changed = False
        
        # Patch USD sum using regex to handle whitespace/\r differences
        pattern_usd = r'<td>\{\{\s*"%\.2f"\|format\(ded\.amount_usd or 0\)\s*\}\}</td>\s*\{%\s*set totals\.ded_usd = totals\.ded_usd \+ \(ded\.amount_usd or 0\)\s*%\}'
        
        new_usd = '''<td>{{ "%.2f"|format(ded.amount_usd or 0) }}</td>
          {% if ded.components in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE"] and doc.cimas_employee_ == 0 %}
             {# Do not add to total because employer pays 100% #}
          {% else %}
             {% set totals.ded_usd = totals.ded_usd + (ded.amount_usd or 0) %}
          {% endif %}'''
          
        if re.search(pattern_usd, html):
            html = re.sub(pattern_usd, new_usd, html)
            changed = True
            
        # Patch ZWG sum
        pattern_zwg = r'<td>\{\{\s*"%\.2f"\|format\(ded\.amount_zwg or 0\)\s*\}\}</td>\s*\{%\s*set totals\.ded_zwg = totals\.ded_zwg \+ \(ded\.amount_zwg or 0\)\s*%\}'
        
        new_zwg = '''<td>{{ "%.2f"|format(ded.amount_zwg or 0) }}</td>
          {% if ded.components in ["CIMAS", "MEDICAL AID", "MEDICAL AID EXPENSE"] and doc.cimas_employee_ == 0 %}
             {# Do not add to total because employer pays 100% #}
          {% else %}
             {% set totals.ded_zwg = totals.ded_zwg + (ded.amount_zwg or 0) %}
          {% endif %}'''
          
        if re.search(pattern_zwg, html):
            html = re.sub(pattern_zwg, new_zwg, html)
            changed = True
            
        if changed:
            doc = frappe.get_doc('Print Format', pf.name)
            doc.html = html
            doc.save()
            frappe.db.commit()
            print(f"Patched {pf.name} successfully!")

