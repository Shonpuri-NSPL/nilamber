# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprEquipment(models.Model):
    _name = 'dpr.equipment'
    _description = 'Equipment Usage Entry'
    _rec_name = 'equipment_name'

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
    equipment_type = fields.Many2one(
        'dpr.equipment.type',
        string='Equipment Type',
        required=True
    )
    equipment_name = fields.Char(
        string='Equipment Name/ID',
        required=True
    )
    hours_operated = fields.Float(
        string='Hours Operated',
        default=0.0,
        required=True
    )
    idle_hours = fields.Float(
        string='Idle Hours',
        default=0.0
    )
    breakdown_hours = fields.Float(
        string='Breakdown Hours',
        default=0.0
    )
    operator_name = fields.Char(
        string='Operator Name'
    )
    fuel_consumed = fields.Float(
        string='Fuel Consumed (Litres)',
        default=0.0
    )
    maintenance_status = fields.Selection([
        ('good', 'Good'),
        ('attention', 'Needs Attention'),
        ('critical', 'Critical')
    ], string='Maintenance Status',
        default='good'
    )
    task_id = fields.Many2one(
        'dpr.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    rental_rate = fields.Float(
        string='Daily Rental Rate',
        required=True
    )
    rental_amount = fields.Monetary(
        string='Rental Amount',
        compute='_compute_rental_amount',
        store=True
    )
    notes = fields.Text(
        string='Notes'
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

    @api.depends('hours_operated', 'rental_rate')
    def _compute_rental_amount(self):
        for equipment in self:
            # Calculate rental based on hours operated (pro-rated from daily rate)
            equipment.rental_amount = (equipment.hours_operated / 8) * equipment.rental_rate

    @api.constrains('hours_operated', 'idle_hours', 'breakdown_hours')
    def _check_hours(self):
        for equipment in self:
            total_hours = equipment.hours_operated + equipment.idle_hours + equipment.breakdown_hours
            if total_hours > 24:
                raise ValidationError(_('Total hours cannot exceed 24!'))

    @api.onchange('equipment_type')
    def _onchange_equipment_type(self):
        if self.equipment_type:
            # Auto-set equipment name based on type
            self.equipment_name = self.equipment_type.name
