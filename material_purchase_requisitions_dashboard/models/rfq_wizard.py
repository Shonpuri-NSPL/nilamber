# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RFQWizard(models.TransientModel):
    _name = 'rfq.wizard'
    _description = 'RFQ Creation Wizard'

    # ---------------------------------------------
    # LOAD DEFAULT LINES FROM REQUISITION
    # ---------------------------------------------
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        req_id = self.env.context.get('default_requisition_id')
        if req_id:
            requisition = self.env['material.purchase.requisition'].browse(req_id)
            lines = []
            for line in requisition.requisition_line_ids:
                lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'qty': line.qty,
                }))
            res['line_ids'] = lines
        return res

    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisition',
        required=True,
        readonly=True
    )

    rfq_type = fields.Selection([
        ('all_to_all', 'Send All Products to All Vendors'),
        ('all_to_one', 'Send All Products to One Vendor'),
    ], default='all_to_all', required=True)

    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]"
    )

    partner_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
        domain="[('supplier_rank', '>', 0)]"
    )

    line_ids = fields.One2many(
        'rfq.wizard.line',
        'wizard_id',
        string='Products'
    )


    # ---------------------------------------------
    # BEHAVIOR: reset vendor fields based on rfq type
    # ---------------------------------------------
    @api.onchange('rfq_type')
    def _onchange_rfq_type(self):
        if self.rfq_type == 'all_to_one':
            self.partner_ids = False
        else:
            self.partner_id = False

    # ---------------------------------------------
    # CREATE RFQs
    # ---------------------------------------------
    def create_rfqs(self):
        self.ensure_one()

        requisition = self.requisition_id

        # ---------------- VALIDATION ----------------
        if self.rfq_type == 'all_to_one' and not self.partner_id:
            raise UserError("Please select a vendor.")

        if self.rfq_type == 'all_to_all' and not self.partner_ids:
            raise UserError("Please select at least one vendor.")

        # Check for zero prices and confirm with user
        zero_price_lines = self.line_ids.filtered(lambda l: l.price_unit == 0.0)
        non_zero_price_lines = self.line_ids.filtered(lambda l: l.price_unit > 0.0)
        
        if zero_price_lines and not non_zero_price_lines:
            # All lines have zero price - ask user if they want to delete RFQ
            return {
                'name': _('Confirm Zero Price RFQ'),
                'type': 'ir.actions.act_window',
                'res_model': 'rfq.zero.price.confirm.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_wizard_id': self.id,
                    'default_zero_price_count': len(zero_price_lines),
                    'default_total_lines': len(self.line_ids),
                }
            }
        elif zero_price_lines and non_zero_price_lines:
            # Some lines have zero price - ask user if they want to exclude them
            return {
                'name': _('Confirm Partial Zero Price RFQ'),
                'type': 'ir.actions.act_window',
                'res_model': 'rfq.zero.price.confirm.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_wizard_id': self.id,
                    'default_zero_price_count': len(zero_price_lines),
                    'default_total_lines': len(self.line_ids),
                    'default_has_mixed_prices': True,
                }
            }
        
        # If no zero prices, proceed with normal RFQ creation
        return self._create_rfqs_with_validation()
    
    def _create_rfqs_with_validation(self, exclude_zero_price_lines=False):
        """Helper method to create RFQs with optional exclusion of zero price lines"""
        self.ensure_one()
        
        requisition = self.requisition_id
        partners = (
            self.partner_ids
            if self.rfq_type == 'all_to_all'
            else self.partner_id
        )

        # Filter lines based on whether to exclude zero price lines
        lines_to_use = self.line_ids
        if exclude_zero_price_lines:
            lines_to_use = self.line_ids.filtered(lambda l: l.price_unit > 0.0)
        
        if not lines_to_use:
            raise UserError("No products with valid prices to create RFQ.")

        # ---------------- PREVENT DUPLICATES ----------------
        existing_vendors = self.env['purchase.order'].search([
            ('material_purchase_requisition_id', '=', requisition.id)
        ]).mapped('partner_id')

        for vendor in partners:
            if vendor in existing_vendors:
                raise UserError(
                    f"RFQ already exists for vendor: {vendor.name}. "
                    "Remove existing PO before sending again."
                )

        # ---------------- CREATE THE RFQs ----------------
        PurchaseOrder = self.env['purchase.order']

        for vendor in partners:
            po_vals = {
                'partner_id': vendor.id,
                'material_purchase_requisition_id': requisition.id,
                # 'requisition_id': False,
                'company_id': self.env.company.id,
                'currency_id': vendor.property_purchase_currency_id.id or self.env.company.currency_id.id,
                'date_order': fields.Datetime.now(),
                'project_id' : self.requisition_id.project_id.id,
                'order_line': [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.product_id.display_name or line.product_id.name or 'Product',
                        'product_uom_id': line.product_id.uom_id.id,
                        'product_qty': line.qty,
                        'price_unit': line.price_unit,
                        'date_planned': fields.Datetime.now(),
                    })
                    for line in lines_to_use if line.product_id
                ],
            }

            # Wrap in try block to expose real error if any
            try:
                po = PurchaseOrder.create(po_vals)
                # Auto-send the RFQ by changing state to sent
                po.write({'state': 'sent'})
            except Exception as e:
                raise UserError(f"PO Creation Failed: {str(e)}")

        # ---------------- UPDATE REQUISITION STATE ----------------
        requisition.write({'state': 'comparison'})

        return {'type': 'ir.actions.act_window_close'}


