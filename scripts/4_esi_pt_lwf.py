# Qltc prototype - step 4: ESI rates, Karnataka PT slabs and LWF amounts on each employee version; recompute September 2026.
# FICTITIOUS PROTOTYPE ONLY. Karnataka LWF (Rs 50 employee / Rs 100 employer) is yearly (December) - put in September
# here only so the web app's LWF screen has figures to show.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/4_esi_pt_lwf.py
import datetime as dt
if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype.')
env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
pt_ka = env['hr.rule.parameter'].search([('code', '=', 'l10n_in_pt_ka')], limit=1)
problems = []
emps = env['hr.employee'].search([('barcode', 'like', '10%')])
for e in emps:
    try:
        with env.cr.savepoint():
            e.version_id.write({
                'pt_rule_parameter_id': pt_ka.id or False,
                'l10n_in_esic_employee_percentage': 0.0075 if e.wage <= 21000 else 0,
                'l10n_in_esic_employer_percentage': 0.0325 if e.wage <= 21000 else 0,
                'l10n_in_lwf_employee_contribution': 50,
                'l10n_in_lwf_employer_contribution': 100,
            })
    except Exception as ex:
        problems.append(f'{e.name}: version ({type(ex).__name__}: {ex})')
env.cr.commit()
d1 = dt.date(2026, 9, 1)
redone = 0
for e in emps:
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
        problems.append(f'{e.name}: payslip ({type(ex).__name__}: {ex})')
env.cr.commit()
totals = {}
for l in env['hr.payslip.line'].search([('slip_id.date_from', '=', d1)]):
    totals[(l.code, l.name)] = totals.get((l.code, l.name), 0) + l.total
print('STEP 4 DONE: %d payslips recomputed; PT table %s' % (redone, pt_ka.code))
for (code, name), t in sorted(totals.items()):
    print('  code %-8s %-45s %12.2f' % (code, name[:45], t))
for p in problems[:10]:
    print('  PROBLEM:', p)
