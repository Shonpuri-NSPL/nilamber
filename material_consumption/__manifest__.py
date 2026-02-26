# -*- coding: utf-8 -*-
{
    'name': "Material Consumption",
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'description': """
Material Consumption Module
==========================

This module allows users to request materials for projects or customers.

Features:
- Create material requests with multiple products
- Support for project-based and customer-based requests
- Configurable approval levels
- Approval history tracking
- Automatic stock issuance after approval
- Billable and free material support for customers
    """,
    'author': 'Nilamber',
    'company': 'Nilamber',
    'website': 'https://www.nilamber.com',
    'license': 'LGPL-3',
    'icon': '/material_consumption/static/description/icon.png',
    'depends': ['base', 'stock', 'sale', 'project'],
    'data': [
        'data/sequence_data.xml',
        'security/security.xml',
        'data/approval_level_data.xml',
        'security/ir.model.access.csv',
        'views/material_request_views.xml',
        'views/material_request_line_views.xml',
        'views/approval_history_views.xml',
        'views/approval_level_configuration_views.xml',
        'views/menu_views.xml',
        'views/stock_location_view.xml',
        'views/stock_scrap_view.xml',
        # 'wizards/approval_wizard_views.xml',
        'report/material_request_report.xml',

    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
