# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    request_id = fields.Many2one('material.request', string='Material Request', readonly=True, copy=False)
