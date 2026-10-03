# Qltc prototype - step 7: install Planning (shift rosters, Savior "shift assignment / schedule upload")
# and restore comp-off as a Grotek leave type "Comp Off" that uses up approved extra hours (Savior COF).
# FICTITIOUS PROTOTYPE ONLY. Run: odoo-bin shell --no-http < ~/src/user/scripts/7_planning_comp_off.py
if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype.')
LT = env['hr.leave.type'].with_context(active_test=False)
co = LT.search([('name', 'in', ['Comp Off', 'Compensatory Days'])], limit=1)
vals = {'name': 'Comp Off', 'active': True}
f = env['hr.leave.type'].fields_get(['requires_allocation', 'overtime_deductible'])
if 'overtime_deductible' in f:
    vals['overtime_deductible'] = True
if 'requires_allocation' in f:
    vals['requires_allocation'] = 'no' if f['requires_allocation']['type'] == 'selection' else False
if co:
    co.write(vals)
else:
    co = LT.create(vals)
env.cr.commit()
mods = env['ir.module.module'].search([('name', '=', 'planning'), ('state', '!=', 'installed')])
if mods:
    mods.button_immediate_install()
env.cr.commit()
print('STEP 7 DONE: leave type %s (deducts extra hours: %s); planning: %s' % (co.name, co.overtime_deductible if 'overtime_deductible' in f else 'n/a', env['ir.module.module'].search([('name', '=', 'planning')]).state))
