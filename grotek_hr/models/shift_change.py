from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GrotekShiftChange(models.Model):
    """A new working schedule (shift) for an employee from a date, optionally until a date.

    As Qltc's Odoo Online x_shift: HR enters or imports the changes (one per line,
    Excel import from the list), schedules them, and a daily job applies each change
    on its From date and puts the shift before back the day after its To date.
    """

    _name = 'grotek.shift.change'
    _description = 'Shift change'
    _inherit = ['mail.thread']
    _order = 'date_from desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    calendar_id = fields.Many2one('resource.calendar', string='New shift', required=True, tracking=True)
    previous_calendar_id = fields.Many2one(
        'resource.calendar', string='Shift before', readonly=True,
        help='The working schedule the employee had when this change was applied; it comes back after the To date.')
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', tracking=True,
                          help='Leave empty when the new shift stays. When set, the shift before comes back the day after.')
    state = fields.Selection(
        [('draft', 'Draft'), ('scheduled', 'Scheduled'), ('applied', 'Applied'), ('ended', 'Ended'), ('cancelled', 'Cancelled')],
        default='draft', required=True, tracking=True, copy=False)
    remark = fields.Text()
    approved_by_id = fields.Many2one('res.users', string='Scheduled by', readonly=True, copy=False)

    @api.depends('employee_id', 'calendar_id', 'date_from')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s from %s' % (rec.employee_id.name or '', rec.calendar_id.name or '', rec.date_from or '')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_('The To date is before the From date.'))

    @api.constrains('employee_id', 'date_from', 'date_to', 'state')
    def _check_overlap(self):
        for rec in self.filtered(lambda r: r.state in ('scheduled', 'applied')):
            others = self.search([
                ('id', '!=', rec.id), ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ('scheduled', 'applied')),
                ('date_from', '<=', rec.date_to or fields.Date.to_date('9999-12-31')),
                '|', ('date_to', '=', False), ('date_to', '>=', rec.date_from),
            ])
            if others:
                raise ValidationError(_('%(emp)s already has a shift change for these dates: %(other)s',
                                        emp=rec.employee_id.name, other=others[0].name))

    def _check_hr(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(_('Only HR officers can schedule or cancel shift changes.'))

    def action_schedule(self):
        self._check_hr()
        for rec in self.filtered(lambda r: r.state == 'draft'):
            rec.write({'state': 'scheduled', 'approved_by_id': self.env.user.id})
        # A change dated today or earlier takes effect at once.
        self._apply_due(fields.Date.context_today(self))
        return True

    def action_cancel(self):
        self._check_hr()
        for rec in self:
            if rec.state == 'applied':
                rec._end()
            rec.state = 'cancelled'
        return True

    def action_draft(self):
        self._check_hr()
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})
        return True

    def _apply(self):
        for rec in self:
            employee = rec.employee_id.sudo()
            rec.previous_calendar_id = employee.resource_calendar_id
            employee.resource_calendar_id = rec.calendar_id
            rec.state = 'applied'
            rec.message_post(body=_('Applied: %(emp)s now works %(cal)s.', emp=employee.name, cal=rec.calendar_id.name))

    def _end(self):
        for rec in self:
            employee = rec.employee_id.sudo()
            if rec.previous_calendar_id and employee.resource_calendar_id == rec.calendar_id:
                employee.resource_calendar_id = rec.previous_calendar_id
            rec.state = 'ended'
            rec.message_post(body=_('Ended: %(emp)s is back on %(cal)s.', emp=employee.name,
                                    cal=rec.previous_calendar_id.name or employee.resource_calendar_id.name))

    def _apply_due(self, today):
        due = self.search([('state', '=', 'scheduled'), ('date_from', '<=', today)], order='date_from, id')
        due._apply()
        over = self.search([('state', '=', 'applied'), ('date_to', '!=', False), ('date_to', '<', today)], order='date_to, id')
        over._end()
        return len(due), len(over)

    @api.model
    def _cron_apply_due(self):
        """Daily: apply the scheduled changes whose From date has come; end those past their To date."""
        return self._apply_due(fields.Date.context_today(self))
