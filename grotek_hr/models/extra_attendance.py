from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PARAM = 'grotek_hr.'


class GrotekExtraAttendance(models.Model):
    """Extra attendance: work on a weekly off (POW) or a public holiday (POH), credited as comp-off.

    The old HRMS way (Bharath, 5 Oct 2026): a daily job finds attendance on days that are
    not working days of the employee's shift; the manager (or HR) approves, and a
    "Comp Off" allocation is created and validated, valid for a fixed number of days.
    Comp Off is a leave type that requires an allocation; it is not taken from extra hours.
    """

    _name = 'grotek.extra.attendance'
    _description = 'Extra attendance (comp-off)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', string='Manager', store=True)
    date = fields.Date(required=True, index=True)
    day_type = fields.Selection(
        [('weekly_off', 'Weekly off (POW)'), ('holiday', 'Public holiday (POH)')], required=True)
    hours = fields.Float(string='Hours worked')
    comp_off_days = fields.Float(string='Comp-off days', tracking=True)
    state = fields.Selection(
        [('pending', 'To approve'), ('allocated', 'Comp-off given'), ('rejected', 'Rejected')],
        default='pending', required=True, tracking=True, copy=False)
    allocation_id = fields.Many2one('hr.leave.allocation', string='Comp-off allocation', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved by', readonly=True, copy=False)
    remark = fields.Text()

    _employee_date_unique = models.Constraint(
        'UNIQUE(employee_id, date)', 'An employee has only one extra attendance per day.')

    @api.depends('employee_id', 'date', 'day_type')
    def _compute_name(self):
        labels = dict(self._fields['day_type'].selection)
        for rec in self:
            rec.name = '%s - %s (%s)' % (rec.employee_id.name or '', rec.date or '', labels.get(rec.day_type, ''))

    # --- settings (Settings > Technical > System Parameters, grotek_hr.*) -------------

    @api.model
    def _param(self, key, default):
        value = self.env['ir.config_parameter'].sudo().get_param(PARAM + key)
        try:
            return float(value) if value not in (None, False, '') else default
        except ValueError:
            return default

    @api.model
    def _days_for_hours(self, hours):
        full = self._param('comp_off_full_day_hours', 7.5)
        half = self._param('comp_off_half_day_hours', 0.0)
        if full and hours >= full:
            return 1.0
        if half and hours >= half:
            return 0.5
        return 0.0

    @api.model
    def _comp_off_type(self):
        type_id = int(self._param('comp_off_leave_type_id', 0))
        leave_type = self.env['hr.leave.type'].sudo().browse(type_id).exists() if type_id else None
        if not leave_type:
            leave_type = self.env['hr.leave.type'].sudo().search([('name', '=ilike', 'Comp Off')], limit=1)
        if not leave_type:
            raise UserError(_('There is no "Comp Off" time-off type. Create it (with "Requires allocation") '
                              'or set grotek_hr.comp_off_leave_type_id.'))
        return leave_type

    # --- detection ------------------------------------------------------------------

    @api.model
    def _day_type(self, employee, day):
        """'weekly_off', 'holiday' or False for a working day of the employee's shift."""
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if not calendar:
            return False
        tz = pytz.timezone(employee.tz or calendar.tz or 'UTC')
        start = tz.localize(datetime.combine(day, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        end = tz.localize(datetime.combine(day, time.max)).astimezone(pytz.utc).replace(tzinfo=None)
        holiday = self.env['resource.calendar.leaves'].sudo().search_count([
            ('resource_id', '=', False),
            '|', ('calendar_id', '=', False), ('calendar_id', '=', calendar.id),
            '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ('date_from', '<=', end), ('date_to', '>=', start),
        ])
        if holiday:
            return 'holiday'
        work_days = set(calendar.attendance_ids.filtered(lambda a: not a.display_type).mapped('dayofweek'))
        if str(day.weekday()) not in work_days:
            return 'weekly_off'
        return False

    @api.model
    def _detect(self, date_from, date_to):
        """Create a pending record for each employee and day of attendance on a weekly off or holiday."""
        Attendance = self.env['hr.attendance'].sudo()
        rows = Attendance.search([
            ('check_in', '>=', datetime.combine(date_from - timedelta(days=1), time.min)),
            ('check_in', '<=', datetime.combine(date_to + timedelta(days=1), time.max)),
            ('check_out', '!=', False),
        ])
        hours = {}
        for att in rows:
            emp = att.employee_id
            tz = pytz.timezone(emp.tz or 'UTC')
            day = pytz.utc.localize(att.check_in).astimezone(tz).date()
            if date_from <= day <= date_to:
                hours[(emp.id, day)] = hours.get((emp.id, day), 0.0) + att.worked_hours
        existing = {(r.employee_id.id, r.date) for r in self.sudo().search([
            ('date', '>=', date_from), ('date', '<=', date_to)])}
        created = self.browse()
        for (emp_id, day), worked in sorted(hours.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if (emp_id, day) in existing:
                continue
            employee = self.env['hr.employee'].sudo().browse(emp_id)
            day_type = self._day_type(employee, day)
            if not day_type:
                continue
            rec = self.sudo().create({
                'employee_id': emp_id, 'date': day, 'day_type': day_type,
                'hours': round(worked, 2), 'comp_off_days': self._days_for_hours(worked),
            })
            approver = employee.parent_id.user_id
            if approver and rec.comp_off_days:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=approver.id,
                    summary=_('Comp-off for %(emp)s on %(day)s', emp=employee.name, day=day))
            created |= rec
        return created

    @api.model
    def _cron_detect(self):
        """Daily: look back over the claim window (grotek_hr.comp_off_claim_window_days, default 31)."""
        today = fields.Date.context_today(self)
        window = int(self._param('comp_off_claim_window_days', 31))
        return self._detect(today - timedelta(days=window), today - timedelta(days=1))

    # --- approval -------------------------------------------------------------------

    def _can_approve(self):
        self.ensure_one()
        user = self.env.user
        if self.employee_id.user_id == user and not user.has_group('hr.group_hr_user'):
            return False
        return user.has_group('hr.group_hr_user') or self.employee_id.parent_id.user_id == user

    def action_approve(self):
        valid_days = int(self._param('comp_off_valid_days', 30))
        leave_type = self._comp_off_type()
        for rec in self.filtered(lambda r: r.state == 'pending'):
            if not rec._can_approve():
                raise UserError(_('Only %(emp)s\'s manager or HR can approve this comp-off.', emp=rec.employee_id.name))
            if rec.comp_off_days <= 0:
                raise UserError(_('%(name)s gives no comp-off days (%(h)s hours worked). Reject it, or HR can set the days.',
                                  name=rec.name, h=rec.hours))
            allocation = self.env['hr.leave.allocation'].sudo().create({
                'name': _('Comp-off for %(type)s on %(day)s', type=dict(self._fields['day_type'].selection)[rec.day_type], day=rec.date),
                'holiday_status_id': leave_type.id,
                'employee_id': rec.employee_id.id,
                'allocation_type': 'regular',
                'number_of_days': rec.comp_off_days,
                'date_from': rec.date,
                'date_to': rec.date + timedelta(days=valid_days),
            })
            self._validate_allocation(allocation)
            rec.write({'state': 'allocated', 'allocation_id': allocation.id, 'approved_by_id': self.env.user.id})
            rec.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    @api.model
    def _validate_allocation(self, allocation):
        # Odoo 18/19: action_approve (first level), then action_validate if a second level is set.
        if allocation.state not in ('validate', 'validate1') and hasattr(allocation, 'action_approve'):
            allocation.action_approve()
        if allocation.state != 'validate' and hasattr(allocation, 'action_validate'):
            allocation.action_validate()

    def action_reject(self):
        for rec in self.filtered(lambda r: r.state == 'pending'):
            if not rec._can_approve():
                raise UserError(_('Only %(emp)s\'s manager or HR can reject this comp-off.', emp=rec.employee_id.name))
            rec.state = 'rejected'
            rec.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_reset(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(_('Only HR can reopen a rejected comp-off.'))
        self.filtered(lambda r: r.state == 'rejected').write({'state': 'pending'})
        return True
