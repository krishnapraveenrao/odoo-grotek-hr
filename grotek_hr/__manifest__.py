{
    'name': 'Grotek HR (shifts, OD attendance, extra attendance)',
    'summary': "Grotek's own HR records: future-dated shift changes, on-duty attendance requests, "
               'extra attendance (work on a weekly off or holiday) credited as comp-off',
    'description': """
Grotek HR, built for Grotek by Qltc (Quantum Leap Trainers and Consultants).

The Python version of what Qltc had built with Studio in its own Odoo Online
(x_shift, x_od_attendance, x_extra_attendance), for the SAP B1 web app's HR
add-on (qltc-in/qltc-sapb1-web-app, addons/hr, #390):

* Shift change: a new working schedule for an employee from a date (and
  optionally until a date), applied and ended on those dates by a daily job.
* OD attendance: an on-duty request with check-in and check-out times; the
  reporting manager (or HR) approves and the attendance line is created.
* Extra attendance: a daily job finds attendance on a weekly off or a public
  holiday; the manager approves and a "Comp Off" allocation is created.
""",
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'author': 'Qltc (Quantum Leap Trainers and Consultants)',
    'license': 'LGPL-3',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'resource', 'mail'],
    'data': [
        'security/grotek_hr_security.xml',
        'security/ir.model.access.csv',
        'data/grotek_hr_data.xml',
        'views/hr_employee_views.xml',
        'views/shift_change_views.xml',
        'views/od_attendance_views.xml',
        'views/extra_attendance_views.xml',
        'views/grotek_hr_menus.xml',
    ],
    'installable': True,
    'application': False,
}
