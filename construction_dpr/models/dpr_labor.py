# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprLabor(models.Model):
    _name = 'dpr.labor'
    _description = 'Labor Attendance & Work Entry'
    _rec_name = 'employee_id'

    report_id = fields.Many2one(
        'dpr.report',
        string='DPR Report',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'dpr.project',
        related='report_id.project_id',
        string='Project',
        store=True
    )
    employee_id = fields.Many2one(
        'dpr.employee',
        string='Employee',
        required=True
    )
    work_type = fields.Selection([
        ('skilled', 'Skilled'),
        ('unskilled', 'Unskilled'),
        ('supervisor', 'Supervisor'),
        ('subcontractor', 'Subcontractor')
    ], string='Work Type',
        required=True,
        default='skilled'
    )
    hours_worked = fields.Float(
        string='Hours Worked',
        default=8.0,
        required=True
    )
    overtime_hours = fields.Float(
        string='Overtime Hours',
        default=0.0
    )
    hourly_rate = fields.Float(
        string='Hourly Rate',
        required=True
    )
    wages_amount = fields.Monetary(
        string='Wages Amount',
        compute='_compute_wages',
        store=True
    )
    work_description = fields.Text(
        string='Work Description'
    )
    task_id = fields.Many2one(
        'dpr.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    present = fields.Boolean(
        string='Present',
        default=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.depends('hours_worked', 'overtime_hours', 'hourly_rate')
    def _compute_wages(self):
        for labor in self:
            total_hours = labor.hours_worked + (labor.overtime_hours * 1.5)
            labor.wages_amount = total_hours * labor.hourly_rate

    @api.constrains('hours_worked', 'overtime_hours')
    def _check_hours(self):
        for labor in self:
            if labor.hours_worked < 0 or labor.hours_worked > 24:
                raise ValidationError(_('Hours worked must be between 0 and 24!'))
            if labor.overtime_hours < 0:
                raise ValidationError(_('Overtime hours cannot be negative!'))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.hourly_rate:
            self.hourly_rate = self.employee_id.hourly_rate
