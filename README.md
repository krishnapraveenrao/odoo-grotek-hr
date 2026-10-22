# Odoo.sh - Grotek HR & payroll

The Odoo.sh project for Grotek's HR and payroll (Odoo 19 Enterprise, India payroll), used by the Qltc SAP B1 web app's HR add-on (`qltc-in/qltc-sapb1-web-app`, `addons/hr/`) through Odoo's JSON-2 API.

- Branch `main` = Odoo.sh production. Odoo apps and India payroll are installed from the Odoo.sh database; Grotek's own module is `grotek_hr` (below).
- Never commit employee data, salaries, API keys or passwords here. The web app's Odoo API key lives only in the server's settings / AWS Secrets Manager.
- Decision: notes 05, H-P7 (3 Oct 2026), in `qltc-in/qltc-sapb1-web-app` - prototype with fictitious data first; real Grotek data only once the web app is served over HTTPS.

## Module `grotek_hr` (Odoo 19)

Grotek's own HR records, in Python, for the SAP B1 web app's HR add-on (#390 in `qltc-in/qltc-sapb1-web-app`). Menu: Employees > Shifts & OD.

| Record | What it does |
|---|---|
| Shift change (`grotek.shift.change`) | HR gives an employee a new working schedule from a date, optionally until a date. A daily job applies it on the From date and puts the shift before back the day after the To date. Many at once: import from Excel. |
| OD attendance (`grotek.od.attendance`) | The employee asks for on-duty attendance (check-in, check-out, reason). The manager (the employee's Manager in Odoo) or HR approves; the attendance line is created. |
| Extra attendance (`grotek.extra.attendance`) | A daily job lists attendance on a weekly off (POW) or a public holiday (POH). The manager gives comp-off: a "Comp Off" allocation is created and validated. |
| Biometric ID (`hr.employee.x_biometric_id`) | The attendance device number. Never reused, archived employees included. Odoo's Badge ID (barcode) is not used. |

Comp-off follows the old HRMS (Bharath's decision, 5 Oct 2026): the Comp Off time-off type **requires an allocation** and is **not** taken from extra hours. This replaces the Comp Off part of script 7.

Settings (Settings > Technical > System Parameters): `grotek_hr.comp_off_full_day_hours` (7.5), `grotek_hr.comp_off_half_day_hours` (0 = no half days), `grotek_hr.comp_off_valid_days` (30), `grotek_hr.comp_off_claim_window_days` (31), and optionally `grotek_hr.comp_off_leave_type_id`.

Shift change writes the employee's Working Hours (in Odoo 19, the current version's). Tests: `grotek_hr/tests` (run by the Odoo.sh branch build).
