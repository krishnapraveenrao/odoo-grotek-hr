from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # The attendance device number. Grotek does not use Odoo's Badge ID (barcode).
    # Same name everywhere: "Biometric ID" (the SAP B1 web app reads x_biometric_id,
    # clients/grotek/config/hr/employee.json). Never reused, even after an employee leaves.
    x_biometric_id = fields.Char(string='Biometric ID', groups='hr.group_hr_user', copy=False, index=True, tracking=True)

    @api.constrains('x_biometric_id')
    def _check_biometric_id_never_reused(self):
        for emp in self.filtered('x_biometric_id'):
            value = emp.x_biometric_id.strip()
            other = self.sudo().with_context(active_test=False).search([
                ('id', '!=', emp.id), ('x_biometric_id', '=', value)], limit=1)
            if other:
                raise ValidationError(_('Biometric ID %(bio)s is already on %(other)s%(archived)s; '
                                        'a Biometric ID is never reused.',
                                        bio=value, other=other.name,
                                        archived='' if other.active else _(' (archived)')))
