# Qltc prototype - step 6: (a) workers are paid from attendance (absence = loss of pay, overtime paid),
# staff stay on the working schedule; (b) archive Odoo's default leave types Grotek does not use, so
# self-service shows only Earned, Casual, Sick, On Duty, Unpaid. Recomputes September 2026.
# FICTITIOUS PROTOTYPE ONLY - Bharath reviews before real data.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/6_attendance_pay_leave_types.py
import datetime as dt
if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype.')
env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
problems = []

archived = []
for t in env['hr.leave.type'].search([('name', 'in', ['Paid Time Off', 'Sick Time Off', 'Extra Time Off', 'Extra Hours', 'Compensatory Days'])]):
    try:
        with env.cr.savepoint():
            t.active = False
            archived.append(t.name)
    except Exception as ex:
        problems.append(f'leave type {t.name}: {type(ex).__name__}: {ex}')
env.cr.commit()

emps = env['hr.employee'].search([('barcode', 'like', '10%')])
workers = emps.filtered(lambda e: e.employee_type == 'worker')
d1, d2 = dt.date(2026, 9, 1), dt.date(2026, 9, 30)
start, stop = dt.datetime(2026, 8, 31, 18, 30), dt.datetime(2026, 9, 30, 18, 29, 59)  # India month in UTC
Slip = env['hr.payslip']
net_before = sum(l.total for l in env['hr.payslip.line'].search([('slip_id.date_from', '=', d1), ('code', '=', 'NET')]))
redone = 0
for e in workers:
    try:
        with env.cr.savepoint():
            slips = Slip.search([('employee_id', '=', e.id), ('date_from', '=', d1)])
            for s in slips:
                if s.state != 'draft':
                    s.action_payslip_cancel()
                if s.state != 'draft':
                    s.action_payslip_draft()
            e.version_id.write({'work_entry_source': 'attendance'})
            e.version_id.generate_work_entries(start, stop, force=True)
            for s in slips:
                s.compute_sheet()
                s.action_payslip_done()
                redone += 1
    except Exception as ex:
        problems.append(f'{e.name}: {type(ex).__name__}: {ex}')
env.cr.commit()

net_after = sum(l.total for l in env['hr.payslip.line'].search([('slip_id.date_from', '=', d1), ('code', '=', 'NET')]))
wd = {}
for w in env['hr.payslip.worked_days'].search([('payslip_id.date_from', '=', d1), ('payslip_id.employee_id', 'in', workers.ids)]):
    wd[w.code] = wd.get(w.code, 0) + w.number_of_days
print('STEP 6 DONE: archived %s; %d workers paid from attendance, %d payslips recomputed' % (archived, len(workers), redone))
print('  worker worked days by code: %s' % {k: round(v, 1) for k, v in sorted(wd.items())})
print('  total NET September: before %.2f after %.2f' % (net_before, net_after))
sample = workers[:3]
for e in sample:
    s = Slip.search([('employee_id', '=', e.id), ('date_from', '=', d1)], limit=1)
    att = env['hr.attendance'].search_count([('employee_id', '=', e.id), ('check_in', '>=', start), ('check_in', '<=', stop)])
    print('  %-18s attendance days %2d  NET %10.2f  worked days %s' % (e.name, att, sum(l.total for l in s.line_ids if l.code == 'NET'),
          {w.code: w.number_of_days for w in s.worked_days_line_ids}))
for p in problems[:10]:
    print('  PROBLEM:', p)
