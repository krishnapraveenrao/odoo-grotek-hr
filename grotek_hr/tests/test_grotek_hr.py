from datetime import date, datetime, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestGrotekHr(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        # Monday to Friday, 9:00-17:30 (UTC, so local dates are the same as UTC dates).
        cls.calendar_day = cls.env['resource.calendar'].create({
            'name': 'Test day shift', 'tz': 'UTC', 'company_id': cls.company.id,
            'attendance_ids': [(0, 0, {'name': 'Day %s' % d, 'dayofweek': str(d), 'hour_from': 9, 'hour_to': 17.5})
                                      for d in range(5)],
        })
        cls.calendar_night = cls.calendar_day.copy({'name': 'Test night shift'})
        cls.hr_user = cls.env['res.users'].create({
            'name': 'Test HR', 'login': 'grotek_test_hr',
            'group_ids': [(6, 0, [cls.env.ref('hr.group_hr_user').id, cls.env.ref('hr_holidays.group_hr_holidays_user').id])],
        })
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Test Manager', 'login': 'grotek_test_mgr',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.staff_user = cls.env['res.users'].create({
            'name': 'Test Staff', 'login': 'grotek_test_staff',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Test Manager', 'user_id': cls.manager_user.id, 'tz': 'UTC',
            'resource_calendar_id': cls.calendar_day.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Staff', 'user_id': cls.staff_user.id, 'parent_id': cls.manager.id, 'tz': 'UTC',
            'resource_calendar_id': cls.calendar_day.id,
        })
        cls.comp_off = cls.env['hr.leave.type'].search([('name', '=ilike', 'Comp Off')], limit=1) or \
            cls.env['hr.leave.type'].create({
                'name': 'Comp Off', 'requires_allocation': True, 'request_unit': 'half_day',
            })

    # --- Biometric ID ---------------------------------------------------------------

    def test_biometric_id_never_reused(self):
        self.employee.x_biometric_id = '9001'
        self.employee.action_archive()
        with self.assertRaises(ValidationError):
            self.manager.x_biometric_id = '9001'

    # --- Shift change ---------------------------------------------------------------

    def test_shift_change_applies_and_ends(self):
        today = date.today()
        change = self.env['grotek.shift.change'].with_user(self.hr_user).create({
            'employee_id': self.employee.id, 'calendar_id': self.calendar_night.id,
            'date_from': today + timedelta(days=2), 'date_to': today + timedelta(days=4),
        })
        change.action_schedule()
        self.assertEqual(change.state, 'scheduled')
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_day)

        change._apply_due(today + timedelta(days=2))
        self.assertEqual(change.state, 'applied')
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_night)
        self.assertEqual(change.previous_calendar_id, self.calendar_day)

        change._apply_due(today + timedelta(days=5))
        self.assertEqual(change.state, 'ended')
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_day)

    def test_shift_change_today_applies_at_once(self):
        change = self.env['grotek.shift.change'].with_user(self.hr_user).create({
            'employee_id': self.employee.id, 'calendar_id': self.calendar_night.id, 'date_from': date.today(),
        })
        change.action_schedule()
        self.assertEqual(change.state, 'applied')
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_night)

    def test_shift_change_overlap_refused(self):
        Change = self.env['grotek.shift.change'].with_user(self.hr_user)
        today = date.today()
        Change.create({'employee_id': self.employee.id, 'calendar_id': self.calendar_night.id,
                       'date_from': today + timedelta(days=10)}).action_schedule()
        second = Change.create({'employee_id': self.employee.id, 'calendar_id': self.calendar_night.id,
                                'date_from': today + timedelta(days=20)})
        with self.assertRaises(ValidationError):
            second.action_schedule()

    def test_shift_change_only_hr(self):
        change = self.env['grotek.shift.change'].create({
            'employee_id': self.employee.id, 'calendar_id': self.calendar_night.id, 'date_from': date.today(),
        })
        with self.assertRaises(UserError):
            change.with_user(self.manager_user).action_schedule()

    # --- OD attendance --------------------------------------------------------------

    def test_od_manager_approves_creates_attendance(self):
        od = self.env['grotek.od.attendance'].with_user(self.staff_user).create({
            'employee_id': self.employee.id, 'reason': 'Customer visit',
            'check_in': datetime(2026, 9, 1, 9, 0), 'check_out': datetime(2026, 9, 1, 17, 30),
        })
        od.action_submit()
        self.assertEqual(od.state, 'submitted')
        with self.assertRaises(UserError):
            od.with_user(self.staff_user).action_approve()
        od.with_user(self.manager_user).action_approve()
        self.assertEqual(od.state, 'approved')
        self.assertTrue(od.attendance_id)
        self.assertEqual(od.attendance_id.check_out, datetime(2026, 9, 1, 17, 30))

    def test_od_times_checked(self):
        with self.assertRaises(ValidationError):
            self.env['grotek.od.attendance'].create({
                'employee_id': self.employee.id, 'reason': 'x',
                'check_in': datetime(2026, 9, 1, 17, 0), 'check_out': datetime(2026, 9, 1, 9, 0),
            })

    # --- Extra attendance (comp-off) ------------------------------------------------

    def _attend(self, day, hours):
        start = datetime.combine(day, datetime.min.time()) + timedelta(hours=9)
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id, 'check_in': start, 'check_out': start + timedelta(hours=hours),
        })

    def test_extra_attendance_weekly_off_to_comp_off(self):
        sunday = date(2026, 9, 6)
        monday = date(2026, 9, 7)
        self._attend(sunday, 8)
        self._attend(monday, 8)
        Extra = self.env['grotek.extra.attendance']
        found = Extra._detect(sunday, monday).filtered(lambda r: r.employee_id == self.employee)
        self.assertEqual(len(found), 1)
        self.assertEqual(found.date, sunday)
        self.assertEqual(found.day_type, 'weekly_off')
        self.assertEqual(found.comp_off_days, 1.0)
        # Running again finds nothing new.
        self.assertFalse(Extra._detect(sunday, monday).filtered(lambda r: r.employee_id == self.employee))

        with self.assertRaises(UserError):
            found.with_user(self.staff_user).action_approve()
        found.with_user(self.manager_user).action_approve()
        self.assertEqual(found.state, 'allocated')
        self.assertEqual(found.allocation_id.holiday_status_id, self.comp_off)
        self.assertEqual(found.allocation_id.number_of_days, 1.0)
        self.assertEqual(found.allocation_id.state, 'validate')
        self.assertEqual(found.allocation_id.date_to, sunday + timedelta(days=30))

    def test_extra_attendance_holiday(self):
        wednesday = date(2026, 9, 9)
        self.env['resource.calendar.leaves'].create({
            'name': 'Test holiday', 'calendar_id': self.calendar_day.id,
            'date_from': datetime(2026, 9, 9, 0, 0), 'date_to': datetime(2026, 9, 9, 23, 59),
        })
        self._attend(wednesday, 8)
        found = self.env['grotek.extra.attendance']._detect(wednesday, wednesday).filtered(
            lambda r: r.employee_id == self.employee)
        self.assertEqual(found.day_type, 'holiday')

    def test_extra_attendance_short_day_no_comp_off(self):
        saturday = date(2026, 9, 12)
        self._attend(saturday, 3)
        found = self.env['grotek.extra.attendance']._detect(saturday, saturday).filtered(
            lambda r: r.employee_id == self.employee)
        self.assertEqual(found.comp_off_days, 0.0)
        with self.assertRaises(UserError):
            found.with_user(self.hr_user).action_approve()
