# -*- coding: utf-8 -*-

import json
from odoo import http
from odoo.http import request
from datetime import datetime


class MobileAuthController(http.Controller):

    @http.route('/api/mobile/auth/login', type='jsonrpc', auth='public',cors='*', methods=['POST'])
    def mobile_login(self, phone=None, pin=None, **kwargs):
        """Mobile authentication endpoint - login with phone and PIN"""
        try:
            phone = (phone or '').strip()
            pin = (pin or '').strip()

            if not phone or not pin:
                return {
                    'success': False,
                    'error_code': 'INVALID_CREDENTIALS',
                    'message': 'Phone number and PIN are required'
                }

            # Search for employee with phone
            employee = request.env['dpr.employee'].sudo().search([
                ('phone', '=', phone),
                ('active', '=', True)
            ], limit=1)

            if not employee:
                return {
                    'success': False,
                    'error_code': 'USER_NOT_FOUND',
                    'message': 'Employee not found with this phone number'
                }

            # Check if mobile login is enabled
            if not employee.mobile_login_enabled:
                return {
                    'success': False,
                    'error_code': 'LOGIN_DISABLED',
                    'message': 'Mobile login is disabled for this employee. Please contact administrator.'
                }

            # Verify PIN
            if not employee.verify_pin(pin):
                return {
                    'success': False,
                    'error_code': 'INVALID_PIN',
                    'message': 'Invalid PIN. Please try again.'
                }

            # Generate auth token
            token = employee.generate_auth_token()

            # Get assigned projects
            projects = employee.project_ids.filtered(lambda p: p.active)

            return {
                'success': True,
                'data': {
                    'token': token,
                    'employee': {
                        'id': employee.id,
                        'name': employee.name,
                        'code': employee.employee_code,
                        'designation': employee.designation or '',
                        'department': employee.department or '',
                        'phone': employee.phone,
                        'email': employee.email or '',
                        'photo': employee.photo or False,
                        'company': employee.company_id.name or '',
                        'currency': employee.company_id.currency_id.symbol or '',
                    },
                    'projects': [{
                        'id': p.id,
                        'name': p.name,
                        'code': p.code,
                        'location': p.location or '',
                        'latitude': p.latitude or 0.0,
                        'longitude': p.longitude or 0.0,
                    } for p in projects]
                },
                'message': 'Login successful'
            }

        except Exception as e:
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/auth/logout', type='jsonrpc', auth='public',cors='*')
    def mobile_logout(self, **kwargs):
        """Logout and invalidate auth token"""
        try:
            employee_id = kwargs.get('employee_id')
            if not employee_id:
                return {
                    'success': False,
                    'error_code': 'MISSING_EMPLOYEE',
                    'message': 'Employee ID is required'
                }

            employee = request.env['dpr.employee'].sudo().browse(employee_id)
            if employee.exists():
                employee.invalidate_token()

            return {
                'success': True,
                'message': 'Logged out successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/auth/profile', type='jsonrpc', auth='public',cors='*')
    def get_profile(self, **kwargs):
        """Get employee profile"""
        try:
            token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
            employee = request.env['dpr.employee'].sudo().search([
                ('auth_token', '=', token),
                ('active', '=', True)
            ], limit=1)

            if not employee:
                return {
                    'success': False,
                    'error_code': 'INVALID_TOKEN',
                    'message': 'Invalid or expired authentication token'
                }

            if not employee.is_token_valid():
                return {
                    'success': False,
                    'error_code': 'TOKEN_EXPIRED',
                    'message': 'Authentication token has expired. Please login again.'
                }

            projects = employee.project_ids.filtered(lambda p: p.active)

            return {
                'success': True,
                'data': {
                    'employee': {
                        'id': employee.id,
                        'name': employee.name,
                        'code': employee.employee_code,
                        'designation': employee.designation or '',
                        'department': employee.department or '',
                        'phone': employee.phone,
                        'email': employee.email or '',
                        'mobile_login_enabled': employee.mobile_login_enabled,
                        'last_login': employee.last_login.strftime('%Y-%m-%d %H:%M:%S') if employee.last_login else None,
                        'login_count': employee.login_count,
                        'photo': employee.photo or False,
                    },
                    'projects': [{
                        'id': p.id,
                        'name': p.name,
                        'code': p.code,
                        'location': p.location or '',
                        'latitude': p.latitude or 0.0,
                        'longitude': p.longitude or 0.0,
                    } for p in projects]
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/auth/verify-pin', type='jsonrpc', auth='public',cors='*', methods=['POST'])
    def verify_pin(self, **kwargs):
        """Verify PIN without generating token"""
        try:
            token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
            pin = kwargs.get('pin', '').strip()

            if not pin:
                return {
                    'success': False,
                    'error_code': 'MISSING_PIN',
                    'message': 'PIN is required'
                }

            employee = request.env['dpr.employee'].sudo().search([
                ('auth_token', '=', token),
                ('active', '=', True)
            ], limit=1)

            if not employee:
                return {
                    'success': False,
                    'error_code': 'INVALID_TOKEN',
                    'message': 'Invalid or expired authentication token'
                }

            if employee.verify_pin(pin):
                return {
                    'success': True,
                    'message': 'PIN verified successfully'
                }
            else:
                return {
                    'success': False,
                    'error_code': 'INVALID_PIN',
                    'message': 'Invalid PIN'
                }

        except Exception as e:
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/auth/refresh-token', type='jsonrpc', auth='public',cors='*', methods=['POST'])
    def refresh_token(self, **kwargs):
        """Refresh authentication token"""
        try:
            token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')

            employee = request.env['dpr.employee'].sudo().search([
                ('auth_token', '=', token),
                ('active', '=', True)
            ], limit=1)

            if not employee:
                return {
                    'success': False,
                    'error_code': 'INVALID_TOKEN',
                    'message': 'Invalid or expired authentication token'
                }

            # Generate new token
            new_token = employee.generate_auth_token()

            return {
                'success': True,
                'data': {
                    'token': new_token
                },
                'message': 'Token refreshed successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': str(e)
            }
