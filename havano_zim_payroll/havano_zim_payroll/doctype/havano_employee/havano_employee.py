import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils import flt
from . import base_currency,split_currency
from frappe.model.naming import make_autoname


class havano_employee(Document):
    def autoname(self):
        # get prefix from field, fallback to "BRO"
        prefix = (f"{self.first_name} {self.last_name}").strip().lower()
        # generate the name with global counter
        v=make_autoname(f"-.###")
        self.name =f"{prefix}" + v

    def before_save(self):
        print(self.native_employee_id)
        company = self.company
        # Set payslip type from company
        payslip_type = frappe.db.get_value("Company", company, "custom_payslip_type")
        self.payslip_type = payslip_type
        print(f"-------------------------{payslip_type}")

        if payslip_type == "Base Currency":
            base_currency.main(self)
        elif payslip_type == "Split Currency":
            split_currency.main(self)

        self.remove_deductions_if_on_attachment()

        # Push is_tax_applicable changes back to havano_salary_component master
        self._sync_tax_applicable_to_components()

        # -----------------------------
        # Create ERPNext Employee if not exists
                # -----------------------------
        existing_emp = frappe.db.exists("Employee", self.native_employee_id)

        if existing_emp:
            # UPDATE EMPLOYEE
            employee_doc = frappe.get_doc("Employee", existing_emp)

            employee_doc.first_name = self.first_name
            employee_doc.last_name = self.last_name
            employee_doc.gender = self.gender
            employee_doc.status = self.status
            employee_doc.company = self.company
            employee_doc.date_of_birth = self.date_of_birth
            employee_doc.date_of_joining = self.date_of_joining

            employee_doc.save(ignore_permissions=True)
            frappe.db.commit()

            # frappe.msgprint(f"Updated Employee: {employee_doc.name}")


        else:
            # CREATE EMPLOYEE
            employee_doc = frappe.get_doc({
                "doctype": "Employee",
                "name": self.native_employee_id,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "gender": self.gender,
                "company": self.company,
                "status": "Active",
                "date_of_birth": self.date_of_birth,
                "date_of_joining": self.date_of_joining
            })

            employee_doc.insert(ignore_permissions=True)
            frappe.db.commit()

            self.native_employee_id = employee_doc.name
            #frappe.msgprint(f"Created Employee: {employee_doc.name}")

    def remove_deductions_if_on_attachment(self):
        if not getattr(self, "is_on_attachment", 0):
            return
            
        self.employee_deductions = []
        self.total_deductions = 0
        self.total_deduction_usd = 0
        self.total_deduction_zwg = 0
        self.payee = 0
        self.aids_levy = 0
        self.payee_usd = 0
        self.aids_levy_usd = 0
        self.payee_zwg = 0
        self.aids_levy_zwg = 0
        self.wcif_usd = 0
        self.nec_usd = 0
        self.wcif_zwg = 0
        self.nec_zwg = 0
        self.nec_employee = 0
        self.necwei = 0
        self.nec_employer = 0
        self.cimas_employee = 0
        self.cimas_employer = 0
        self.funeral_employee = 0
        self.funeral_employer = 0
        self.lapf_employee = 0
        self.lapf_employer = 0
        self.allowable_deductions = 0
        self.total_allowable_deductions_usd = 0
        self.total_allowable_deductions_zwg = 0
        
        self.net_income = self.total_income
        if getattr(self, "payslip_type", "") == "Base Currency":
            if getattr(self, "salary_currency", "") == "USD":
                self.total_net_income_usd = self.total_income
            else:
                self.total_net_income_zwg = self.total_income
        elif getattr(self, "payslip_type", "") == "Split Currency":
            self.total_net_income_usd = flt(getattr(self, "total_earnings_usd", 0))
            self.total_net_income_zwg = flt(getattr(self, "total_earnings_zwg", 0))

    def _sync_tax_applicable_to_components(self):
        """When user changes is_tax_applicable on a row, update the salary component master."""
        all_rows = list(self.employee_earnings or []) + list(self.employee_deductions or [])
        for row in all_rows:
            if not row.get("components"):
                continue
            current = frappe.db.get_value(
                "havano_salary_component", row.components, "is_tax_applicable"
            )
            if current is None:
                continue
            row_val = 1 if row.get("is_tax_applicable") else 0
            if int(current) != row_val:
                frappe.db.set_value(
                    "havano_salary_component",
                    row.components,
                    "is_tax_applicable",
                    row_val
                )
                frappe.logger().info(
                    f"[havano_employee] Updated is_tax_applicable={row_val} "
                    f"on component '{row.components}' from employee '{self.name}'"
                )

    @frappe.whitelist()
    def calculate_totals(self):
        """Whitelisted method to trigger calculations from client side."""
        from . import base_currency, split_currency
        
        payslip_type = frappe.db.get_value("Company", self.company, "custom_payslip_type")
        self.payslip_type = payslip_type

        if payslip_type == "Base Currency":
            base_currency.main(self)
        elif payslip_type == "Split Currency":
            split_currency.main(self)
        
        self.remove_deductions_if_on_attachment()
        
        # Return the modified fields so the client can update the UI
        return self.as_dict()
