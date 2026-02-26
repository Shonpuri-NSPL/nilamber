# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprActivityTemplate(models.Model):
    """
    Standard Activity Templates for Construction Units
    Based on 19 standard activities from Excel: Tower wise Activity status check.xlsx
    """
    _name = 'dpr.activity.template'
    _description = 'Activity Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Activity Name',
        required=True,
        help='Standard activity name'
    )
    code = fields.Char(
        string='Activity Code',
        required=True,
        help='Unique code for activity'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    category = fields.Selection([
        ('structural', 'Structural Work'),
        ('masonry', 'Masonry Work'),
        ('electrical', 'Electrical Work'),
        ('plumbing', 'Plumbing Work'),
        ('waterproofing', 'Waterproofing'),
        ('flooring', 'Flooring Work'),
        ('tiling', 'Tiling Work'),
        ('carpentry', 'Carpentry Work'),
        ('painting', 'Painting Work'),
        ('finishing', 'Finishing Work'),
        ('fixtures', 'Fixtures & Fittings'),
        ('other', 'Other')
    ], string='Category',
        required=True,
        default='other'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of the activity'
    )
    estimated_duration_days = fields.Integer(
        string='Estimated Duration (Days)',
        help='Typical duration for this activity'
    )
    estimated_hours = fields.Float(
        string='Estimated Hours',
        help='Typical labor hours required'
    )
    unit_type_ids = fields.Many2many(
        'dpr.unit.type',
        string='Applicable Unit Types',
        help='Unit types where this activity applies'
    )
    is_mandatory = fields.Boolean(
        string='Mandatory',
        default=True,
        help='Whether this activity is mandatory for all units'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    _uniques = [
        ('code_unique', 'UNIQUE(code)', 'Activity code must be unique!')
    ]

    def name_get(self):
        result = []
        for template in self:
            name = f"[{template.code}] {template.name}"
            result.append((template.id, name))
        return result


class DprUnitType(models.Model):
    """Unit Type Configuration"""
    _name = 'dpr.unit.type'
    _description = 'Unit Type'
    _order = 'sequence, name'

    name = fields.Char(
        string='Unit Type',
        required=True
    )
    code = fields.Char(
        string='Code',
        required=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    description = fields.Text(
        string='Description'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    _uniques = [
        ('code_unique', 'UNIQUE(code)', 'Unit type code must be unique!')
    ]
