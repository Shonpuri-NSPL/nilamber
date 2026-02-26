# -*- coding: utf-8 -*-
{
    'name': 'Construction DPR - Daily Progress Report',
    'version': '19.0.1.0.0',
    'category': 'Construction/Project Management',
    'description': """
Construction DPR Module for Daily Progress Reports
==================================================

A comprehensive Daily Progress Report module for construction industry with:
- Project and Task Management
- Daily Progress Reporting
- Labor Attendance Tracking
- Material Consumption Tracking
- Equipment Usage Monitoring
- Weather Condition Recording
- Photo Documentation
- Mobile App Integration with REST API
- PIN-based Employee Authentication
- Modern Dashboard with Interactive Charts
- Approval Workflow
- Comprehensive Reports
    """,
    'author': 'Nilamber',
    'company': 'Nilamber',
    'website': 'https://www.nilamber.com',
    'depends': [
        'base',
        'mail',
        'hr',
        'project',
    ],
    'data': [
        'security/dpr_security.xml',
        'security/ir.model.access.csv',
        'views/dpr_project_views.xml',
        'views/dpr_task_views.xml',
        'views/dpr_task_type_views.xml',
        'views/dpr_equipment_type_views.xml',

        'views/dpr_labor_views.xml',
        'views/dpr_material_views.xml',
        # 'views/dpr_equipment_views.xml',
        'views/dpr_weather_views.xml',
        'views/dpr_photo_views.xml',
        'views/dpr_employee_views.xml',
        # 'views/dpr_dashboard_views.xml',
        # 'views/dpr_dashboard_templates.xml',
        'wizard/dpr_approval_wizard_views.xml',
        'wizard/dpr_report_wizard_views.xml',
        'reports/dpr_report_templates.xml',
        'views/dpr_action_views.xml',
        'data/sequence.xml',
        'data/dpr_config_data.xml',
        'views/dpr_report_views.xml',
        'data/activity_templates_data.xml',
        'views/dpr_task_hierarchy_views.xml',
        'wizard/create_units_wizard_views.xml',
        'wizard/project_setup_wizard_views.xml',
        'views/dpr_menu.xml',
    ],
    'demo': [
        'data/dpr_demo_data.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'application': True,
    'auto_install': False,
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'construction_dpr/static/src/css/dpr_task_kanban.css',
        ],
    },
}
