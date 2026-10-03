# Qltc prototype - step 2: FICTITIOUS employees and payroll for September 2026.
# Run: odoo-bin shell --no-http < ~/src/user/scripts/2_fictitious_data.py
import datetime as dt
import random
from odoo import fields

if env['ir.config_parameter'].sudo().get_param('qltc.prototype_fictitious_data') != '1':
    raise SystemExit('ABORT: not marked as a fictitious prototype (run step 1 first).')
if env['hr.employee'].search_count([('barcode', 'not like', '10%')]) > 1:
    raise SystemExit('ABORT: database has other employees.')

random.seed(7)
company = env.ref('base.main_company')
env = env(context=dict(env.context, tz='Asia/Kolkata', tracking_disable=True, mail_create_nolog=True, mail_notrack=True))
IN = env.ref('base.in')
KA = env['res.country.state'].search([('country_id', '=', IN.id), ('code', '=', 'KA')], limit=1)
EMP = env['hr.employee']
ok, problems = [], []

def has(model, f):
    return f in env[model]._fields

def utc(d, hours):
    """India local date + decimal hours -> naive UTC datetime."""
    return dt.datetime.combine(d, dt.time()) + dt.timedelta(hours=hours) - dt.timedelta(hours=5, minutes=30)

# --- working schedules (Mon-Sat) ---
def calendar(name, start, end):
    cal = env['resource.calendar'].search([('name', '=', name), ('company_id', '=', company.id)], limit=1)
    if cal:
        return cal
    mid = start + 4
    lines = []
    for d in range(6):
        for nm, a, b, period in ((f'{d} morning', start, mid, 'morning'), (f'{d} afternoon', mid + 0.5, end, 'afternoon')):
            vals = {'name': nm, 'dayofweek': str(d), 'hour_from': a, 'hour_to': b}
            if has('resource.calendar.attendance', 'day_period'):
                vals['day_period'] = period
            lines.append((0, 0, vals))
    return env['resource.calendar'].create({'name': name, 'company_id': company.id, 'tz': 'Asia/Kolkata', 'attendance_ids': [(5, 0, 0)] + lines})

CAL = {'G': calendar('General Shift 08:00-16:30', 8, 16.5), 'A': calendar('Shift A 06:00-14:00', 6, 14), 'B': calendar('Shift B 14:00-22:00', 14, 22)}
ok.append('3 working schedules')

# --- leave types ---
def leave_type(name, needs_alloc):
    t = env['hr.leave.type'].search([('name', '=', name)], limit=1)
    if t:
        return t
    vals = {'name': name, 'company_id': company.id}
    f = env['hr.leave.type']._fields.get('requires_allocation')
    if f is not None:
        vals['requires_allocation'] = (('yes' if needs_alloc else 'no') if f.type == 'selection' else needs_alloc)
    return env['hr.leave.type'].create(vals)

LT = {n: leave_type(n, a) for n, a in (('Earned Leave', True), ('Casual Leave', True), ('Sick Leave', True), ('On Duty', False), ('Unpaid', False))}
ok.append('5 leave types')

# --- departments ---
DEPTS = ['Machining', 'Foundry', 'Quality', 'Stores', 'Maintenance', 'Admin & HR', 'Accounts']
D = {}
for n in DEPTS:
    D[n] = env['hr.department'].search([('name', '=', n), ('company_id', '=', company.id)], limit=1) or env['hr.department'].create({'name': n, 'company_id': company.id})
ok.append('7 departments')

# --- employees (made-up people) ---
first = ['Ravi', 'Suresh', 'Mahesh', 'Kiran', 'Anil', 'Prakash', 'Manjunath', 'Lokesh', 'Naveen', 'Ganesh', 'Shankar', 'Raghu', 'Deepa', 'Kavya', 'Lakshmi', 'Asha', 'Pooja', 'Shwetha', 'Harish', 'Venkatesh', 'Ramesh', 'Sunil', 'Arun', 'Divya', 'Meena']
last = ['Kumar', 'Gowda', 'Rao', 'Shetty', 'Naik', 'Hegde', 'Reddy', 'Patil', 'Murthy', 'Prasad']
female = {'Deepa', 'Kavya', 'Lakshmi', 'Asha', 'Pooja', 'Shwetha', 'Divya', 'Meena'}
jobs = {'Machining': ['CNC Operator', 'VMC Operator', 'Machinist'], 'Foundry': ['Moulder', 'Melter', 'Fettler'], 'Quality': ['Quality Inspector', 'Lab Technician'], 'Stores': ['Storekeeper', 'Store Assistant'], 'Maintenance': ['Electrician', 'Fitter'], 'Admin & HR': ['HR Executive', 'Admin Officer'], 'Accounts': ['Accountant']}
plan = ['Machining'] * 7 + ['Foundry'] * 7 + ['Quality'] * 3 + ['Stores'] * 2 + ['Maintenance'] * 2 + ['Admin & HR'] * 2 + ['Accounts'] * 2
struct_type = env['hr.payroll.structure.type'].search([('country_id', '=', IN.id)], limit=1)
if not struct_type:
    problems.append('No India structure type found - salaries set without a structure type.')
