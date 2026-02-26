# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprMaterial(models.Model):
    _name = 'dpr.material'
    _description = 'Material Consumption Entry'
    _rec_name = 'item_name'

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
    material_type = fields.Selection([
        ('cement', 'Cement'),
        ('steel', 'Steel'),
        ('sand', 'Sand'),
        ('aggregate', 'Aggregate'),
        ('brick', 'Brick'),
        ('concrete', 'Concrete'),
        ('other', 'Other')
    ], string='Material Type',
        required=True
    )
    item_name = fields.Char(
        string='Item Name',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain=[('type', 'in', ['product', 'consumable'])]
    )
    quantity = fields.Float(
        string='Quantity Used',
        required=True,
        default=1.0
    )
    unit = fields.Selection([
        ('ton', 'Ton'),
        ('kg', 'Kg'),
        ('cum', 'Cubic Meter'),
        ('sqm', 'Square Meter'),
        ('piece', 'Piece'),
        ('bag', 'Bag'),
        ('litre', 'Litre')
    ], string='Unit',
        required=True,
        default='piece'
    )
    rate = fields.Float(
        string='Rate per Unit',
        required=True
    )
    amount = fields.Monetary(
        string='Amount',
        compute='_compute_amount',
        store=True
    )
    source = fields.Selection([
        ('site_stock', 'Site Stock'),
        ('contractor', 'Contractor Supply'),
        ('purchased', 'Purchased')
    ], string='Source',
        required=True,
        default='site_stock'
    )
    task_id = fields.Many2one(
        'dpr.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    opening_stock = fields.Float(
        string='Opening Stock'
    )
    closing_stock = fields.Float(
        string='Closing Stock'
    )
    received_qty = fields.Float(
        string='Quantity Received'
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

    @api.depends('quantity', 'rate')
    def _compute_amount(self):
        for material in self:
            material.amount = material.quantity * material.rate

    @api.constrains('quantity', 'opening_stock', 'closing_stock')
    def _check_stock(self):
        for material in self:
            if material.closing_stock and material.opening_stock:
                if material.received_qty:
                    expected_closing = material.opening_stock + material.received_qty - material.quantity
                else:
                    expected_closing = material.opening_stock - material.quantity
                if abs(material.closing_stock - expected_closing) > 0.01:
                    raise ValidationError(_('Stock reconciliation error! Expected closing stock: %s') % expected_closing)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.item_name = self.product_id.name
            if self.product_id.list_price:
                self.rate = self.product_id.list_price
