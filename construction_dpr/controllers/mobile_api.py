# -*- coding: utf-8 -*-

import json
import base64
from odoo import http
from odoo.http import request
from datetime import datetime, date


class MobileApiController(http.Controller):
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

    def _serialize_report(self, report):
        """Serialize DPR report to JSON"""
        return {
            'id': report.id,
            'name': report.name,
            'project_id': report.project_id.id,
            'project_name': report.project_id.name,
            'task_id': report.task_id.id if report.task_id else None,
            'task_name': report.task_id.name if report.task_id else None,
            'report_date': str(report.report_date),
            'prepared_by_id': report.prepared_by_id.id,
            'prepared_by_name': report.prepared_by_id.name,
            'state': report.state,
            'work_summary': report.work_summary or '',
            'delays_description': report.delays_description or '',
            'safety_incidents': report.safety_incidents or '',
            'notes': report.notes or '',
            'is_holiday': report.is_holiday,
            'total_labor_cost': report.total_labor_cost,
            'total_material_cost': report.total_material_cost,
            'total_equipment_cost': report.total_equipment_cost,
            'overall_progress': report.overall_progress,
            'latitude': report.latitude or 0.0,
            'longitude': report.longitude or 0.0,
            'labor_ids': [self._serialize_labor(l) for l in report.labor_ids],
            'material_ids': [self._serialize_material(m) for m in report.material_ids],
            'equipment_ids': [self._serialize_equipment(e) for e in report.equipment_ids],
            'photo_ids': [self._serialize_photo(p) for p in report.photo_ids],
            'weather': self._serialize_weather(report.weather_id) if report.weather_id else None,
        }

    def _serialize_labor(self, labor):
        """Serialize labor entry"""
        return {
            'id': labor.id,
            'employee_id': labor.employee_id.id,
            'employee_name': labor.employee_id.name,
            'work_type': labor.work_type,
            'hours_worked': labor.hours_worked,
            'overtime_hours': labor.overtime_hours,
            'hourly_rate': labor.hourly_rate,
            'wages_amount': labor.wages_amount,
            'work_description': labor.work_description or '',
            'task_id': labor.task_id.id if labor.task_id else None,
            'present': labor.present,
        }

    def _serialize_material(self, material):
        """Serialize material entry"""
        return {
            'id': material.id,
            'material_type': material.material_type,
            'item_name': material.item_name,
            'quantity': material.quantity,
            'unit': material.unit,
            'rate': material.rate,
            'amount': material.amount,
            'source': material.source,
            'task_id': material.task_id.id if material.task_id else None,
            'opening_stock': material.opening_stock,
            'closing_stock': material.closing_stock,
            'received_qty': material.received_qty,
        }

    def _serialize_equipment(self, equipment):
        """Serialize equipment entry"""
        return {
            'id': equipment.id,
            'equipment_type_id': equipment.equipment_type.id if equipment.equipment_type else None,
            'equipment_type_name': equipment.equipment_type.name if equipment.equipment_type else '',
            'equipment_name': equipment.equipment_name,
            'hours_operated': equipment.hours_operated,
            'idle_hours': equipment.idle_hours,
            'breakdown_hours': equipment.breakdown_hours,
            'operator_name': equipment.operator_name or '',
            'fuel_consumed': equipment.fuel_consumed,
            'maintenance_status': equipment.maintenance_status,
            'task_id': equipment.task_id.id if equipment.task_id else None,
            'rental_rate': equipment.rental_rate,
            'rental_amount': equipment.rental_amount,
        }

    def _serialize_photo(self, photo):
        """Serialize photo entry"""
        base_url = request.httprequest.host_url.rstrip('/')
        unique = int(photo.write_date.timestamp()) if photo.write_date else 0

        return {
            'id': photo.id,
            'photo_name': photo.photo_name,
            'photo_type': photo.photo_type,
            'latitude': photo.latitude or 0.0,
            'longitude': photo.longitude or 0.0,
            'captured_time': str(photo.captured_time) if photo.captured_time else None,
            'photo': photo.photo.decode('utf-8') if photo.photo else None,
            'has_image': bool(photo.photo),
        }

    def _serialize_weather(self, weather):
        """Serialize weather entry"""
        return {
            'id': weather.id,
            'weather_condition': weather.weather_condition,
            'temperature': weather.temperature or 0.0,
            'humidity': weather.humidity or 0.0,
            'wind_speed': weather.wind_speed or 0.0,
            'rainfall_mm': weather.rainfall_mm or 0.0,
            'working_hours_lost': weather.working_hours_lost,
            'weather_impact': weather.weather_impact or '',
        }

    def _serialize_equipment_type(self, equipment_type):
        """Serialize equipment type master"""
        return {
            'id': equipment_type.id,
            'name': equipment_type.name,
            'code': equipment_type.code or '',
            'description': equipment_type.description or '',
        }

    # ========== DPR REPORTS ==========

    @http.route('/api/mobile/dpr/reports_list', type='jsonrpc', auth='public', cors='*')
    def get_reports(self, **kwargs):
        """Get DPR reports"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            project_ids = employee.project_ids.ids
            domain = [('project_id', 'in', project_ids)]

            # Filter by state if provided
            state = kwargs.get('state')
            if state:
                domain.append(('state', '=', state))

            # Filter by date range
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            if date_from:
                domain.append(('report_date', '>=', date_from))
            if date_to:
                domain.append(('report_date', '<=', date_to))

            reports = request.env['dpr.report'].sudo().search(domain, order='report_date desc, id desc')

            return {
                'success': True,
                'data': [self._serialize_report(r) for r in reports]
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/dpr/reports/<int:report_id>', type='jsonrpc', auth='public', cors='*')
    def get_report(self, report_id, **kwargs):
        """Get specific DPR report"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            return {
                'success': True,
                'data': self._serialize_report(report)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/dpr/reports', type='jsonrpc', auth='public', cors='*', methods=['POST'])
    def create_report(self, **kwargs):
        """Create new DPR report"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            data = kwargs
            project_id = data.get('project_id')
            report_date = data.get('report_date', str(date.today()))

            if not project_id:
                return {'success': False, 'error_code': 'MISSING_PROJECT', 'message': 'Project ID is required'}

            # Check if report already exists for this date
            existing = request.env['dpr.report'].sudo().search([
                ('project_id', '=', project_id),
                ('report_date', '=', report_date)
            ], limit=1)

            if existing:
                # Update existing report
                report = existing
                report_data = {
                    'work_summary': data.get('work_summary', ''),
                    'delays_description': data.get('delays_description', ''),
                    'safety_incidents': data.get('safety_incidents', ''),
                    'notes': data.get('notes', ''),
                    'is_holiday': data.get('is_holiday', False),
                    'latitude': data.get('latitude', 0.0),
                    'longitude': data.get('longitude', 0.0),
                    'overall_progress': data.get('overall_progress', 0.0),
                }
                report.write(report_data)
            else:
                # Create new report
                report = request.env['dpr.report'].sudo().create({
                    'project_id': project_id,
                    'report_date': report_date,
                    'prepared_by_id': employee.id,
                    'work_summary': data.get('work_summary', ''),
                    'delays_description': data.get('delays_description', ''),
                    'safety_incidents': data.get('safety_incidents', ''),
                    'notes': data.get('notes', ''),
                    'is_holiday': data.get('is_holiday', False),
                    'latitude': data.get('latitude', 0.0),
                    'longitude': data.get('longitude', 0.0),
                    'overall_progress': data.get('overall_progress', 0.0),
                })

            return {
                'success': True,
                'message': 'Report created/updated successfully',
                'data': self._serialize_report(report)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/dpr/reports/<int:report_id>/submit', type='jsonrpc', auth='public', cors='*',
                methods=['POST'])
    def submit_report(self, report_id, **kwargs):
        """Submit DPR report for approval"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            if report.state != 'draft':
                return {'success': False, 'error_code': 'INVALID_STATE',
                        'message': 'Only draft reports can be submitted'}

            report.action_submit()

            return {
                'success': True,
                'message': 'Report submitted for approval',
                'data': self._serialize_report(report)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    # ========== LABOR ==========

    @http.route('/api/mobile/dpr/<int:report_id>/labor', type='jsonrpc', auth='public', cors='*',
                methods=['GET', 'POST'])
    def manage_labor(self, report_id, **kwargs):
        """Get or add labor entries for a report"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            if request.httprequest.method == 'GET':
                return {
                    'success': True,
                    'data': [self._serialize_labor(l) for l in report.labor_ids]
                }
            else:
                # Create labor entry
                data = kwargs
                labor = request.env['dpr.labor'].sudo().create({
                    'report_id': report_id,
                    'employee_id': data.get('employee_id'),
                    'work_type': data.get('work_type', 'skilled'),
                    'hours_worked': data.get('hours_worked', 8.0),
                    'overtime_hours': data.get('overtime_hours', 0.0),
                    'hourly_rate': data.get('hourly_rate', 500.0),
                    'work_description': data.get('work_description', ''),
                    'task_id': data.get('task_id'),
                    'present': data.get('present', True),
                })

                return {
                    'success': True,
                    'message': 'Labor entry added',
                    'data': self._serialize_labor(labor)
                }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    # ========== MATERIALS ==========

    @http.route('/api/mobile/dpr/<int:report_id>/materials', type='jsonrpc', auth='public', cors='*',
                methods=['GET', 'POST'])
    def manage_materials(self, report_id, **kwargs):
        """Get or add material entries for a report"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            if request.httprequest.method == 'GET':
                return {
                    'success': True,
                    'data': [self._serialize_material(m) for m in report.material_ids]
                }
            else:
                data = kwargs
                material = request.env['dpr.material'].sudo().create({
                    'report_id': report_id,
                    'material_type': data.get('material_type'),
                    'item_name': data.get('item_name'),
                    'quantity': data.get('quantity', 1.0),
                    'unit': data.get('unit', 'piece'),
                    'rate': data.get('rate', 0.0),
                    'source': data.get('source', 'site_stock'),
                    'task_id': data.get('task_id'),
                    'opening_stock': data.get('opening_stock', 0.0),
                    'closing_stock': data.get('closing_stock', 0.0),
                    'received_qty': data.get('received_qty', 0.0),
                })

                return {
                    'success': True,
                    'message': 'Material entry added',
                    'data': self._serialize_material(material)
                }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    # ========== EQUIPMENT ==========

    @http.route('/api/mobile/dpr/<int:report_id>/equipment', type='jsonrpc', auth='public', cors='*',
                methods=['GET', 'POST'])
    def manage_equipment(self, report_id, **kwargs):
        """Get or add equipment entries for a report"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            if request.httprequest.method == 'GET':
                return {
                    'success': True,
                    'data': [self._serialize_equipment(e) for e in report.equipment_ids]
                }
            else:
                data = kwargs
                equipment = request.env['dpr.equipment'].sudo().create({
                    'report_id': report_id,
                    'equipment_type': data.get('equipment_type_id'),
                    'equipment_name': data.get('equipment_name'),
                    'hours_operated': data.get('hours_operated', 0.0),
                    'idle_hours': data.get('idle_hours', 0.0),
                    'breakdown_hours': data.get('breakdown_hours', 0.0),
                    'operator_name': data.get('operator_name', ''),
                    'fuel_consumed': data.get('fuel_consumed', 0.0),
                    'maintenance_status': data.get('maintenance_status', 'good'),
                    'task_id': data.get('task_id'),
                    'rental_rate': data.get('rental_rate', 0.0),
                })

                return {
                    'success': True,
                    'message': 'Equipment entry added',
                    'data': self._serialize_equipment(equipment)
                }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/equipment/types', type='jsonrpc', auth='public', cors='*', methods=['POST'])
    def get_equipment_types(self, **kwargs):
        """Get equipment type master data"""
        try:
            # Authentication is optional for this endpoint - can be used without login
            equipment_types = request.env['dpr.equipment.type'].sudo().search([('active', '=', True)])
            equipment = [self._serialize_equipment_type(et) for et in equipment_types]

            return {
                'success': True,
                'data': equipment
            }
        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    # ========== PHOTOS ==========

    @http.route('/api/mobile/dpr/<int:report_id>/photos/add',
                type='jsonrpc', auth='public', cors='*', methods=['POST'])
    def add_photo(self, report_id, **kwargs):
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            photo_data = {
                'report_id': report_id,
                'photo_name': kwargs.get('photo_name'),
                'photo_type': kwargs.get('photo_type', 'progress'),
                'latitude': kwargs.get('latitude', 0.0),
                'longitude': kwargs.get('longitude', 0.0),
                'captured_by_id': employee.id,
                'photo': kwargs.get('photo'),
            }

            photo = request.env['dpr.photo'].sudo().create(photo_data)

            return {
                'success': True,
                'message': 'Photo added',
                'data': self._serialize_photo(photo)
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/dpr/<int:report_id>/photos',
                type='jsonrpc', auth='public', cors='*', methods=['POST'])
    def get_photos(self, report_id, **kwargs):
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}
            photo_data = [self._serialize_photo(p) for p in report.photo_ids]

            return {
                'success': True,
                'data': photo_data
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    @http.route('/api/mobile/dpr/<int:report_id>/photos/<int:photo_id>/delete',
                type='jsonrpc', auth='public', cors='*', methods=['POST'])
    def delete_photo(self, report_id, photo_id, **kwargs):
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {
                    'success': False,
                    'error_code': 'UNAUTHORIZED',
                    'message': 'Invalid or expired token'
                }

            # Find the photo
            photo = request.env['dpr.photo'].sudo().browse(photo_id)
            if not photo.exists():
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': 'Photo not found'
                }

            # Verify photo belongs to the report
            if photo.report_id.id != report_id:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': 'Photo does not belong to this report'
                }

            # Delete the photo
            photo.unlink()

            return {
                'success': True,
                'message': 'Photo deleted successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': str(e)
            }

    # ========== WEATHER ==========

    @http.route('/api/mobile/dpr/<int:report_id>/weather', type='jsonrpc', auth='public', cors='*',
                methods=['GET', 'POST'])
    def manage_weather(self, report_id, **kwargs):
        """Get or add weather entry for a report"""
        try:
            employee = self._get_authenticated_employee()
            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            report = request.env['dpr.report'].sudo().browse(report_id)
            if not report.exists():
                return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'Report not found'}

            if request.httprequest.method == 'GET':
                if report.weather_id:
                    return {
                        'success': True,
                        'data': self._serialize_weather(report.weather_id)
                    }
                else:
                    return {'success': False, 'error_code': 'NOT_FOUND', 'message': 'No weather data recorded'}
            else:
                data = kwargs
                weather = request.env['dpr.weather'].sudo().create({
                    'report_id': report_id,
                    'weather_condition': data.get('weather_condition', 'sunny'),
                    'temperature': data.get('temperature', 0.0),
                    'humidity': data.get('humidity', 0.0),
                    'wind_speed': data.get('wind_speed', 0.0),
                    'rainfall_mm': data.get('rainfall_mm', 0.0),
                    'working_hours_lost': data.get('working_hours_lost', 0.0),
                    'weather_impact': data.get('weather_impact', ''),
                })

                return {
                    'success': True,
                    'message': 'Weather data recorded',
                    'data': self._serialize_weather(weather)
                }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}

    # ========== Equipment Type Master ==========


    # ========== DASHBOARD ==========

    @http.route('/api/mobile/dashboard/summary', type='jsonrpc', auth='public', cors='*', methods=['POST'])
    def get_dashboard_summary(self, **kwargs):
        """Get dashboard summary data"""
        try:
            employee = self._get_authenticated_employee()
            odoo_bot = request.env['res.users'].sudo().search([
                ('name', '=', 'OdooBot')
            ], limit=1)
            request.update_env(user=odoo_bot.id)

            if not employee:
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}

            project_ids = employee.project_ids.ids

            # Get metrics
            reports = request.env['dpr.report'].sudo().search([
                ('project_id', 'in', project_ids)
            ])

            dashboard_model = request.env['dpr.dashboard'].sudo()
            daily_progress = dashboard_model.get_daily_progress_data(7)

            today = date.today()

            total_projects = len(employee.project_ids.filtered(lambda p: p.state == 'active'))
            pending_approvals = len(reports.filtered(lambda r: r.state == 'submitted'))
            draft_reports = len(reports.filtered(lambda r: r.state == 'draft'))
            total_dprs_this_month = request.env['dpr.report'].sudo().search_count([
                ('project_id', 'in', project_ids),
                ('report_date', '>=', today.replace(day=1)),
                ('report_date', '<=', today)
            ])


            return {
                'success': True,
                'data': {
                    'total_projects': total_projects,
                    'pending_approvals': pending_approvals,
                    'draft_reports': draft_reports,
                    'total_dprs_this_month': total_dprs_this_month,
                    'daily_progress': daily_progress,
                }
            }

        except Exception as e:
            return {'success': False, 'error_code': 'INTERNAL_ERROR', 'message': str(e)}
