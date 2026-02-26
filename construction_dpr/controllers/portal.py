# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class DprPortalController(http.Controller):
    """Portal controller for external access"""

    @http.route('/my/dpr', type='http', auth='user', website=True)
    def my_dpr(self, **kwargs):
        """My DPR dashboard page"""
        employee = request.env['dpr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not employee:
            return request.redirect('/')

        projects = employee.project_ids.filtered(lambda p: p.active)

        return request.render('construction_dpr.portal_my_dpr', {
            'employee': employee,
            'projects': projects,
        })

    @http.route('/my/dpr/reports', type='http', auth='user', website=True)
    def my_dpr_reports(self, **kwargs):
        """My DPR reports page"""
        employee = request.env['dpr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not employee:
            return request.redirect('/')

        project_ids = employee.project_ids.ids
        domain = [('project_id', 'in', project_ids)]

        state = kwargs.get('state')
        if state:
            domain.append(('state', '=', state))

        reports = request.env['dpr.report'].sudo().search(domain, order='report_date desc')

        return request.render('construction_dpr.portal_my_dpr_reports', {
            'employee': employee,
            'reports': reports,
            'state': state,
        })
