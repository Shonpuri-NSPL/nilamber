# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CreateUnitsWizard(models.TransientModel):

    _name = 'create.units.wizard'
    _description = 'Create Units with Activities Wizard'

    floor_id = fields.Many2one(
        'dpr.task',
        string='Floor',
        required=True,
        domain=[('task_level', '=', 'floor')],
        help='Select the floor where units will be created'
    )
    project_id = fields.Many2one(
        'dpr.project',
        string='Project',
        related='floor_id.project_id',
        readonly=True
    )
    tower_id = fields.Many2one(
        'dpr.task',
        string='Tower',
        related='floor_id.parent_id',
        readonly=True
    )
    
    # Unit creation parameters
    unit_count = fields.Integer(
        string='Number of Units',
        default=2,
        required=True,
        help='Number of units to create on this floor'
    )
    unit_prefix = fields.Char(
        string='Unit Number Prefix',
        help='Prefix for unit numbers (e.g., "14" for 14th floor will create 1401, 1402...)'
    )
    starting_number = fields.Integer(
        string='Starting Number',
        default=1,
        required=True,
        help='Starting number for units (e.g., 1 will create 01, 02...)'
    )
    unit_type = fields.Selection([
        ('1bhk', '1 BHK'),
        ('2bhk', '2 BHK'),
        ('3bhk', '3 BHK'),
        ('3.5bhk', '3.5 BHK'),
        ('4bhk', '4 BHK'),
        ('4.5bhk', '4.5 BHK'),
        ('5bhk', '5 BHK'),
        ('penthouse', 'Penthouse'),
        ('duplex', 'Duplex'),
        ('studio', 'Studio'),
        ('shop', 'Shop'),
        ('office', 'Office'),
        ('club', 'Club House'),
        ('amenity', 'Amenity'),
        ('other', 'Other')
    ], string='Unit Type',
        default='3bhk',
        required=True
    )
    carpet_area = fields.Float(
        string='Carpet Area (sq.ft)',
        help='Default carpet area for all units'
    )
    
    # Activity creation
    create_activities = fields.Boolean(
        string='Create Standard Activities',
        default=True,
        help='Automatically create 19 standard activities for each unit'
    )
    activity_template_ids = fields.Many2many(
        'dpr.activity.template',
        string='Activity Templates',
        help='Select activity templates to create (leave empty for all active templates)'
    )
    
    # Date parameters
    planned_start_date = fields.Date(
        string='Planned Start Date',
        default=fields.Date.today,
        required=True
    )
    planned_end_date = fields.Date(
        string='Planned End Date',
        required=True
    )

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        """Auto-populate unit prefix from floor number"""
        if self.floor_id and self.floor_id.floor_number:
            floor_num = self.floor_id.floor_number
            if floor_num > 0:
                self.unit_prefix = str(floor_num)
            elif floor_num == 0:
                self.unit_prefix = "G"  # Ground floor
            else:
                self.unit_prefix = f"B{abs(floor_num)}"  # Basement

    @api.constrains('unit_count')
    def _check_unit_count(self):
        for wizard in self:
            if wizard.unit_count < 1 or wizard.unit_count > 50:
                raise ValidationError(_('Unit count must be between 1 and 50!'))

    @api.constrains('planned_start_date', 'planned_end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.planned_end_date < wizard.planned_start_date:
                raise ValidationError(_('End date cannot be before start date!'))

    def action_create_units(self):
        """Create units with activities"""
        self.ensure_one()
        
        if not self.floor_id:
            raise ValidationError(_('Please select a floor!'))
        
        # Get activity templates
        if self.create_activities:
            if self.activity_template_ids:
                templates = self.activity_template_ids
            else:
                templates = self.env['dpr.activity.template'].search([('active', '=', True)], order='sequence')
            
            if not templates:
                raise ValidationError(_('No activity templates found! Please create activity templates first.'))
        
        created_units = self.env['dpr.task']
        
        # Create units
        for i in range(self.unit_count):
            unit_num = self.starting_number + i
            unit_number = f"{self.unit_prefix}{unit_num:02d}" if self.unit_prefix else f"{unit_num:02d}"
            
            # Create unit
            unit_vals = {
                'name': f"Unit {unit_number}",
                'project_id': self.project_id.id,
                'parent_id': self.floor_id.id,
                'task_level': 'unit',
                'unit_number': unit_number,
                'unit_type': self.unit_type,
                'carpet_area': self.carpet_area,
                'planned_start_date': self.planned_start_date,
                'planned_end_date': self.planned_end_date,
                'sequence': unit_num,
                'state': 'pending',
            }
            
            unit = self.env['dpr.task'].create(unit_vals)
            created_units |= unit
            
            # Create activities for this unit
            if self.create_activities:
                for template in templates:
                    activity_vals = {
                        'name': template.name,
                        'project_id': self.project_id.id,
                        'parent_id': unit.id,
                        'task_level': 'activity',
                        'activity_template_id': template.id,
                        'activity_category': template.category,
                        'activity_status': 'not_started',
                        'planned_start_date': self.planned_start_date,
                        'planned_end_date': self.planned_end_date,
                        'estimated_hours': template.estimated_hours,
                        'sequence': template.sequence,
                        'state': 'pending',
                    }
                    self.env['dpr.task'].create(activity_vals)
        
        # Return action to view created units
        return {
            'name': _('Created Units'),
            'type': 'ir.actions.act_window',
            'res_model': 'dpr.task',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_units.ids)],
            'context': {'default_parent_id': self.floor_id.id},
        }
