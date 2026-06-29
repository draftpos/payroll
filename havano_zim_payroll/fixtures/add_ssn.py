import json

with open(custom_field.json, r) as f:
    data = json.load(f)

# Add for havano_employee
data.append({
    doctype: Custom
