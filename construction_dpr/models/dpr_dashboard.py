# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class DprDashboard(models.Model):
    _name = 'dpr.dashboard'
    _description = 'DPR Dashboard Data'
    _rec_name = 'name'

    name = fields.Char(
        string='Dashboard Name',
        required=True
    )
    dashboard_type = fields.Selection([
        ('project', 'Project'),
        ('overall', 'Overall'),
        ('departmental', 'Departmental')
    ], string='Dashboard Type',
        default='overall'
    )
    date_from = fields.Date(
        string='Date From',
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        default=fields.Date.context_today
    )
    project_ids = fields.Many2many(
        'dpr.project',
        string='Filter Projects'
    )
    # KPI Metrics
    total_projects = fields.Integer(
        string='Total Projects',
        readonly=True
    )
    active_projects = fields.Integer(
        string='Active Projects',
        readonly=True
    )
    total_dpr_submitted = fields.Integer(
        string='Submitted DPRs',
        readonly=True
    )
    total_dpr_approved = fields.Integer(
        string='Approved DPRs',
        readonly=True
    )
    total_dpr_rejected = fields.Integer(
        string='Rejected DPRs',
        readonly=True
    )
    total_labor_count = fields.Integer(
        string='Total Labor Entries',
        readonly=True
    )
    total_labor_hours = fields.Float(
        string='Total Labor Hours',
        readonly=True
    )
    total_material_cost = fields.Float(
        string='Total Material Cost',
        readonly=True
    )
    total_equipment_cost = fields.Float(
        string='Total Equipment Cost',
        readonly=True
    )
    total_labor_cost = fields.Float(
        string='Total Labor Cost',
        readonly=True
    )
    average_progress = fields.Float(
        string='Average Progress %',
        readonly=True
    )
    weather_days_lost = fields.Float(
        string='Days Lost to Weather',
        readonly=True
    )
    labor_utilization_rate = fields.Float(
        string='Labor Utilization %',
        readonly=True
    )
    equipment_efficiency = fields.Float(
        string='Equipment Efficiency %',
        readonly=True
    )
    # Chart Data (JSON)
    progress_chart_data = fields.Text(
        string='Progress Chart Data',
        readonly=True
    )
    labor_chart_data = fields.Text(
        string='Labor Chart Data',
        readonly=True
    )
    material_chart_data = fields.Text(
        string='Material Chart Data',
        readonly=True
    )
    cost_breakdown_data = fields.Text(
        string='Cost Breakdown Data',
        readonly=True
    )
    is_favorite = fields.Boolean(
        string='Favorite',
        default=False
    )
    user_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    create_date = fields.Datetime(
        string='Created On',
        readonly=True
    )

    @api.model
    def refresh_dashboard(self, domain=None):
        """Refresh dashboard with latest data"""
        return self._compute_dashboard_metrics(domain)

    @api.model
    def _compute_dashboard_metrics(self, domain=None):
        """Compute dashboard metrics"""
        today = fields.Date.today()
        date_from = today - timedelta(days=30)
        date_to = today

        # Base domain
        base_domain = [('report_date', '>=', date_from),
                       ('report_date', '<=', date_to)]

        if domain:
            base_domain.extend(domain)

        # Compute metrics
        reports = self.env['dpr.report'].search(base_domain)

        metrics = {
            'total_projects': len(self.env['dpr.project'].search([('active', '=', True)])),
            'active_projects': len(self.env['dpr.project'].search([('state', '=', 'active')])),
            'total_dpr_submitted': len(reports.filtered(lambda r: r.state in ['submitted', 'approved'])),
            'total_dpr_approved': len(reports.filtered(lambda r: r.state == 'approved')),
            'total_dpr_rejected': len(reports.filtered(lambda r: r.state == 'rejected')),
            'total_labor_count': len(reports.mapped('labor_ids')),
            'total_labor_hours': sum(reports.mapped('labor_ids').mapped('hours_worked')),
            'total_material_cost': sum(reports.mapped('total_material_cost')),
            'total_equipment_cost': sum(reports.mapped('total_equipment_cost')),
            'total_labor_cost': sum(reports.mapped('total_labor_cost')),
            'weather_days_lost': sum(reports.mapped('weather_id').mapped('working_hours_lost')) / 8,
        }

        # Calculate averages
        if metrics['total_labor_count'] > 0:
            metrics['labor_utilization_rate'] = (metrics['total_labor_hours'] /
                                                   (metrics['total_labor_count'] * 8)) * 100

        return metrics

    @api.model
    def get_project_summary(self, project_id):
        """Get summary for a specific project"""
        project = self.env['dpr.project'].browse(project_id)
        reports = self.env['dpr.report'].search([
            ('project_id', '=', project_id),
            ('state', '=', 'approved')
        ])

        return {
            'project_name': project.name,
            'overall_progress': project.overall_progress,
            'total_dprs': len(reports),
            'total_labor_cost': sum(reports.mapped('total_labor_cost')),
            'total_material_cost': sum(reports.mapped('total_material_cost')),
            'total_equipment_cost': sum(reports.mapped('total_equipment_cost')),
            'total_cost': sum(reports.mapped('total_labor_cost')) +
                          sum(reports.mapped('total_material_cost')) +
                          sum(reports.mapped('total_equipment_cost')),
        }

    @api.model
    def get_daily_progress_data(self, days=7):
        """Get daily progress data for charts"""
        today = fields.Date.today()
        data = []

        for i in range(days):
            date = today - timedelta(days=days - i - 1)
            reports = self.env['dpr.report'].search([
                ('report_date', '=', date),
                ('state', 'in', ['submitted', 'approved'])
            ])

            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'dpr_count': len(reports),
                'labor_count': sum(reports.mapped('labor_ids').filtered(lambda l: l.present).mapped('hours_worked')),
                'material_cost': sum(reports.mapped('total_material_cost')),
                'equipment_cost': sum(reports.mapped('total_equipment_cost')),
            })

        return data

    @api.model
    def get_labor_utilization_data(self, project_id=None):
        """Get labor utilization data"""
        domain = []
        if project_id:
            domain.append(('project_id', '=', project_id))

        labor_entries = self.env['dpr.labor'].search(domain)
        by_work_type = {}

        for entry in labor_entries:
            work_type = entry.work_type
            if work_type not in by_work_type:
                by_work_type[work_type] = {'count': 0, 'hours': 0}
            by_work_type[work_type]['count'] += 1
            by_work_type[work_type]['hours'] += entry.hours_worked

        return by_work_type
