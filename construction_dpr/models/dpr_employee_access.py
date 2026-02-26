# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprEmployeeAccess(models.Model):
    """
    Employee Access Control - Defines which towers/floors/units
    an employee can access for DPR reporting.
    
    Uses cascading selection:
    1. Select Project -> Towers populate
    2. Select Tower -> Floors populate
    3. Select Floor -> Units populate
    """
    _name = 'dpr.employee.access'
    _description = 'Employee Access Control'
    _order = 'employee_id, project_id'

    employee_id = fields.Many2one(
        'dpr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        help='Employee who gets access'
    )
    
    project_id = fields.Many2one(
        'dpr.project',
        string='Project',
        required=True,
        ondelete='cascade',
        help='Project to which access is granted'
    )
    
    # Tower selection
    tower_id = fields.Many2one(
        'dpr.task',
        string='Tower',
        ondelete='cascade',
        help='Select tower (optional)'
    )
    
    # Floor selection
    floor_id = fields.Many2one(
        'dpr.task',
        string='Floor',
        ondelete='cascade',
        help='Select floor (optional)'
    )
    
    # Unit selection
    unit_id = fields.Many2one(
        'dpr.task',
        string='Unit',
        ondelete='cascade',
        help='Select unit (optional)'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    description = fields.Char(
        string='Description',
        help='Optional description of access grant'
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset tower/floor/unit when project changes"""
        self.tower_id = False
        self.floor_id = False
        self.unit_id = False
        if self.project_id:
            return {
                'domain': {
                    'tower_id': [('project_id', '=', self.project_id.id), ('task_level', '=', 'tower')],
                }
            }
        else:
            return {'domain': {'tower_id': []}}

    @api.onchange('tower_id')
    def _onchange_tower_id(self):
        """Reset floor/unit when tower changes"""
        self.floor_id = False
        self.unit_id = False
        if self.tower_id:
            return {
                'domain': {
                    'floor_id': [('parent_id', '=', self.tower_id.id), ('task_level', '=', 'floor')],
                }
            }
        else:
            return {'domain': {'floor_id': []}}

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        """Reset unit when floor changes"""
        self.unit_id = False
        if self.floor_id:
            return {
                'domain': {
                    'unit_id': [('parent_id', '=', self.floor_id.id), ('task_level', '=', 'unit')],
                }
            }
        else:
            return {'domain': {'unit_id': []}}

    def name_get(self):
        """Custom name for access records"""
        result = []
        for record in self:
            name = f"{record.employee_id.name} - {record.project_id.name}"
            if record.tower_id:
                name += f" / {record.tower_id.name}"
                if record.floor_id:
                    name += f" / {record.floor_id.name}"
                    if record.unit_id:
                        name += f" / {record.unit_id.name}"
            result.append((record.id, name))
        return result

    def _get_tower_domain(self):
        """Get domain for tower field"""
        if self.project_id:
            return [('project_id', '=', self.project_id.id), ('task_level', '=', 'tower')]
        return [('task_level', '=', 'tower')]

    def _get_floor_domain(self):
        """Get domain for floor field based on tower"""
        if self.tower_id:
            return [('parent_id', '=', self.tower_id.id), ('task_level', '=', 'floor')]
        elif self.project_id:
            return [('project_id', '=', self.project_id.id), ('task_level', '=', 'floor')]
        return [('task_level', '=', 'floor')]

    def _get_unit_domain(self):
        """Get domain for unit field based on floor"""
        if self.floor_id:
            return [('parent_id', '=', self.floor_id.id), ('task_level', '=', 'unit')]
        elif self.tower_id:
            return [('parent_id.parent_id', '=', self.tower_id.id), ('task_level', '=', 'unit')]
        elif self.project_id:
            return [('project_id', '=', self.project_id.id), ('task_level', '=', 'unit')]
        return [('task_level', '=', 'unit')]
