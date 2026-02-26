# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class PurchaseRequisitionMobileAPI(http.Controller):

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

    def _get_employee_from_user(self):
        """Get employee record from current user"""
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        return employee

    @http.route('/api/mobile/purchase_requisitions', type='jsonrpc', auth='public',cors='*', methods=['POST'], csrf=False)
    def get_purchase_requisitions(self, **kwargs):
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {
                    'success': False,
                    'error_code': 'UNAUTHORIZED',
                    'message': 'Invalid or expired token'
                }

            state = kwargs.get('state')
            if state == "approve":
                state = 'po_confirm'

            # Log for debugging
            _logger.info(f"📋 Request - State: {state}, Project: {state}")
            if not state:
                return {'success': False, 'error_code': 'MISSING_STATE', 'message': 'Project State is required'}


            domain = [('employee_id', '=', employee.hr_employee_id.id,)]
            if state and state != 'all':
                domain.append(('state', '=', state))

            requisitions = request.env['material.purchase.requisition'].sudo().search(
                domain,
                order='request_date desc, id desc'
            )

            data = []
            for req in requisitions:
                data.append({
                    'id': req.id,
                    'name': req.name,
                    'employee_id': [req.employee_id.id, req.employee_id.name] if req.employee_id else False,
                    'department_id': [req.department_id.id, req.department_id.name] if req.department_id else False,
                    'project_id': [req.project_id.id, req.project_id.name] if req.project_id else False,
                    'request_date': req.request_date.strftime('%Y-%m-%d') if req.request_date else False,
                    'receive_date': req.receive_date.strftime('%Y-%m-%d') if req.receive_date else False,
                    'requisition_type': req.requisition_type,
                    'state': req.state,
                    'reason': req.reason,
                    'reject_reason': req.reject_reason,
                    'line_count': len(req.requisition_line_ids.ids),
                })

            return {
                'success': True,
                'data': data,
                'count': len(data)
            }

        except Exception as e:
            _logger.error("Error fetching purchase requisitions", exc_info=True)
            return {
                'success': False,
                'error_code': 'SERVER_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/purchase_requisitions/<int:requisition_id>', type='jsonrpc', auth='public',cors='*', methods=['POST'],
                csrf=False)
    def get_purchase_requisition_detail(self, requisition_id, **kwargs):
        """Get detailed information about a specific purchase requisition"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {
                    'success': False,
                    'error_code': 'UNAUTHORIZED',
                    'message': 'Invalid or expired token'
                }

            requisition = request.env['material.purchase.requisition'].sudo().browse(requisition_id)

            if not requisition.exists():
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': 'Requisition not found'
                }

            # Get requisition lines
            lines = []
            for line in requisition.requisition_line_ids:
                lines.append({
                    'id': line.id,
                    'product_id': [line.product_id.id, line.product_id.name] if line.product_id else False,
                    'description': line.description,
                    'qty': line.qty,
                    'uom': [line.uom.id, line.uom.name] if line.uom else False,
                })

            # Get state history
            history = []
            for hist in requisition.state_history_ids:
                history.append({
                    'id': hist.id,
                    'from_state': hist.from_state,
                    'to_state': hist.to_state,
                    'state_label': hist.state_label,
                    'user_id': [hist.user_id.id, hist.user_id.name] if hist.user_id else False,
                    'date': hist.date.strftime('%Y-%m-%d %H:%M:%S') if hist.date else False,
                    'notes': hist.notes,
                })

            data = {
                'id': requisition.id,
                'name': requisition.name,
                'employee_id': [requisition.employee_id.id,
                                requisition.employee_id.name] if requisition.employee_id else False,
                'department_id': [requisition.department_id.id,
                                  requisition.department_id.name] if requisition.department_id else False,
                'project_id': [requisition.project_id.id,
                               requisition.project_id.name] if requisition.project_id else False,
                'request_date': requisition.request_date.strftime('%Y-%m-%d') if requisition.request_date else False,
                'receive_date': requisition.receive_date.strftime('%Y-%m-%d') if requisition.receive_date else False,
                'requisition_type': requisition.requisition_type,
                'state': requisition.state,
                'reason': requisition.reason,
                'reject_reason': requisition.reject_reason,
                'requisition_line_ids': lines,
                'state_history_ids': history,
            }

            return {
                'success': True,
                'data': data
            }

        except Exception as e:
            _logger.error(f"Error fetching requisition detail: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error_code': 'SERVER_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/purchase_requisitions/create', type='jsonrpc', auth='public',cors='*', methods=['POST'], csrf=False)
    def create_purchase_requisition(self, **kwargs):
        try:
            auth_error = self._get_authenticated_employee()
            if auth_error:
                return auth_error

            params = request.jsonrequest.get('params', {})

            # Validate required fields
            if not params.get('employee_id'):
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'Employee ID is required'
                }

            if not params.get('project_id'):
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'Project ID is required'
                }

            if not params.get('requisition_line_ids'):
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'At least one line item is required'
                }

            # Get employee and set department
            employee = request.env['hr.employee'].sudo().browse(params['employee_id'])
            if not employee.exists():
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'Invalid employee'
                }

            # Prepare requisition data
            vals = {
                'employee_id': params['employee_id'],
                'department_id': employee.department_id.id if employee.department_id else False,
                'project_id': params['project_id'],
                'request_date': params.get('request_date'),
                'receive_date': params.get('receive_date'),
                'reason': params.get('reason'),
                'requisition_type': params.get('requisition_type', 'purchase'),
                'state': 'draft',
                'requisition_line_ids': params['requisition_line_ids'],
            }

            # Create requisition
            requisition = request.env['material.purchase.requisition'].sudo().create(vals)

            return {
                'success': True,
                'data': {
                    'id': requisition.id,
                    'name': requisition.name,
                    'state': requisition.state,
                },
                'message': 'Requisition created successfully'
            }

        except Exception as e:
            _logger.error(f"Error creating purchase requisition: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error_code': 'SERVER_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/purchase_requisitions/<int:requisition_id>/submit', type='jsonrpc', auth='public',cors='*',
                methods=['POST'], csrf=False)
    def submit_purchase_requisition(self, requisition_id, **kwargs):
        """Submit a purchase requisition for approval"""
        try:
            auth_error = self._get_authenticated_employee()
            if auth_error:
                return auth_error

            requisition = request.env['material.purchase.requisition'].sudo().browse(requisition_id)

            if not requisition.exists():
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': 'Requisition not found'
                }

            if requisition.state != 'draft':
                return {
                    'success': False,
                    'error_code': 'INVALID_STATE',
                    'message': f'Cannot submit requisition in {requisition.state} state'
                }

            # Submit requisition (move to next state)
            requisition.requisition_confirm()

            return {
                'success': True,
                'data': {
                    'id': requisition.id,
                    'name': requisition.name,
                    'state': requisition.state,
                },
                'message': 'Requisition submitted successfully'
            }

        except Exception as e:
            _logger.error(f"Error submitting requisition: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error_code': 'SERVER_ERROR',
                'message': str(e)
            }

    @http.route('/api/mobile/purchase_requisitions/products', type='jsonrpc', auth='public',cors='*', methods=['POST'], csrf=False)
    def get_products(self, **kwargs):
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {
                    'success': False,
                    'error_code': 'UNAUTHORIZED',
                    'message': 'Invalid or expired token'
                }

            # params = request.jsonrequest.get('params', {})
            # search = params.get('search', '')

            domain = [('purchase_ok', '=', True)]

            # if search:
            #     domain.append('|')
            #     domain.append(('name', 'ilike', search))
            #     domain.append(('default_code', 'ilike', search))

            products = request.env['product.product'].sudo().search(domain, limit=100)

            data = []
            for product in products:
                data.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code,
                    'uom_id': [product.uom_id.id, product.uom_id.name] if product.uom_id else False,
                })

            return {
                'success': True,
                'data': data,
                'count': len(data)
            }

        except Exception as e:
            _logger.error(f"Error fetching products: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error_code': 'SERVER_ERROR',
                'message': str(e)
            }
