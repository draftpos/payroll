import pandas as pd
import json
import os

excel_files = [
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/JANUARY 2026  END OF MONTH STOCK SUMMARY.xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/FEBRUARY 2026 END OF MONTH STOCK SUMMARY.xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/MARCH 2026 END OF MONTH STOCK SUMMARY.xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/END OF MONTH APRIL 2026.xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/MAY 2026 END OF MONTH STOCK SUMMARY.xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/END_OF_MONTH_JUNE_2026(1).xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/JULY 2026 END OF MONTH STOCK SUMMARY.xlsx",
    "Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/tmp_excel/END_OF_AUGUST__2026(1).xlsx"
]

item_keywords = {
    "YEAST": "YEAST (kgs)",
    "LACTIC": "LACTIC ACID (kgs)",
    "SORGHUM": "SORGHUM MALT (kgs )",
    "SUGAR": "SUGAR (kgs)",
    "MAIZE": "MAIZE MEAL (kgs )",
    "COAL": "COAL",
    "DIESEL": "DIESEL",
    "FIREWOOD": "FIREWOOD",
    "BULK BEER": "BULK BEER",
    "2L PACKAGED": "2L PUNGWE",
    "LOOSE BOTTLES": "LOOSE BOTTLES",
    "CLOSURES": "CLOSURES (unit )",
    "SLEEVES": "SHAKE-SHAKE SLEEVES",
    "CRATES IN CIRCULATION": "CRATES IN CIRCULATION",
    "BOTTLES IN CIRCULATION": "BOTTLES IN CIRCULATION",
    "ONLINE DESCALENT": "ONLINE DESCALENT",
    "SHAKE-SHAKE CLOSURES": "SHAKE-SHAKE CLOSURES",
    "TANK CLEANER": "TANK CLEANER (LTRS )"
}

with open('Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/erpnext_items.json', 'r') as f:
    erp_data = json.load(f)
valid_items = {i['name'] for i in erp_data['items']}

def find_item_code(text):
    text = str(text).upper().strip()
    for v in valid_items:
        if v.upper() == text:
            return v
    for k, v in item_keywords.items():
        if k in text:
            return v
    return None

unmapped = set()

for file_path in excel_files:
    try:
        df = pd.read_excel(file_path, header=None)
        for index, row in df.iterrows():
            for i, cell in enumerate(row):
                val_str = str(cell).strip()
                if not val_str or val_str.lower() in ('nan', 'none', 'item', 'total', 'quantity', 'cost per unit', 'inventory', 'january 2026 end of month stock summary', 'pungwe breweries and marketing'):
                    continue
                # If there's a number in the adjacent cells, it might be an item
                has_number = False
                for j in range(i+1, len(row)):
                    v = row[j]
                    if pd.notna(v):
                        try:
                            if isinstance(v, str):
                                v = v.replace(',', '').replace(' ', '')
                            float(v)
                            has_number = True
                            break
                        except ValueError:
                            pass
                
                if has_number:
                    code = find_item_code(cell)
                    if not code:
                        unmapped.add(val_str)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

print("Potentially unmapped items in Excel files:")
for u in unmapped:
    print(f"- {u}")
