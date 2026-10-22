import re

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

PARAM = 'grotek_embed.frame_ancestors'
# one https origin: scheme, host, optional port; no path, no wildcard
_ORIGIN = re.compile(r'^https://[A-Za-z0-9.-]+(:\d{1,5})?$')


def allowed_frame_ancestors():
    """The 2608 origins that may frame Odoo, from the system parameter; invalid entries are dropped."""
    raw = request.env['ir.config_parameter'].sudo().get_param(PARAM, '') or ''
    return [o for o in raw.split() if _ORIGIN.match(o)]


def allow_framing(response):
    """Replace Odoo's frame headers with frame-ancestors 'self' + the allowed origins. No origins = unchanged."""
    origins = allowed_frame_ancestors()
    if origins:
        response.headers.pop('X-Frame-Options', None)
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self' " + ' '.join(origins)
    return response


class GrotekEmbedHome(Home):

    @http.route()
    def web_login(self, *args, **kw):
        return allow_framing(super().web_login(*args, **kw))

    @http.route()
    def web_client(self, *args, **kw):
        return allow_framing(super().web_client(*args, **kw))
