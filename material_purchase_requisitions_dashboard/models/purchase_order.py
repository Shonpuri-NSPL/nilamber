# -*- coding: utf-8 -*-

from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    material_purchase_requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisitions',
        copy=False,
        ondelete="set null",
    )

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    material_requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisitions Line',
        copy=False
    )
