# Prototype setup scripts (FICTITIOUS DATA ONLY)

Run in the Odoo.sh web shell of the production build of `qltc-in-odoo-grotek-hr`, in order:

```
odoo-bin shell --no-http < ~/src/user/scripts/1_company_modules.py
odoo-bin shell --no-http < ~/src/user/scripts/2_fictitious_data.py
odoo-bin shell --no-http < ~/src/user/scripts/3_statutory_flags.py
odoo-bin shell --no-http < ~/src/user/scripts/4_esi_pt_lwf.py
odoo-bin shell --no-http < ~/src/user/scripts/5_pf_rule_cap.py
odoo-bin shell --no-http < ~/src/user/scripts/6_attendance_pay_leave_types.py
odoo-bin shell --no-http < ~/src/user/scripts/7_planning_comp_off.py
```

- Script 1 names the company Grotek (India, Karnataka), marks the database as a fictitious prototype and installs India Payroll + Time Off.
- Script 2 loads made-up people (25 employees, 7 departments, salaries, bank accounts, leave balances, holidays, September 2026 attendance and payslips) and creates the "Web app API" user (no password, no API key).
- Script 3 switches on PF, ESIC, PT and LWF (fictitious registration numbers), ESIC only up to Rs 21,000, TDS for higher salaries, and recomputes September 2026.
- Script 4 sets ESI rates (0.75% / 3.25% up to Rs 21,000), the Karnataka PT table and LWF amounts (yearly in reality; September here for the demo) and recomputes September.
- Script 5 changes the PF/PFE rules so a member restricted to the ceiling pays exactly 12% of min(basic, Rs 15,000) (Odoo's standard rule over-deducted when overtime raised the paid basic); Bharath reviews before real data.
- Script 6 pays workers from attendance (work entry source Attendances; staff stay on the schedule) and archives Odoo's default leave types Grotek does not use; recomputes September.
- Script 7 installs Planning (shift rosters) and restores comp-off as 'Comp Off' (uses up approved extra hours).
- Script 2 refuses to run unless script 1's marker is set and the database has no other employees. Never run these on a live database. Real Grotek data is loaded from the Qltc templates once the web app runs over HTTPS (notes 05, H-P7).
