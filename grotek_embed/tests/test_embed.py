from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestEmbed(HttpCase):

    def _set(self, value):
        self.env['ir.config_parameter'].sudo().set_param('grotek_embed.frame_ancestors', value)

    def test_login_default_unchanged(self):
        self._set('')
        r = self.url_open('/web/login')
        self.assertEqual(r.headers.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(r.headers.get('Content-Security-Policy'), "frame-ancestors 'self'")

    def test_login_allows_listed_origin(self):
        self._set('https://app.example.in https://x.example.in:8443')
        r = self.url_open('/web/login')
        self.assertIsNone(r.headers.get('X-Frame-Options'))
        self.assertEqual(
            r.headers.get('Content-Security-Policy'),
            "frame-ancestors 'self' https://app.example.in https://x.example.in:8443")

    def test_bad_entries_dropped(self):
        self._set('* http://plain.example.in https://ok.example.in/path https://ok.example.in')
        r = self.url_open('/web/login')
        self.assertEqual(r.headers.get('Content-Security-Policy'), "frame-ancestors 'self' https://ok.example.in")

    def test_main_screen_not_denied(self):
        self._set('https://app.example.in')
        self.authenticate('admin', 'admin')
        r = self.url_open('/odoo')
        self.assertIsNone(r.headers.get('X-Frame-Options'))
        self.assertIn('https://app.example.in', r.headers.get('Content-Security-Policy', ''))
