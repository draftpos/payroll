import frappe

def print_slabs():
    frappe.init(site="v15.local")
    frappe.connect()
    
    slabs = frappe.get_all("Havano Tax Slab")
    print(slabs)

if __name__ == "__main__":
    print_slabs()
