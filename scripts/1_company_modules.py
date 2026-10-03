# Qltc prototype - step 1: company and modules. FICTITIOUS PROTOTYPE ONLY.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/1_company_modules.py
if env['hr.employee'].search_count([]) > 1:
    raise SystemExit('ABORT: this database already has employees - not a fresh prototype.')
IN = env.ref('base.in')
KA = env['res.country.state'].search([('country_id', '=', IN.id), ('code', '=', 'KA')], limit=1)
company = env.ref('base.main_company')
company.write({'name': 'Grotek', 'country_id': IN.id, 'state_id': KA.id, 'city': 'Shivamogga', 'zip': '577201',
               'street': 'Test address - prototype', 'currency_id': env.ref('base.INR').id})
env['ir.config_parameter'].sudo().set_param('qltc.prototype_fictitious_data', '1')
env.ref('base.user_admin').write({'tz': 'Asia/Kolkata'})
env.cr.commit()
mods = env['ir.module.module'].search([('name', 'in', ['hr_holidays', 'hr_payroll_holidays', 'hr_work_entry_holidays', 'l10n_in_hr_payroll'])])
to_install = mods.filtered(lambda m: m.state != 'installed')
print('Installing:', to_install.mapped('name'))
if to_install:
    to_install.button_immediate_install()
env.cr.commit()
print('STEP 1 DONE: company', company.name, company.country_id.code, company.state_id.code)
