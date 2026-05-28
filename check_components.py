import frappe

def execute():
    frappe.init(site="v15.local")
    frappe.connect()
    
    docs = frappe.get_list("havano_salary_component", pluck="name")
    print(docs)
