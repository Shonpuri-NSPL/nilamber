# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DprTaskType(models.Model):
    _name = 'dpr.task.type'
    _description = 'Construction Task Type'
    _order = 'sequence, name'
    _uniques = [
        ('name_unique', 'UNIQUE(name)', 'Task type name must be unique!'),
    ]

    name = fields.Char(
        string='Task Type',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the task type'
    )
    description = fields.Text(
        string='Description'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure unique codes are uppercase"""
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = vals['code'].upper()
        return super().create(vals_list)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name}"
            if record.code:
                name = f"[{record.code}] {name}"
            result.append((record.id, name))
        return result
