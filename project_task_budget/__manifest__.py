# -*- coding: utf-8 -*-

{
    'name': 'RCL Project Task Budget',
    'version': '19.0.1.0',
    'category': 'Project',
    'depends': ['base', 'project', 'account_budget', 'project_account_budget', 'project_purchase', 'analytic','purchase','stock','construction_dpr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/project_views.xml',
        'views/project_task_view.xml',
        'reports/purchase_order_templates.xml',
        'views/purchase_order_view.xml',
        'views/rate_analysis_views.xml',

    ],
    'assets': {
            'web.assets_backend': [
                'project_task_budget/static/src/components/**/*',
            ],
        },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}