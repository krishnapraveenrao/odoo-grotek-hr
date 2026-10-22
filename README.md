# Odoo.sh - Grotek HR & payroll

The Odoo.sh project for Grotek's HR and payroll (Odoo 19 Enterprise, India payroll), used by the Qltc SAP B1 web app's HR add-on (`qltc-in/qltc-sapb1-web-app`, `addons/hr/`) through Odoo's JSON-2 API.

- Branch `main` = Odoo.sh production. No custom modules yet; Odoo apps and India payroll are installed from the Odoo.sh database.
- Never commit employee data, salaries, API keys or passwords here. The web app's Odoo API key lives only in the server's settings / AWS Secrets Manager.
- Decision: notes 05, H-P7 (3 Oct 2026), in `qltc-in/qltc-sapb1-web-app` - prototype with fictitious data first; real Grotek data only once the web app is served over HTTPS.
- `grotek_embed/` (frame test, 22 Oct 2026): a small module that lets the web app (2608) show Odoo screens inside its own tabs, by naming the 2608 hosts as allowed frame parents (system parameter `grotek_embed.frame_ancestors`, https origins only). It must be on `main` (production) and installed from Apps (Update Apps List, then install) to take effect. Test address: `hr-test.qltc.in` (custom domain on production).
