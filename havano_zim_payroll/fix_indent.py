import sys

def fix_indentation(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    # We need to indent lines that are inside the try block for Havano Payroll Journal
    # The try block starts at line 658, and the except is at 773.
    # Lines 669 to 771 (0-indexed 668 to 770) need 4 spaces added if they don't have it yet.
    # Let's dynamically find the blocks.
    
    in_pj_try = False
    in_ecj_try = False
    
    for i in range(len(lines)):
        # Detect start of pj block
        if "if create_journal_entry:" in lines[i]:
            pass
            
        if "pj.company = comp" in lines[i]:
            in_pj_try = True
            continue
        if "except Exception as e:" in lines[i] and in_pj_try:
            in_pj_try = False
            continue
            
        if in_pj_try:
            if lines[i].strip() == "":
                continue
            # If it's only indented 16 spaces (instead of 20), indent it
            if lines[i].startswith("                ") and not lines[i].startswith("                    "):
                lines[i] = "    " + lines[i]
                
        if "ecj.company = comp" in lines[i]:
            in_ecj_try = True
            continue
        if "except Exception as e:" in lines[i] and in_ecj_try:
            in_ecj_try = False
            continue
            
        if in_ecj_try:
            if lines[i].strip() == "":
                continue
            if lines[i].startswith("                ") and not lines[i].startswith("                    "):
                lines[i] = "    " + lines[i]

    with open(filepath, 'w') as f:
        f.writelines(lines)

fix_indentation('/home/ashley/frappe-bench-v15/apps/havano_zim_payroll/havano_zim_payroll/api.py')
print("Done")
