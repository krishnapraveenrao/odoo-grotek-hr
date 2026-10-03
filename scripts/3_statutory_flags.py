# Qltc prototype - step 3: switch on India statutory deductions (FICTITIOUS registration numbers) and recompute September 2026.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/3_statutory_flags.py
import datetime as dt
if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype.')
env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
company = env.ref('base.main_company')
company.write({
    'l10n_in_provident_fund': True, 'l10n_in_esic': True, 'l10n_in_pt': True, 'l10n_in_labour_welfare': True,
    'l10n_in_epf_employer_id': 'TEST/EPF/0000001', 'l10n_in_esic_ip_number': 'TEST0000000001',
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
Slip = env['hr.payslip']
redone = 0
for e in emps:
    try:
        old = Slip.search([('employee_id', '=', e.id), ('date_from', '=', d1)])
        for s in old:
            for m in ('action_payslip_cancel', 'action_payslip_draft'):
                if hasattr(s, m) and s.state != 'draft':
                    try:
                        getattr(s, m)()
                    except Exception:
                        pass
        old.filtered(lambda s: s.state in ('draft', 'cancel')).unlink()
        slip = Slip.create({'employee_id': e.id, 'date_from': d1, 'date_to': dt.date(2026, 9, 30), 'name': f'Salary Slip - {e.name} - September 2026'})
        slip.compute_sheet()
        slip.action_payslip_done()
        redone += 1
    except Exception as ex:
        problems.append(f'{e.name}: payslip ({ex})')
env.cr.commit()
codes = env['hr.payslip.line'].read_group([('slip_id.date_from', '=', d1)], ['code', 'name', 'total:sum'], ['code', 'name'], lazy=False)
print('STEP 3 DONE: %d payslips recomputed' % redone)
for c in sorted(codes, key=lambda c: c['code']):
    print('  code %-12s %-40s %12.2f' % (c['code'], c['name'], c['total']))
for p in problems:
    print('  PROBLEM:', p)
