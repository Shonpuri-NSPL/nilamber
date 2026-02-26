# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class DprReportWizard(models.TransientModel):
    _name = 'dpr.report.wizard'
    _description = 'DPR Report Generation Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.today()
    )
    project_ids = fields.Many2many(
        'dpr.project',
        string='Projects',
        domain=[('active', '=', True)]
    )
    employee_ids = fields.Many2many(
        'dpr.employee',
        string='Employees'
    )
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('labor', 'Labor Report'),
        ('material', 'Material Report'),
        ('equipment', 'Equipment Report'),
        ('cost', 'Cost Analysis Report'),
        ('progress', 'Progress Report')
    ], string='Report Type',
        required=True,
        default='summary'
    )
    include_photos = fields.Boolean(
        string='Include Photos',
        default=False
    )
    include_weather = fields.Boolean(
        string='Include Weather Data',
        default=True
    )
    group_by = fields.Selection([
        ('project', 'Project'),
        ('date', 'Date'),
        ('employee', 'Employee'),
        ('none', 'No Grouping')
    ], string='Group By',
        default='project'
    )
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('html', 'HTML')
    ], string='Output Format',
        required=True,
        default='pdf'
    )

    def action_generate_report(self):
        """Generate the selected report"""
        self.ensure_one()

        # Build domain
        domain = [
            ('report_date', '>=', self.date_from),
            ('report_date', '<=', self.date_to),
        ]

        if self.project_ids:
            domain.append(('project_id', 'in', self.project_ids.ids))

        if self.employee_ids:
            domain.append(('prepared_by_id', 'in', self.employee_ids.ids))

        # Get data based on report type
        if self.report_type == 'summary':
            return self._generate_summary_report(domain)
        elif self.report_type == 'labor':
            return self._generate_labor_report(domain)
        elif self.report_type == 'material':
            return self._generate_material_report(domain)
        elif self.report_type == 'equipment':
            return self._generate_equipment_report(domain)
        elif self.report_type == 'cost':
            return self._generate_cost_report(domain)
        elif self.report_type == 'progress':
            return self._generate_progress_report(domain)

    def _generate_summary_report(self, domain):
        """Generate summary report"""
        reports = self.env['dpr.report'].search(domain)

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'projects': self.project_ids,
            'reports': reports,
            'include_photos': self.include_photos,
            'include_weather': self.include_weather,
        }

        if self.output_format == 'pdf':
            return self.env.ref('construction_dpr.action_report_dpr_summary').report_action(docids=reports.ids, data=data)
        elif self.output_format == 'xlsx':
            return self.env.ref('construction_dpr.action_xlsx_dpr_summary').report_action(docids=reports.ids, data=data)
        else:
            return self.env['ir.ui.view']._render_template('construction_dpr.report_dpr_summary_html', data)

    def _generate_labor_report(self, domain):
        """Generate labor report"""
        reports = self.env['dpr.report'].search(domain)
        labor_entries = reports.mapped('labor_ids')

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'labor_entries': labor_entries,
            'group_by': self.group_by,
        }

        return self.env.ref('construction_dpr.action_report_dpr_labor').report_action(docids=reports.ids, data=data)

    def _generate_material_report(self, domain):
        """Generate material report"""
        reports = self.env['dpr.report'].search(domain)
        material_entries = reports.mapped('material_ids')

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'material_entries': material_entries,
            'group_by': self.group_by,
        }

        return self.env.ref('construction_dpr.action_report_dpr_material').report_action(docids=reports.ids, data=data)

    def _generate_equipment_report(self, domain):
        """Generate equipment report"""
        reports = self.env['dpr.report'].search(domain)
        equipment_entries = reports.mapped('equipment_ids')

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'equipment_entries': equipment_entries,
            'group_by': self.group_by,
        }

        return self.env.ref('construction_dpr.action_report_dpr_equipment').report_action(docids=reports.ids, data=data)

    def _generate_cost_report(self, domain):
        """Generate cost analysis report"""
        reports = self.env['dpr.report'].search(domain)

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'reports': reports,
        }

        return self.env.ref('construction_dpr.action_report_dpr_progress').report_action(docids=reports.ids, data=data)

    def _generate_progress_report(self, domain):
        """Generate progress report"""
        reports = self.env['dpr.report'].search(domain)
        projects = self.project_ids or reports.mapped('project_id')

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'projects': projects,
            'reports': reports,
        }

        return self.env.ref('construction_dpr.action_report_dpr_progress').report_action(docids=reports.ids, data=data)

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        """Validate dates"""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                self.date_to = self.date_from
