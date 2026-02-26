# -*- coding: utf-8 -*-

import json
import base64
from odoo import http
from odoo.http import request
from datetime import datetime, date


class MobileApiControllerTask(http.Controller):
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

    def _serialize_task(self, task):
        """Serialize task to JSON"""
        return {
            'id': task.id,
            'name': task.name,
            'task_code': task.task_code,
            'description': task.description or '',
            'project_id': task.project_id.id,
            'project_name': task.project_id.name,
            'assigned_to_id': task.assigned_to_id.id if task.assigned_to_id else None,
            'assigned_to_name': task.assigned_to_id.name if task.assigned_to_id else None,
            'state': task.state,
            'priority': task.priority,
            'task_type': task.task_type,
            'progress_percentage': task.progress_percentage,
            'planned_start_date': str(task.planned_start_date) if task.planned_start_date else None,
            'planned_end_date': str(task.planned_end_date) if task.planned_end_date else None,
        }

    # ========== TASKS ==========

    @http.route('/api/mobile/projects/<int:project_id>/tasks', type='jsonrpc', auth='public',cors='*')
    def get_project_tasks(self, project_id, **kwargs):
        """Get tasks for a project based on employee access control"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}
            project = request.env['dpr.project'].sudo().browse(project_id)
            if not project.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Project not found'}
            
            # Get accessible tasks and filter by project
            accessible_tasks = employee.get_accessible_tasks()
            tasks = accessible_tasks.filtered(
                lambda t: t.project_id.id == project_id and t.active
            )
            return {
                'success': True,
                'data': [self._serialize_task(t) for t in tasks]
            }
        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/tasks', type='jsonrpc', auth='user',cors='*')
    def get_tasks(self, **kwargs):
        """Get all tasks for employee based on access control"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            # Get accessible tasks based on access control
            accessible_tasks = employee.get_accessible_tasks()
            
            # Filter for active tasks only
            tasks = accessible_tasks.filtered(lambda t: t.active)

            return {
                'success': True,
                'data': [self._serialize_task(t) for t in tasks]
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/tasks/<int:task_id>', type='jsonrpc', auth='user',cors='*')
    def get_task(self, task_id, **kwargs):
        """Get specific task details based on employee access control"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            task = request.env['dpr.task'].sudo().browse(task_id)
            if not task.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Task not found'}

            # Check if employee has access to this task
            accessible_tasks = employee.get_accessible_tasks()
            if task not in accessible_tasks:
                return {'success': False, 'error_code': 'FORBIDDEN', 'message': 'You do not have access to this task'}

            return {
                'success': True,
                'data': self._serialize_task(task)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/tasks/<int:task_id>/progress', type='jsonrpc', auth='user',cors='*')
    def update_task_progress(self, task_id, **kwargs):
        """Update task progress based on employee access control"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            progress = kwargs.get('progress', 0)
            task = request.env['dpr.task'].sudo().browse(task_id)
            if not task.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Task not found'}

            # Check if employee has access to this task
            accessible_tasks = employee.get_accessible_tasks()
            if task not in accessible_tasks:
                return {'success': False, 'error_code': 'FORBIDDEN', 'message': 'You do not have access to this task'}

            task.write({'progress_percentage': progress})

            return {
                'success': True,
                'message': 'Task progress updated successfully',
                'data': self._serialize_task(task)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}