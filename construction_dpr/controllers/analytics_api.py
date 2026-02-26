# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AnalyticAPI(http.Controller):

    def _get_authenticated_employee(self):
        """Get authenticated employee from token"""
        token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
        employee = request.env['dpr.employee'].sudo().search([
            ('auth_token', '=', token),
            ('active', '=', True)
        ], limit=1)

        if not employee or not employee.is_token_valid():
            return None
        return employee

    @http.route('/api/mobile/analytics', type='jsonrpc', auth='public', cors='*')
    def get_analytics(self, period='month'):
        employee = self._get_authenticated_employee()
        if not employee:
            return {'success': False, 'error_code': 'UNAUTHORIZED'}

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'quarter':
            start_date = end_date - timedelta(days=90)
        else:  # year
            start_date = end_date - timedelta(days=365)

        # Fetch analytics data
        dprs = request.env['dpr.report'].sudo().search([
            # ('employee_id', '=', employee.hr_employee_id.id),
            ('report_date', '>=', start_date),
            ('report_date', '<=', end_date)
        ])

        # Calculate metrics
        data = {
            'total_dprs': len(dprs),
            'dpr_draft': len(dprs.filtered(lambda d: d.state == 'draft')),
            'dpr_submitted': len(dprs.filtered(lambda d: d.state == 'submitted')),
            'dpr_approved': len(dprs.filtered(lambda d: d.state == 'approved')),
            # ... more calculations
        }

        return {'success': True, 'data': data}