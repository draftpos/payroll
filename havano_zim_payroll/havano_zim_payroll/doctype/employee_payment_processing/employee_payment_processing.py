# Copyright (c) 2025, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeePaymentProcessing(Document):
    
   def before_save(self):
      self.supplier=self.get_basic_salary_supplier()
   
      total_amount = 0
      for idx, row in enumerate(self.employee, start=1):
         amount_owing = row.amount_payable or 0
         amount_paid = row.amount_paying or 0

         if amount_paid > amount_owing:
            frappe.throw(
                  (f"Amount to be paid ({amount_paid}) cannot be greater than amount owing ({amount_owing}) for row {idx}")
            )

         total_amount += amount_paid      
      self.total_amount = total_amount
      a=create_payment_entry(
                  company=self.company,
                  payment_type="Pay",
                  party_type="Supplier",
                  party= self.supplier,
                  paid_from=self.account_from,
                  paid_from_currency=self.currency,
                  paid_amount=total_amount,            
                  received_amount=total_amount,     
                  mode_of_payment=self.mode_of_payment,
                  paid_to=self.account_to,
                  paid_to_currency=self.currency,


   
               )
      if a["status"] == 200:     # 200 is integer, not string
         for idx, row in enumerate(self.employee, start=1):

            amount_owing = row.amount_payable or 0
            amount_paid = row.amount_paying or 0

            # Fetch employee ledger
            ledger = frappe.db.get_value(
                  "Employee Ledger",
                  {"employee": row.employee},
                  ["name", "employee", "current_balance_owing"],
                  as_dict=True
            )

            if not ledger:
                  frappe.throw(f"No Employee Ledger found for employee {row.employee}")

            # Calculate new balance
            new_balance = ledger.current_balance_owing - amount_paid

            # Update ledger
            ledger_doc = frappe.get_doc("Employee Ledger", ledger.name)
            ledger_doc.current_balance_owing = new_balance
            ledger_doc.save(ignore_permissions=True)





   def get_basic_salary_supplier(self):
      # Step 1: Get the Havano Salary Component with component = "Basic Salary"
      salary_component = frappe.get_all(
         "havano_salary_component",
         filters={"salary_component": "Basic Salary"},
         fields=["name"],
         limit=1
      )

      if not salary_component:
         frappe.throw("No 'Basic Salary' component found.")

      # Step 2: Get the doc to access the child table 'accounts'
      doc = frappe.get_doc("havano_salary_component", salary_component[0].name)

      # Step 3: Grab the supplier from the child table
      supplier = None
      for row in doc.accounts:
         if row.supplier:
               supplier = row.supplier
               break

      if not supplier:
         frappe.throw("No supplier ID found in the 'Accounts' child table for Basic Salary.")

      return supplier

@frappe.whitelist()
def create_payment_entry(
    *,
    company,
    payment_type,
    party_type,
    party,
    paid_from,
    paid_from_currency,
    paid_to,
    paid_to_currency,
    paid_amount,
    received_amount,
    mode_of_payment=None,
    posting_date=None,
):
    """
    Creates and submits a Payment Entry in ERPNext with named parameters only.
    Supports multi-currency payments with explicit exchange rates.
    """
    try:
        from frappe.utils import nowdate

        posting_date = posting_date or nowdate()

        payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "company": company,
            "payment_type": payment_type,
            "party_type": party_type,
            "party": party,
            "paid_from": paid_from,
            "paid_from_account_currency": paid_from_currency,
            "paid_to": paid_to,
            "paid_to_account_currency": paid_to_currency,
            "paid_amount": paid_amount,
            "received_amount": received_amount,
            "mode_of_payment": mode_of_payment,
            "posting_date": posting_date
        })
        payment_entry.flags.ignore_permissions = True
        payment_entry.insert()
        payment_entry.submit()  # <-- Submit the document
        frappe.db.commit()

        return {
            "status": 200,
            "message": "Payment Entry created and submitted successfully",
            "data": payment_entry.name
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Payment Entry Creation Error")
        return {
            "status": 400,
            "message": str(e),
            "data": None
        }
@frappe.whitelist()
def get_employees_with_ledger(company=None, branch=None, department=None):
    """
    Returns a list of employees that have corresponding Employee Ledger entries.
    """

    filters = {}
    # if company:
    #     filters["company"] = company
    # if branch:
    #     filters["branch"] = branch
    # if department:
    #     filters["department"] = department

    # Step 1: Get all employees based on filters
    employees = frappe.get_all(
        "havano_employee",
        filters=filters,
        fields=["name as employee", "first_name","last_name"]
    )
    for i in employees:
      print(i)

    results = []

    # Step 2: For each employee, check if there's a ledger entry
    for emp in employees:
        ledger = frappe.db.get_value(
            "Employee Ledger",
            {"employee": emp.employee},
            ["employee", "added_last_month", "balance_added", "current_balance_owing"],
            as_dict=True
        )

        if ledger:  # Only add if ledger exists
            results.append({
                "employee": emp.employee,
                "employee_name": emp.first_name,
                "added_last_month": ledger.added_last_month,
                "balance_added": ledger.balance_added,
                "current_balance_owing": ledger.current_balance_owing
            })

    for i in results:
        print(i)

    return results
