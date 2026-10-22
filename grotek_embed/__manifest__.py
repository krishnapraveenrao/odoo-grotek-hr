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
""",
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'author': 'Qltc (Quantum Leap Trainers and Consultants)',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': ['data/grotek_embed_data.xml'],
    'installable': True,
    'application': False,
}