in_fields = sorted(f for f in EMP._fields if f.startswith('l10n_in'))
print('India employee fields available:', in_fields)

bank = env['res.bank'].search([('bic', '=', 'SBIN0000001')], limit=1) or env['res.bank'].create({'name': 'State Bank of India (TEST)', 'bic': 'SBIN0000001'})
rows = []
for k, dept in enumerate(plan, 1):
    staff = dept in ('Admin & HR', 'Accounts') or k in (1, 8)
    basic = random.choice([22000, 26000, 30000, 35000]) if staff else random.choice([9000, 10000, 11000, 12000, 13000])
    gross = int(basic * (1.8 if staff else 1.6)) // 100 * 100
    name = f'{first[k - 1]} {random.choice(last)}'
    shift = 'G' if staff else ('A' if k % 2 else 'B')
    badge = str(1000 + k)
    emp = EMP.search([('barcode', '=', badge)], limit=1)
    vals = {
        'name': name, 'company_id': company.id, 'department_id': D[dept].id,
        'job_title': 'Supervisor' if k in (1, 8) else random.choice(jobs[dept]),
        'employee_type': 'employee' if staff else ('worker' if 'worker' in dict(EMP._fields['employee_type'].selection) else 'employee'),
        'mobile_phone': f'90000{k:05d}', 'barcode': badge, 'pin': f'{k:04d}',
        'resource_calendar_id': CAL[shift].id,
        'birthday': dt.date(1975 + k % 25, 1 + k % 12, 1 + k % 27),
        'sex': 'female' if first[k - 1] in female else 'male',
        'marital': 'married' if k % 3 else 'single',
        'private_city': 'Shivamogga', 'private_state_id': KA.id, 'private_zip': '577201', 'private_country_id': IN.id,
    }
    for f, v in (('l10n_in_uan', f'9000000{k:05d}'), ('l10n_in_pan', f'TESPT{k:04d}A'), ('l10n_in_esic_number', f'90000{k:05d}' if gross <= 21000 else False)):
        if f in EMP._fields:
            vals[f] = v
    # Odoo's hr_skills adds keys to the dict given to create(), so always pass copies.
    if emp:
        emp.write(dict(vals))
    else:
        emp = EMP.create(dict(vals))
    joined = dt.date(2015 + k % 11, 1 + (k * 5) % 12, 1 + (k * 3) % 27)
    vver = {'wage': gross, 'contract_date_start': joined}
    if struct_type:
        vver['structure_type_id'] = struct_type.id
    try:
        emp.write(vver)
    except Exception as e:
        problems.append(f'{name}: salary not set ({e})')
    try:
        acc = env['res.partner.bank'].search([('acc_number', '=', f'00000{k:07d}')], limit=1) or env['res.partner.bank'].create({'acc_number': f'00000{k:07d}', 'partner_id': emp.work_contact_id.id, 'bank_id': bank.id})
        emp.write({'bank_account_ids': [(6, 0, [acc.id])]})
    except Exception as e:
        problems.append(f'{name}: bank account ({e})')
    rows.append((emp, dept, staff, shift, joined))
ok.append(f'{len(rows)} employees with salary and bank account')

# reporting managers: supervisors for Machining/Foundry, HR executive for the rest
sup = {'Machining': rows[0][0], 'Foundry': rows[7][0]}
hr_head = rows[21][0]
for emp, dept, *_ in rows:
    mgr = sup.get(dept, hr_head)
    if mgr != emp:
        emp.parent_id = mgr
    elif emp != hr_head:
        emp.parent_id = hr_head
ok.append('reporting managers')

