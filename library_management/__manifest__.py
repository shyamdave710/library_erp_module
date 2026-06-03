# -*- coding: utf-8 -*-
{
    'name': 'Library Management System',
    'version': '19.0.1.0.0',
    'category': 'Service/Library',
    'price':'10.0',
    'currency': 'USD',
    'summary': 'Manage books, members, issues and returns',
    'description': """
        Complete Library Management System built on Odoo 18.
        Features:
            - Book catalog with all field types
            - Member registration and management
            - Book issue and return with fine calculation
            - Reservation calendar
            - Role-based security (Admin, Librarian, Member)
            - Qweb PDF reports
    """,
    'author': "Shyam Dave",
    'depends': [
        'base',         # core odoo - always required
        'mail',         # for chatter (messaging on records)
        'contacts',     # for res.partner (members link to contacts)
    ],
    'data':[
        'security/library_security.xml',
        'security/ir.model.access.csv',
        'data/library_data.xml',
        'views/book_views.xml',
        'views/member_views.xml',
        'views/issue_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}