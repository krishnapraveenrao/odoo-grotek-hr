from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GrotekOdAttendance(models.Model):
    """On-duty (OD) attendance: the employee was working away from the biometric device.

    As Qltc's Odoo Online x_od_attendance: the employee (or HR for them) asks with
    check-in and check-out times and a reason; the reporting manager (the employee's
    Manager in Odoo) or an HR officer approves, and the attendance line is created.
    """

    _name = 'grotek.od.attendance'
    _description = 'OD attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_in desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, index=True, tracking=True,
        default=lambda self: self.env.user.employee_id)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', string='Manager', store=True)
    check_in = fields.Datetime(required=True, tracking=True)
    check_out = fields.Datetime(required=True, tracking=True)
    worked_hours = fields.Float(compute='_compute_worked_hours', store=True)
    reason = fields.Text(required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'To approve'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft', required=True, tracking=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved by', readonly=True, copy=False)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance', readonly=True, copy=False)
    reject_reason = fields.Char(tracking=True, copy=False)

    @api.depends('employee_id', 'check_in')
    def _compute_name(self):
        for rec in self:
            day = fields.Datetime.context_timestamp(rec, rec.check_in).date() if rec.check_in else ''
            rec.name = _('OD %(emp)s %(day)s', emp=rec.employee_id.name or '', day=day)

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                rec.worked_hours = (rec.check_out - rec.check_in).total_seconds() / 3600.0
            else:
                rec.worked_hours = 0.0

    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for rec in self:
            if rec.check_out <= rec.check_in:
                raise ValidationError(_('Check-out must be after check-in.'))

    def _can_approve(self):
        self.ensure_one()
        user = self.env.user
        return user.has_group('hr.group_hr_user') or (self.employee_id.parent_id.user_id == user)

    def _approver_user(self):
        self.ensure_one()
        return self.employee_id.parent_id.user_id

    def action_submit(self):
        for rec in self.filtered(lambda r: r.state == 'draft'):
            rec.state = 'submitted'
            approver = rec._approver_user()
            if approver:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=approver.id,
                    summary=_('Approve OD attendance of %s', rec.employee_id.name))
        return True

    def action_approve(self):
        for rec in self.filtered(lambda r: r.state in ('draft', 'submitted')):
            if not rec._can_approve():
                raise UserError(_('Only %(emp)s\'s manager or HR can approve this OD.', emp=rec.employee_id.name))
            if rec.employee_id.user_id == self.env.user and not self.env.user.has_group('hr.group_hr_user'):
                raise UserError(_('You cannot approve your own OD.'))
            attendance = self.env['hr.attendance'].sudo().create({
                'employee_id': rec.employee_id.id,
                'check_in': rec.check_in,
                'check_out': rec.check_out,
            })
            rec.write({'state': 'approved', 'approved_by_id': self.env.user.id, 'attendance_id': attendance.id})
            rec.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_reject(self):
        for rec in self.filtered(lambda r: r.state in ('draft', 'submitted')):
            if not rec._can_approve():
                raise UserError(_('Only %(emp)s\'s manager or HR can reject this OD.', emp=rec.employee_id.name))
            rec.state = 'rejected'
            rec.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_draft(self):
        self.filtered(lambda r: r.state == 'rejected').write({'state': 'draft', 'reject_reason': False})
        return True

    def unlink(self):
        if self.filtered(lambda r: r.state == 'approved'):
            raise UserError(_('An approved OD cannot be deleted; delete its attendance line instead and reject it.'))
        return super().unlink()
