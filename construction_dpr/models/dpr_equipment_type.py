# -*- coding: utf-8 -*-

from odoo import models, fields


class DprEquipmentType(models.Model):
    _name = 'dpr.equipment.type'
    _description = 'Equipment Type Master'
    _rec_name = 'name'

    name = fields.Char(
        string='Equipment Type Name',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Code',
        required=False,
        help='Short code for the equipment type'
    )
    description = fields.Text(
        string='Description'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    _uniques = [
        ('name_unique', 'unique(name)', 'Equipment type name must be unique!'),
    ]
