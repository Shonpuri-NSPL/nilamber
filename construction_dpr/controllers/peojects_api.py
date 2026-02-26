# -*- coding: utf-8 -*-

import json
import base64
from odoo import http
from odoo.http import request
from datetime import datetime, date


class MobileApiControllerProjects(http.Controller):
    """REST API Controller for Mobile App"""

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

    def _serialize_project(self, project):
        """Serialize project to JSON"""
        return {
            'id': project.id,
            'name': project.name,
            'code': project.code,
            'description': project.description or '',
            'location': project.location or '',
            'start_date': str(project.start_date) if project.start_date else None,
            'end_date': str(project.end_date) if project.end_date else None,
            'state': project.state,
            'project_type': project.project_type,
            'overall_progress': project.overall_progress,
            'latitude': project.latitude or 0.0,
            'longitude': project.longitude or 0.0,
        }

    # ========== PROJECTS ==========

    @http.route('/api/mobile/projects', type='jsonrpc', auth='public',cors='*')
    def get_projects(self, **kwargs):
        """Get all projects for authenticated employee"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            projects = employee.project_ids.filtered(lambda p: p.active and p.state == 'active')

            return {
                'success': True,
                'data': [self._serialize_project(p) for p in projects]
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/projects/<int:project_id>', type='jsonrpc', auth='public',cors='*')
    def get_project(self, project_id, **kwargs):
        """Get specific project details"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            project = request.env['dpr.project'].sudo().browse(project_id)
            if not project.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Project not found'}

            return {
                'success': True,
                'data': self._serialize_project(project)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

