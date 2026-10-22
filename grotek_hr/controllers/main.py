from odoo import http
from odoo.http import request


class GrotekHrController(http.Controller):

    @http.route('/grotek_hr/web_app_url', type='http', auth='user', methods=['GET'])
    def web_app_url(self):
        """The web app's address for the "Back to web app" button in the top bar (empty = no button).

        Set it in Settings > Technical > System Parameters (grotek_hr.web_app_url) per environment.
        """
        url = request.env['ir.config_parameter'].sudo().get_param('grotek_hr.web_app_url', '')
        return request.make_response(url or '', headers=[('Content-Type', 'text/plain; charset=utf-8')])
