# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprReport(models.Model):
    _name = 'dpr.report'
    _description = 'Daily Progress Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'report_date desc, name desc'

    name = fields.Char(
        string='Report Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    project_id = fields.Many2one(
        'dpr.project',
        string='Project',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    task_id = fields.Many2one(
        'dpr.task',
        string='Primary Task',
        domain="[('project_id', '=', project_id)]"
    )
    report_date = fields.Date(
        string='Report Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    prepared_by_id = fields.Many2one(
        'dpr.employee',
        string='Prepared By',
        required=True,
        tracking=True
    )
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status',
        default='draft',
        tracking=True
    )
    weather_id = fields.Many2one(
        'dpr.weather',
        string='Weather Conditions'
    )
    work_summary = fields.Text(
        string='Work Summary',
        required=True
    )
    delays_description = fields.Text(
        string='Delays/Issues'
    )
    safety_incidents = fields.Text(
        string='Safety Incidents'
    )
    notes = fields.Text(
        string='Additional Notes'
    )
    is_holiday = fields.Boolean(
        string='Holiday',
        default=False
    )
    total_labor_cost = fields.Monetary(
        string='Total Labor Cost',
        compute='_compute_costs',
        store=True
    )
    total_material_cost = fields.Monetary(
        string='Total Material Cost',
        compute='_compute_costs',
        store=True
    )
    total_equipment_cost = fields.Monetary(
        string='Total Equipment Cost',
        compute='_compute_costs',
        store=True
    )
    overall_progress = fields.Float(
        string='Overall Progress %',
        default=0.0
    )
    submission_time = fields.Datetime(
        string='Submission Time',
        readonly=True
    )
    approval_time = fields.Datetime(
        string='Approval Time',
        readonly=True
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True
    )
    latitude = fields.Float(
        string='GPS Latitude',
        digits=(10, 7)
    )
    longitude = fields.Float(
        string='GPS Longitude',
        digits=(10, 7)
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    labor_ids = fields.One2many(
        'dpr.labor',
        'report_id',
        string='Labor Entries'
    )
    material_ids = fields.One2many(
        'dpr.material',
        'report_id',
        string='Material Entries'
    )
    equipment_ids = fields.One2many(
        'dpr.equipment',
        'report_id',
        string='Equipment Entries'
    )
    photo_ids = fields.One2many(
        'dpr.photo',
        'report_id',
        string='Photos'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    _uniques = [
        ('report_unique', 'UNIQUE(project_id, report_date)',
         'Only one DPR report per project per day is allowed!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('dpr.report')
        return super().create(vals_list)

    @api.depends('labor_ids.wages_amount',
                 'material_ids.amount',
                 'equipment_ids.rental_amount')
    def _compute_costs(self):
        for report in self:
            report.total_labor_cost = sum(report.labor_ids.mapped('wages_amount'))
            report.total_material_cost = sum(report.material_ids.mapped('amount'))
            report.total_equipment_cost = sum(report.equipment_ids.mapped('rental_amount'))

    def action_submit(self):
        self.state = 'submitted'
        self.submission_time = fields.Datetime.now()

        # Send notification to project manager
        if self.project_id.project_manager_id:
            self.activity_schedule(
                'construction_dpr.mail_activity_dpr_approval',
                user_id=self.project_id.project_manager_id.id,
                note=_('DPR Report %s requires your approval') % self.name
            )

    def action_approve(self):
        self.state = 'approved'
        self.approved_by_id = self.env.user.id
        self.approval_time = fields.Datetime.now()
        self.activity_feedback(['construction_dpr.mail_activity_dpr_approval'])

    def action_reject(self, reason=''):
        self.state = 'rejected'
        self.rejection_reason = reason
        self.activity_feedback(['construction_dpr.mail_activity_dpr_approval'])

    def action_reset_to_draft(self):
        self.state = 'draft'

    def name_get(self):
        result = []
        for report in self:
            name = f"{report.name} - {report.project_id.name} - {report.report_date}"
            result.append((report.id, name))
        return result

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            self.task_id = False
