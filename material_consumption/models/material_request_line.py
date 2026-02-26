# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MaterialRequestLine(models.Model):
    _name = 'material.request.line'
    _description = 'Material Request Line'
    _order = 'id asc'

    request_id = fields.Many2one('material.request', string='Material Request', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id',
                                      string='Product Template')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    quantity = fields.Float(string='Quantity', required=True, digits=(16, 2),
                            default=1.0)

    # Pricing
    unit_price = fields.Float(string='Unit Price', digits=(16, 2),)
    currency_id = fields.Many2one('res.currency', related='request_id.currency_id', string='Currency')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)

    # Available Stock
    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
        readonly=True,
        digits=(16, 2),
    )

    # Description
    description = fields.Char(string='Description')

    # Warehouse
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]"
    )

    # Billable Information
    is_billable = fields.Boolean(related='request_id.is_billable', string='Billable', store=True)
    billable_price = fields.Float(string='Billable Price', digits=(16, 2))

    # Project Task Reference
    task_id = fields.Many2one('project.task', related='request_id.task_id', string='Task', readonly=True)

    # Lot/Serial Number tracking
    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial/Lot Number',
        domain="[('id', 'in', available_lot_ids)]"
        #domain="[('product_id', '=', product_id)]"
    )

    available_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_available_lot_ids'
    )

    is_tracked = fields.Boolean(
        string='Is Tracked',
        compute='_compute_is_tracked',
        store=True
    )

    @api.depends('product_id')
    def _compute_is_tracked(self):
        for line in self:
            line.is_tracked = bool(
                line.product_id and line.product_id.tracking != 'none'
            )

    @api.depends('product_id', 'location_id')
    def _compute_available_qty(self):
        """Compute available quantity based on selected location"""
        for line in self:
            if not line.product_id:
                line.available_qty = 0.0
                continue
            
            domain = [
                ('product_id', '=', line.product_id.id),
                ('quantity', '>', 0),
            ]
            
            # Filter by location if selected
            if line.location_id:
                domain.append(('location_id', '=', line.location_id.id))
            
            quants = self.env['stock.quant'].search(domain)
            line.available_qty = sum(quant.quantity for quant in quants)

    @api.depends('product_id', 'location_id')
    def _compute_available_lot_ids(self):
        for line in self:
            if not line.product_id:
                line.available_lot_ids = False
                continue

            domain = [
                ('product_id', '=', line.product_id.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ]
            
            # Filter by location if selected
            if line.location_id:
                domain.append(('location_id', '=', line.location_id.id))

            quants = self.env['stock.quant'].search(domain)
            line.available_lot_ids = quants.mapped('lot_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.uom_id = record.product_id.uom_id.id
                record.unit_price = record.product_id.list_price
                record.description = record.product_id.name
                # Set default warehouse and location based on product
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
                if warehouse:
                    record.warehouse_id = warehouse.id
                    record.location_id = warehouse.lot_stock_id.id
            record.lot_id = False

    @api.onchange('location_id')
    def _onchange_location_id(self):
        """Refresh available qty and lots when location changes"""
        # Clear lot_id if it's not available in the new location
        if self.lot_id and self.location_id:
            lot_in_location = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id),
                ('location_id', '=', self.location_id.id),
                ('quantity', '>', 0),
            ], limit=1)
            if not lot_in_location:
                self.lot_id = False
        elif not self.location_id:
            self.lot_id = False

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.quantity * record.unit_price

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
    
    def write(self, vals):
        for line in self:
            if line.request_id.state in ('approved', 'issued', 'rejected', 'cancelled'):
                raise UserError(_('You cannot modify material request lines when the request is %s.') % line.request_id.state)
        return super(MaterialRequestLine, self).write(vals)
    
    def unlink(self):
        for line in self:
            if line.request_id.state in ('approved', 'issued', 'rejected', 'cancelled'):
                raise UserError(_('You cannot delete material request lines when the request is %s.') % line.request_id.state)
        return super(MaterialRequestLine, self).unlink()

    @api.onchange('quantity')
    def _onchange_quantity(self):
        """Check if sufficient stock is available"""
        for record in self:
            if record.product_id and record.quantity > record.available_qty:
                return {
                    'warning': {
                        'title': _('Insufficient Stock'),
                        'message': _('Only %s units of %s are available in stock.') % (record.available_qty,
                                                                                       record.product_id.name)
                    }
                }
