import frappe

def run():
    frappe.init(site="v15.local")
    frappe.connect()
    
    try:
        docs = frappe.get_all("havano_tax_credits", fields=["credit_name", "amount_usd", "amount_zwg"])
        for d in docs:
            print(d)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
