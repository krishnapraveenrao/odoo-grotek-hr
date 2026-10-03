# Qltc prototype - step 5: PF rules - a member restricted to the wage ceiling pays exactly 12% of
# min(BASIC, Rs 15,000); a member on actual pays 12% of BASIC. Odoo's standard rule turned the
# ceiling into a percentage of the contract basic, so overtime (higher paid basic) over-deducted PF.
# Changes the PF and PFE rules of "India: Regular Pay" - Bharath reviews before real Grotek data.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/5_pf_rule_cap.py
import datetime as dt
if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype.')
env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
rules = env['hr.salary.rule'].search([('struct_id.name', 'ilike', 'India: Regular Pay'), ('code', 'in', ['PF', 'PFE'])])
CODE = """
ceiling = payslip._rule_parameter('l10n_in_pf_amount')
rate = payslip._rule_parameter('l10n_in_pf_percent')
if version.%(type)s == 'fixed':
    result = -min(categories['BASIC'], ceiling)
else:
    result = -categories['BASIC']
result_rate = rate * 100
"""
for r in rules:
    t = 'l10n_in_pf_employee_type' if r.code == 'PF' else 'l10n_in_pf_employer_type'
    r.write({'amount_select': 'code', 'amount_python_compute': CODE % {'type': t}})
    print('rule %s updated' % r.code)
env.cr.commit()
d1 = dt.date(2026, 9, 1)
problems, redone = [], 0
for e in env['hr.employee'].search([('barcode', 'like', '10%')]):
    try:
        with env.cr.savepoint():
            for s in env['hr.payslip'].search([('employee_id', '=', e.id), ('date_from', '=', d1)]):
                if s.state != 'draft':
                    s.action_payslip_cancel()
                if s.state != 'draft':
                    s.action_payslip_draft()
                s.compute_sheet()
                s.action_payslip_done()
                redone += 1
    except Exception as ex:
        problems.append(f'{e.name}: {type(ex).__name__}: {ex}')
env.cr.commit()
bad = []
for l in env['hr.payslip.line'].search([('slip_id.date_from', '=', d1), ('code', '=', 'PF')]):
    basic = sum(x.total for x in l.slip_id.line_ids if x.code == 'BASIC')
    ok = any(abs(round(w * 0.12) - round(-l.total)) <= 1 for w in (basic, min(basic, 15000)))
    if not ok:
        bad.append(f'{l.slip_id.employee_id.name}: PF {-l.total:.0f} vs basic {basic:.0f}')
print('STEP 5 DONE: %d payslips recomputed; PF lines not 12%% of PF wages: %d' % (redone, len(bad)))
for b in bad + problems:
    print('  PROBLEM:', b)
