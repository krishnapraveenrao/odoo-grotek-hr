{
    'name': 'Grotek embed (let the web app show Odoo in a tab)',
    'summary': "Lets the SAP B1 web app (2608) show Odoo screens inside its own tabs by naming it as an allowed frame parent",
    'description': """
Odoo sends X-Frame-Options (DENY on the main screen, SAMEORIGIN on the sign-in page) and
Content-Security-Policy frame-ancestors 'self', so a browser will not show it inside another site.

This module replaces those headers on the two pages with
``Content-Security-Policy: frame-ancestors 'self' <the 2608 hosts>``. The hosts are read from the system
parameter ``grotek_embed.frame_ancestors`` (space-separated origins, https only, no wildcards); empty or
missing = no change (Odoo stays as it is). Nothing else is changed.

Slice 2: a small script, active only when Odoo is framed, tells the 2608 page where Odoo is, whether the sign-in
page is shown and whether a form has unsaved changes (postMessage to the listed origins only).
""",
    'version': '19.0.1.1.0',
    'category': 'Technical',
    'author': 'Qltc (Quantum Leap Trainers and Consultants)',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': ['data/grotek_embed_data.xml'],
    'assets': {
        'web.assets_backend': ['grotek_embed/static/src/embed_bridge.js'],
        'web.assets_frontend': ['grotek_embed/static/src/embed_bridge.js'],
    },
    'installable': True,
    'application': False,
}
