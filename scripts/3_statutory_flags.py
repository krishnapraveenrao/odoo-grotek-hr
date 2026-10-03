# Qltc prototype - step 3: switch on India statutory deductions (FICTITIOUS registration numbers) and recompute September 2026.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/3_statutory_flags.py
import datetime as dt
if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype.')
env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
company = env.ref('base.main_company')
company.write({
    'l10n_in_provident_fund': True, 'l10n_in_esic': True, 'l10n_in_pt': True, 'l10n_in_labour_welfare': True,
    # Odoo checks: EPF employer id XX/XXX/1234567/000; company ESIC IP number exactly 17 digits (fictitious values)
    'l10n_in_epf_employer_id': 'TS/TST/0000001/000', 'l10n_in_esic_ip_number': '99000000000000001',
    'l10n_in_pt_number': 'TEST-PT-0001', 'l10n_in_labour_identification_number': 'TEST-LWF-0001',
})
problems = []
emps = env['hr.employee'].search([('barcode', 'like', '10%')])
for e in emps:
    vals = {'l10n_in_provident_fund': True, 'l10n_in_pf_employee_type': 'fixed', 'l10n_in_pf_employer_type': 'fixed',
            'l10n_in_esic': e.wage <= 21000, 'l10n_in_pt': True, 'l10n_in_labour_welfare': True}
    if e.wage >= 40000:
        vals['l10n_in_tds'] = round(e.wage * 0.03)
    try:
        e.version_id.write(vals)
    except Exception as ex:
        problems.append(f'{e.name}: flags ({ex})')

d1 = dt.date(2026, 9, 1)
env.cr.commit()  # keep the flags even if a payslip below fails
Slip = env['hr.payslip']
redone = 0
for e in emps:
    try:
        with env.cr.savepoint():
            for s in Slip.search([('employee_id', '=', e.id), ('date_from', '=', d1)]):
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
    k = (l.code, l.name)
    totals[k] = totals.get(k, 0) + l.total
print('STEP 3 DONE: %d payslips recomputed' % redone)
for (code, name), t in sorted(totals.items()):
    print('  code %-12s %-40s %12.2f' % (code, name, t))
for p in problems[:10]:
    print('  PROBLEM:', p)