class RFQWizardLine(models.TransientModel):
    _name = 'rfq.wizard.line'
    _description = 'RFQ Wizard Line'

    wizard_id = fields.Many2one('rfq.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price', default=0.0, digits='Product Price')

    requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisition Line'
    )


class RFQZeroPriceConfirmWizard(models.TransientModel):
    _name = 'rfq.zero.price.confirm.wizard'
    _description = 'RFQ Zero Price Confirmation Wizard'

    wizard_id = fields.Many2one('rfq.wizard', string='RFQ Wizard')
    zero_price_count = fields.Integer(string='Zero Price Lines')
    total_lines = fields.Integer(string='Total Lines')
    has_mixed_prices = fields.Boolean(string='Has Mixed Prices', default=False)
    message = fields.Text(string='Message', readonly=True)
    exclude_zero_price_lines = fields.Boolean(string='Exclude Zero Price Lines', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        
        wizard_id = context.get('default_wizard_id')
        zero_price_count = context.get('default_zero_price_count', 0)
        total_lines = context.get('default_total_lines', 0)
        has_mixed_prices = context.get('default_has_mixed_prices', False)
        
        if has_mixed_prices:
            message = f"You have {zero_price_count} product(s) with zero price out of {total_lines} total products.\n\nDo you want to:\n• Create RFQ with only products that have prices (recommended)\n• Create RFQ with all products including zero-price ones"
        else:
            message = f"All {total_lines} product(s) have zero price.\n\nDo you want to:\n• Delete this RFQ (recommended)\n• Create RFQ with zero-price products"
        
        res.update({
            'wizard_id': wizard_id,
            'zero_price_count': zero_price_count,
            'total_lines': total_lines,
            'has_mixed_prices': has_mixed_prices,
            'message': message,
        })
        return res

    def action_confirm_with_prices(self):
        """Create RFQ excluding zero price lines"""
        if self.wizard_id:
            return self.wizard_id._create_rfqs_with_validation(exclude_zero_price_lines=True)
        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_with_zero_prices(self):
        """Create RFQ including zero price lines"""
        if self.wizard_id:
            return self.wizard_id._create_rfqs_with_validation(exclude_zero_price_lines=False)
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel_rfq(self):
        """Cancel RFQ creation entirely"""
        return {'type': 'ir.actions.act_window_close'}


class RFQLineZeroPriceConfirmWizard(models.TransientModel):
    _name = 'rfq.line.zero.price.confirm.wizard'
    _description = 'RFQ Line Zero Price Confirmation Wizard'

    line_id = fields.Integer(string='Line ID')
    vendor_id = fields.Integer(string='Vendor ID')
    product_id = fields.Integer(string='Product ID')
    requisition_id = fields.Integer(string='Requisition ID')
    product_name = fields.Char(string='Product Name')
    vendor_name = fields.Char(string='Vendor Name')
    message = fields.Text(string='Message', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        
        product_name = context.get('default_product_name', 'Unknown Product')
        vendor_name = context.get('default_vendor_name', 'Unknown Vendor')
        
        message = f"The product '{product_name}' from vendor '{vendor_name}' has zero price.\n\nDo you want to:\n• Confirm this product anyway\n• Cancel and remove this product from RFQ"
        
        res.update({
            'line_id': context.get('default_line_id'),
            'vendor_id': context.get('default_vendor_id'),
            'product_id': context.get('default_product_id'),
            'requisition_id': context.get('default_requisition_id'),
            'product_name': product_name,
            'vendor_name': vendor_name,
            'message': message,
        })
        return res

    def action_confirm_zero_price(self):
        """Confirm the product even with zero price"""
        requisition_model = self.env['material.purchase.requisition']
        return requisition_model._confirm_line_with_price(
            self.line_id, 
            self.vendor_id, 
            self.product_id, 
            self.requisition_id
        )

    def action_cancel_line(self):
        """Cancel and remove this product line"""
        line = self.env['purchase.order.line'].browse(self.line_id)
        if line.exists():
            line.unlink()
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Set default price from product's list price if not already set
            if not self.price_unit or self.price_unit == 0.0:
                self.price_unit = self.product_id.list_price