# --- leave balances ---
Alloc = env['hr.leave.allocation']
for emp, *_ in rows:
    for t, days in (('Earned Leave', random.choice([4, 6, 8.5, 12])), ('Casual Leave', random.choice([3, 4, 5])), ('Sick Leave', random.choice([2, 3, 6]))):
        if Alloc.search_count([('employee_id', '=', emp.id), ('holiday_status_id', '=', LT[t].id)]):
            continue
        try:
            a = Alloc.create({'name': 'Opening balance (TEST)', 'employee_id': emp.id, 'holiday_status_id': LT[t].id, 'number_of_days': days, 'date_from': dt.date(2026, 9, 1), 'allocation_type': 'regular'})
            for m in ('action_approve', 'action_validate'):
                if a.state not in ('validate',) and hasattr(a, m):
                    try:
                        getattr(a, m)()
                    except Exception:
                        pass
        except Exception as e:
            problems.append(f'allocation {emp.name} {t}: {e}')
ok.append('leave balances')

# --- public holidays (fixed-date only) ---
for n, d in (('Gandhi Jayanti', dt.date(2026, 10, 2)), ('Kannada Rajyotsava', dt.date(2026, 11, 1)), ('Christmas', dt.date(2026, 12, 25)), ('Republic Day', dt.date(2027, 1, 26))):
    if not env['resource.calendar.leaves'].search_count([('name', '=', n), ('date_from', '=', utc(d, 0))]):
        env['resource.calendar.leaves'].create({'name': n, 'date_from': utc(d, 0), 'date_to': utc(d, 23.99), 'company_id': company.id, 'resource_id': False, 'calendar_id': False})
ok.append('public holidays')

# --- September 2026 attendance (and 1 Oct) from the shift times, with some absences and overtime ---
Att = env['hr.attendance']
start = {'G': 8, 'A': 6, 'B': 14}
day = dt.date(2026, 9, 1)
count = 0
while day <= dt.date(2026, 10, 1):
    if day.weekday() < 6:
        for emp, dept, staff, shift, joined in rows:
            if random.random() < 0.07 or Att.search_count([('employee_id', '=', emp.id), ('check_in', '>=', utc(day, 0)), ('check_in', '<', utc(day, 24))]):
                continue
            s = start[shift] + random.uniform(-0.2, 0.25)
            e = s + 8.5 + (random.choice([0, 0, 0, 1, 2]) if not staff else 0) + random.uniform(0, 0.3)
            Att.create({'employee_id': emp.id, 'check_in': utc(day, s), 'check_out': utc(day, e)})
            count += 1
    day += dt.timedelta(days=1)
ok.append(f'{count} attendance records')

# --- September 2026 payslips: generate work entries, compute, mark Done ---
d1, d2 = dt.date(2026, 9, 1), dt.date(2026, 9, 30)
Slip = env['hr.payslip']
done = 0
for emp, *_ in rows:
    try:
        ver = emp.version_id
        for m in ('generate_work_entries', '_generate_work_entries'):
            if hasattr(ver, m):
                try:
                    getattr(ver, m)(d1, d2)
                except TypeError:
                    getattr(ver, m)(dt.datetime.combine(d1, dt.time()), dt.datetime.combine(d2, dt.time(23, 59)))
                break
        slip = Slip.search([('employee_id', '=', emp.id), ('date_from', '=', d1)], limit=1) or Slip.create({'employee_id': emp.id, 'date_from': d1, 'date_to': d2, 'name': f'Salary Slip - {emp.name} - September 2026'})
        slip.compute_sheet()
        if slip.state not in ('done', 'paid'):
            slip.action_payslip_done()
        done += 1
    except Exception as e:
        problems.append(f'payslip {emp.name}: {e}')
ok.append(f'{done} September 2026 payslips Done')

# --- web app API user (no password, no API key - Krishna creates the key himself) ---
user = env['res.users'].search([('login', '=', 'webapp-api')], limit=1)
groups = [env.ref(x).id for x in ('base.group_user', 'hr.group_hr_manager', 'hr_payroll.group_hr_payroll_manager', 'hr_holidays.group_hr_holidays_manager', 'hr_attendance.group_hr_attendance_manager') if env.ref(x, raise_if_not_found=False)]
gfield = 'group_ids' if 'group_ids' in env['res.users']._fields else 'groups_id'
if not user:
    user = env['res.users'].create({'name': 'Web app API', 'login': 'webapp-api', 'company_id': company.id, 'company_ids': [(6, 0, [company.id])], gfield: [(6, 0, groups)], 'tz': 'Asia/Kolkata'})
ok.append(f'API user webapp-api (id {user.id}), company id {company.id}')

env.cr.commit()
print('\n'.join(['STEP 2 DONE:'] + ['  ok: ' + x for x in ok] + ['  PROBLEM: ' + p for p in problems]))
