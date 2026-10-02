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

months_map = {
    "JANUARY": "2026-01-31",
    "FEBRUARY": "2026-02-28",
    "MARCH": "2026-03-31",
    "APRIL": "2026-04-30",
    "MAY": "2026-05-31",
    "JUNE": "2026-06-30",
    "JULY": "2026-07-31",
    "AUGUST": "2026-08-31"
}

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
    "SHAKE-SHAKE CLOSURES": "SHAKE-SHAKE CLOSURES", "TANK CLEANER": "TANK CLEANER (LTRS )", "FLOOR CLEANER": "FLOOR CLEANER (kgs)", "CHEMELL 160": "CHEMELL 160 (ltrs)", "BACTERGENT": "BACTERGENT (kgs)", "BIOCHEMELL": "BIOCHEMELL(ltrs)", "SAFIER SET": "SAFIER SET (kgs)", "DAMAGED BOTTLES": "DAMAGED BOTTLES", "DAMAGED CRATES": "DAMAGED CRATES",
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

adjustments = []

for file_path in excel_files:
    filename = os.path.basename(file_path).upper()
    posting_date = None
    for m, date_str in months_map.items():
        if m in filename:
            posting_date = date_str
            break
            
    if not posting_date:
        continue
        
    df = pd.read_excel(file_path, header=None)
    items_map = {}
    
    for index, row in df.iterrows():
        for i, cell in enumerate(row):
            item_code = find_item_code(cell)
            if item_code:
                numbers = []
                for j in range(i+1, len(row)):
                    val = row[j]
                    if pd.notna(val):
                        try:
                            if isinstance(val, str):
                                val = val.replace(',', '').replace(' ', '')
                            numbers.append(float(val))
                        except ValueError:
                            continue
                
                if numbers:
                    qty = numbers[0]
                    # if there's a second number, assume it's cost per unit, else fallback to 1
                    rate = numbers[1] if len(numbers) > 1 else 1.0
                    if rate == 0:
                        rate = 1.0 # avoid 0 rate which can sometimes be invalid if stock goes up
                    
                    if item_code in items_map:
                        items_map[item_code]["qty"] = qty
                        # keep latest rate or max rate
                        if rate > items_map[item_code]["valuation_rate"]:
                            items_map[item_code]["valuation_rate"] = rate
                    else:
                        items_map[item_code] = {"qty": qty, "valuation_rate": rate}
                break
                
    if items_map:
        items_list = [{"item_code": k, "qty": v["qty"], "warehouse": "Stores - PB", "valuation_rate": v["valuation_rate"]} for k, v in items_map.items()]
        adjustments.append({
            "posting_date": posting_date,
            "items": items_list
        })

adjustments.sort(key=lambda x: x["posting_date"])

with open('Z:/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/adjustments_payload.json', 'w') as f:
    json.dump(adjustments, f, indent=2)

print(f"Generated payload with {len(adjustments)} months of adjustments.")
