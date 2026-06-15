INSERT IGNORE INTO `tabReport` (name, report_name, ref_doctype, report_type, is_standard, module, idx, creation, modified, owner) 
VALUES 
('Salary Register', 'Salary Register', 'havano_employee', 'Script Report', 'Yes', 'Havano Zim Payroll', 0, NOW(), NOW(), 'Administrator'), 
('NSSA Report', 'NSSA Report', 'havano_employee', 'Script Report', 'Yes', 'Havano Zim Payroll', 0, NOW(), NOW(), 'Administrator'), 
('SDL Report', 'SDL Report', 'havano_employee', 'Script Report', 'Yes', 'Havano Zim Payroll', 0, NOW(), NOW(), 'Administrator'), 
('NEC Report', 'NEC Report', 'havano_employee', 'Script Report', 'Yes', 'Havano Zim Payroll', 0, NOW(), NOW(), 'Administrator');
