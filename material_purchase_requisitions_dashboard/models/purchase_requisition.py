# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

class PurchaseOrder(models.Model):
    _name = 'material.purchase.requisition'
    _description = 'Material Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, default = lambda self: self.env['ir.sequence'].next_by_code('purchase.requisition.seq') or 'New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string='Department')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    project_id = fields.Many2one('project.project', string='Project')
    site_location = fields.Many2one('stock.location', string='Site Location')

    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    receive_date = fields.Date(string='Receive Date')
    requisition_type = fields.Selection([
        ('internal', 'Internal Picking'),
        ('purchase', 'Purchase Order'),
    ], string='Requisition Type', default='purchase')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('dept_confirm', 'Department Confirmed'),
        ('budget_check', 'Budget Check'),
        ('ir_approve', 'Waiting Approval'),
        ('procurement_review', 'Procurement Review'),
        ('approve', 'Approved'),
        ('rfq_creation', 'RFQ Creation'),
        ('comparison', 'Comparison'),
        ('po_confirm', 'PO Confirmed'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'),
    ], string='Status', default='draft')
    requisition_line_ids = fields.One2many('material.purchase.requisition.line', 'requisition_id', string='Requisition Lines')
    purchase_order_ids = fields.One2many('purchase.order', 'material_purchase_requisition_id', string='RFQs / Purchase Orders')
    reason = fields.Text(string='Reason')
    approve_manager_id = fields.Many2one('res.users', string='Approved by Manager')
    approve_employee_id = fields.Many2one('res.users', string='Approved by Employee')
    confirm_date = fields.Datetime(string='Confirm Date')
    managerapp_date = fields.Datetime(string='Manager Approval Date')
    userrapp_date = fields.Datetime(string='User Approval Date')
    userreject_date = fields.Datetime(string='Reject Date')
    date_done = fields.Datetime(string='Date Done')
    employee_confirm_id = fields.Many2one('res.users', string='Employee Confirmed By')
    reject_employee_id = fields.Many2one('res.users', string='Rejected By')
    reject_reason = fields.Text(string='Rejection Reason')
    
    # History tracking
    state_history_ids = fields.One2many('purchase.requisition.history', 'requisition_id', string='State History', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('picking_type_id'):
                site_location = vals.get('site_location')
                company_id = vals.get('company_id', self.env.company.id)

                if site_location:
                    # Get warehouse associated with the selected location
                    warehouses = self.env['stock.warehouse'].search([('lot_stock_id', '=', site_location)])
                    if warehouses:
                        picking_types = self.env['stock.picking.type'].search([
                            ('warehouse_id', '=', warehouses[0].id),
                            ('code', '=', 'incoming')
                        ], limit=1)
                        if picking_types:
                            vals['picking_type_id'] = picking_types.id
                            vals['warehouse_id'] = warehouses[0].id

        return super(PurchaseOrder, self).create(vals_list)


    
    @api.model
    def _default_picking_type_id(self):
        picking_type = self.env['stock.picking.type'].search([('warehouse_id.company_id', '=', self.env.company.id), ('code', '=', 'incoming')], limit=1)
        if not picking_type:
            self.env['stock.warehouse']._warehouse_redirect_warning()
        return picking_type

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', domain="[('company_id', '=', company_id)]")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', required=True, default=_default_picking_type_id)
    
    def _track_state_change(self, new_state, notes=None, from_state=None):
        """Track state changes in history"""
        state_labels = {
            'draft': 'Draft',
            'dept_confirm': 'Department Confirmed',
            'budget_check': 'Budget Check',
            'ir_approve': 'Waiting Approval',
            'procurement_review': 'Procurement Review',
            'approve': 'Approved',
            'rfq_creation': 'RFQ Creation',
            'comparison': 'Comparison',
            'po_confirm': 'PO Confirmed',
            'cancel': 'Cancelled',
            'reject': 'Rejected',
        }
        
        self.env['purchase.requisition.history'].create({
            'requisition_id': self.id,
            'from_state': from_state or self.state,
            'to_state': new_state,
            'state_label': state_labels.get(new_state, new_state),
            'user_id': self.env.user.id,
            'notes': notes,
            'ip_address': self.env.context.get('request_ip') if self.env.context.get('request_ip') else '127.0.0.1'
        })

    @api.onchange('site_location')
    def _onchange_site_location(self):
        """Reset picking_type_id when location changes and update domain"""
        if self.site_location:
            # Clear the current picking type to force re-selection with new domain
            self.picking_type_id = False
            # Update warehouse based on selected location
            warehouses = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.site_location.id)])
            if warehouses:
                self.warehouse_id = warehouses[0]
        else:
            self.warehouse_id = False
            self.picking_type_id = False
        
        # Return domain update for picking_type_id
        return {
            'domain': {
                'picking_type_id': self._get_picking_type_domain()
            }
        }
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Reset picking_type_id when company changes"""
        self.picking_type_id = False
        self.warehouse_id = False
        return {
            'domain': {
                'picking_type_id': self._get_picking_type_domain()
            }
        }
    
    def _get_picking_type_domain(self):
        """Get domain for picking types based on selected location"""
        domain = []
        if self.site_location:
            # Get warehouse associated with the selected location
            warehouses = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.site_location.id)])
            if warehouses:
                domain = [('warehouse_id', '=', warehouses[0].id)]
            else:
                # If no direct warehouse found, get warehouses in the same company
                domain = [('warehouse_id.company_id', '=', self.company_id.id)]
        else:
            # If no location selected, show all warehouses for the company
            domain = [('warehouse_id.company_id', '=', self.company_id.id)]
        return domain


    def requisition_confirm(self):
        old_state = self.state
        self.write({'state': 'dept_confirm'})
        self._track_state_change('dept_confirm', 'Requisition confirmed by employee', old_state)

    def budget_approve(self):
        old_state = self.state
        self.write({
            'state': 'dept_confirm',
            'employee_confirm_id': self.env.user.id,
            'confirm_date': fields.Datetime.now(),
        })
        self._track_state_change('dept_confirm', 'Budget approved', old_state)

    def manager_approve(self):
        old_state = self.state
        self.write({
            'state': 'ir_approve',
            'approve_manager_id': self.env.user.id,
            'managerapp_date': fields.Datetime.now(),
        })
        self._track_state_change('ir_approve', 'Department approved by manager', old_state)

    def procurement_review(self):
        old_state = self.state
        self.write({'state': 'procurement_review'})
        self._track_state_change('procurement_review', 'Moved to procurement review', old_state)

    def user_approve(self):
        old_state = self.state
        self.write({
            'state': 'rfq_creation',
            'approve_employee_id': self.env.user.id,
            'userrapp_date': fields.Datetime.now(),
        })
        self._track_state_change('rfq_creation', 'Approved by procurement user', old_state)

    def create_rfqs(self):
        return {
            'name': 'Create RFQs',
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_requisition_id': self.id},
        }

    def action_po_confirm(self):
        old_state = self.state
        self.write({'state': 'po_confirm'})
        self._track_state_change('po_confirm', 'PO Confirmed', old_state)

    def requisition_reject(self):
        # Show dialog to capture rejection reason
        return {
            'name': 'Rejection Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_requisition_id': self.id},
        }
    
    def reject_with_reason(self, reason):
        """Reject requisition with reason"""
        old_state = self.state
        self.write({
            'state': 'reject',
            'reject_employee_id': self.env.user.id,
            'reject_reason': reason,
            'userreject_date': fields.Datetime.now(),
        })
        self._track_state_change('reject', f'Rejected: {reason}', old_state)

    def action_cancel(self):
        old_state = self.state
        self.write({'state': 'cancel'})
        self._track_state_change('cancel', 'Requisition cancelled', old_state)

    def reset_draft(self):
        old_state = self.state
        self.write({'state': 'draft'})
        self._track_state_change('draft', 'Reset to draft', old_state)


    def action_show_po(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'RFQs / Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('material_purchase_requisition_id', '=', self.id)],
            'context': {'default_material_purchase_requisition_id': self.id},
        }
    
    def action_show_history(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'State History',
            'res_model': 'purchase.requisition.history',
            'view_mode': 'list,form',
            'domain': [('requisition_id', '=', self.id)],
            'context': {'default_requisition_id': self.id},
        }

    @api.model
    def get_purchase_line_data(self, option, requisition_id=None, project_filter=None):
        min_price_total = []
        min_delivery_date = []
        
        record = []
        total = []
        partner_ids = []

        min_total_vendor = 0
        min_delivery_vendor = 0
        
        # Get all projects for the filter dropdown
        projects = self.env['project.project'].search([]).mapped(lambda p: {'id': p.id, 'name': p.name})
        
        tendor_id = self.env['material.purchase.requisition'].search([('id', '=', requisition_id)], limit=1)
        if not tendor_id:
            return {
                'record_line_ids': [],
                'partner_ids': [],
                'total': [],
                'length': 0,
                'option': option,
                'min_total_vendor': 0,
                'min_delivery_vendor': 0,
                'reqisition_name': 'Unknown',
                'projects': projects,
            }
            
        purchase_ids = self.env['purchase.order'].search([('material_purchase_requisition_id', '=', tendor_id.id)]).filtered(lambda x: len(x.order_line.ids) > 0)
        
        # Filter out purchase orders that don't exist or have no lines
        purchase_ids = purchase_ids.filtered(lambda po: po.exists() and len(po.order_line.ids) > 0)
        
        # Apply project filter if specified
        if project_filter:
            purchase_ids = purchase_ids.filtered(lambda po: po.material_purchase_requisition_id.project_id.id == int(project_filter))
            
        product_ids = self.env['purchase.order.line'].search([('order_id', 'in', purchase_ids.ids)]).mapped('product_id')
        
        # Filter out products that don't have valid lines
        product_ids = product_ids.filtered(lambda p: p.exists())
        
        for purchase_id in purchase_ids:
            min_price_total.append(sum(purchase_id.order_line.mapped('price_unit')))
            min_delivery_date.append(min(purchase_id.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"))

        for order in purchase_ids:
            if min(min_price_total) == sum(order.order_line.mapped('price_unit')):
                min_total_vendor = order.partner_id
            if min(min_delivery_date) == min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"):
                min_delivery_vendor = order.partner_id

        for order in purchase_ids:
            if option =='by_price' and min_total_vendor == order.partner_id:
                partner_ids.append({
                    'option': 'by_price',
                    'id': order.partner_id.id,
                    'name': f"{order.partner_id.name} - {order.name}",
                    'rfq_number': order.name,
                })
                total.append({
                    'state': order.state,
                    'option': 'by_price',
                    'id': order.id,
                    'partner_id':order.partner_id.id,
                    'total': order.amount_total,
                    'subtotal': sum(order.order_line.mapped('price_unit')),
                    'tax': order.amount_tax,
                    'delivery_date': min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"),
                })
            elif option =='by_date' and min_delivery_vendor == order.partner_id:
                partner_ids.append({
                    'option': 'by_date',
                    'id': order.partner_id.id,
                    'name': f"{order.partner_id.name} - {order.name}",
                    'rfq_number': order.name,
                })
                total.append({
                    'state': order.state,
                    'option': 'by_date',
                    'id': order.id,
                    'partner_id':order.partner_id.id,
                    'total': order.amount_total,
                    'subtotal': sum(order.order_line.mapped('price_unit')),
                    'tax': order.amount_tax,
                    'delivery_date': min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"),
                })
            else:
                partner_ids.append({
                    'option': '',
                    'id': order.partner_id.id,
                    'name': f"{order.partner_id.name} - {order.name}",
                    'rfq_number': order.name,
                })
                total.append({
                    'state': order.state,
                    'option': '',
                    'id': order.id,
                    'partner_id':order.partner_id.id,
                    'total': order.amount_total,
                    'subtotal': sum(order.order_line.mapped('price_unit')),
                    'tax': order.amount_tax,
                    'delivery_date': min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"),
                })

        for product_id in product_ids:
            lines=[]
            
            # Get lines for this product, handling cases where orders might be deleted
            product_lines = self.env['purchase.order.line'].search([
                ('order_id', 'in', purchase_ids.ids), 
                ('product_id', '=', product_id.id)
            ]).filtered(lambda line: line.exists() and line.order_id.exists())
            
            if not product_lines:
                # Skip products with no valid lines
                continue
                
            min_prize = min(product_lines.mapped('price_unit'))
            
            # Find vendor with minimum price
            min_price_line = product_lines.filtered(lambda l: l.price_unit == min_prize)[0]
            min_prize_vendor = min_price_line.order_id.partner_id if min_price_line.order_id.exists() else None
            
            min_date = min(product_lines.mapped('date_planned'))
            
            # Find vendor with minimum date
            min_date_line = product_lines.filtered(lambda l: l.date_planned == min_date)[0]
            min_date_vendor = min_date_line.order_id.partner_id if min_date_line.order_id.exists() else None
            for vendor_id in purchase_ids:
                if vendor_id.exists() and product_id.id in vendor_id.order_line.mapped('product_id').ids:
                    for order_line in vendor_id.order_line:
                        if order_line.product_id.id == product_id.id and order_line.exists():
                            if option =='by_price' and min_prize_vendor and min_total_vendor == vendor_id.partner_id:
                                lines.append({
                                    'option': 'by_price',
                                    'message': ('Delivery Date :' + str(order_line.date_planned)),
                                    'vendor_id': vendor_id.partner_id.id,
                                    'line_id': order_line.id,
                                    'product_id': order_line.product_id.id,
                                    'vendor_name': f"{vendor_id.partner_id.name} - {vendor_id.name}",
                                    'unit_price': order_line.price_unit,
                                    'qty': order_line.product_qty,
                                    })
                            
                            elif option =='by_date' and min_date_vendor and min_delivery_vendor == vendor_id.partner_id:
                                lines.append({
                                    'option': 'by_date',
                                    'vendor_id': vendor_id.partner_id.id,
                                    'message': ('Delivery Date :' + str(order_line.date_planned)),
                                    'line_id': order_line.id,
                                    'product_id': order_line.product_id.id,
                                    'vendor_name': f"{vendor_id.partner_id.name} - {vendor_id.name}",
                                    'unit_price': order_line.price_unit,
                                    'qty': order_line.product_qty,
                                    })
                            else:
                                lines.append({
                                    'option': '',
                                    'vendor_id': vendor_id.partner_id.id,
                                    'line_id': order_line.id,
                                    'message': ('Delivery Date :' + str(order_line.date_planned)),
                                    'product_id': order_line.product_id.id,
                                    'vendor_name': f"{vendor_id.partner_id.name} - {vendor_id.name}",
                                    'unit_price': order_line.price_unit,
                                    'qty': order_line.product_qty,
                                    })
                else:
                    lines.append({
                        'option': '',
                        'vendor_id': 0,
                        'line_id': 0,
                        'product_id': product_id.id,
                        'vendor_name': 0,
                        'unit_price': 0,
                        'qty': 0,
                        })

            # Only add record if we have valid vendors
            if min_date_vendor and min_prize_vendor:
                min_date_po = self.env['purchase.order'].search([
                    ('partner_id', '=', min_date_vendor.id), 
                    ('material_purchase_requisition_id', '=', tendor_id.id)
                ], limit=1)
                min_prize_po = self.env['purchase.order'].search([
                    ('partner_id', '=', min_prize_vendor.id), 
                    ('material_purchase_requisition_id', '=', tendor_id.id)
                ], limit=1)
                
                record.append({
                    'min_date_vendor': f"{min_date_vendor.name} - {min_date_po.name if min_date_po.exists() else 'Unknown'}",
                    'min_date': min_date.date().strftime("%d/%m/%Y"),
                    'product_id': product_id.id,
                    'product_name': product_id.name,
                    'description': product_lines[0].name if product_lines else '',
                    'min_prize': min_prize,
                    'min_prize_vendor': f"{min_prize_vendor.name} - {min_prize_po.name if min_prize_po.exists() else 'Unknown'}",
                    'message': ("Vendor Name: " + min_prize_vendor.name + " ,Min Prize: " + str(min_prize)),
                    'record_lines': lines,
                })

        return {
            'record_line_ids': record,
            'partner_ids': partner_ids,
            'total': total,
            'length': len(purchase_ids.ids),
            'option': option,
            'min_total_vendor': min_total_vendor,
            'min_delivery_vendor': min_delivery_vendor,
            'reqisition_name': tendor_id.name,
            'projects': projects,
        }

    def action_open_dashboard(self):
        if self.state == 'po_confirm':
            raise UserError(
                _("Purchase Order Already Confirmed for this Requisition"))
        active_id = self.env.context.get('active_id')
        return {
            'name': 'Dashboard',
            'type': 'ir.actions.client',
            'tag': 'compare_dashboard',
            'context': "{'requisition_id': active_id}",
        }

    @api.model
    def remove_line_action(self, line_id=None, active_id=None):
        lines = self.env['purchase.order.line'].search([('id', '=', line_id)])
        if lines:
            lines.unlink()
        return True

    @api.model
    def confirm_order_action(self, purchase_id, all_ids):
        purchase_order = self.env['purchase.order'].browse(int(purchase_id))
        if not purchase_order:
            raise UserError(
                _("Invalid Purchase Order. Received ID: %s") % purchase_id)
        #Check for zero-priced lines
        zero_price_lines = purchase_order.order_line.filtered(
            lambda l: l.price_unit <= 0)
        if zero_price_lines:
            product_names = ", ".join(
                zero_price_lines.mapped('product_id.display_name')
            )
            raise UserError(
                _(
                    "You cannot confirm this Purchase Order because the following "
                    "products have a unit price of 0:\n\n%s\n\n"
                    "Please remove or update these lines before confirming."
                ) % product_names
            )
        #Confirm PO
        purchase_order.button_confirm()

        #Cancle PO
        other_po = self.env['purchase.order'].browse(
            [int(pid) for pid in all_ids if int(pid) != int(purchase_id)]
        )

        cancelable_po = other_po.filtered(
            lambda po: po.state in ['draft', 'sent']
        )

        cancelable_po.button_cancel()

        #Subscribe vendor to chatter
        if (
                purchase_order.partner_id
                and purchase_order.partner_id not in purchase_order.message_partner_ids
        ):
            purchase_order.message_subscribe([purchase_order.partner_id.id])

        #Update requisition state
        purchase_order.material_purchase_requisition_id.state = 'po_confirm'
        return True

    @api.model
    def confirm_line_action(self, line_id, vendor_id, product_id, requisition_id):
        """Confirm individual product line with zero price validation"""
        # Debug: Log the received parameters
        _logger = logging.getLogger(__name__)
        _logger.info(f"Received line_id: {line_id}, vendor_id: {vendor_id}, product_id: {product_id}, requisition_id: {requisition_id}")
        
        if not line_id or line_id == 0:
            raise UserError(_(f"Invalid line ID: {line_id}. Please refresh the dashboard and try again."))
        
        line = self.env['purchase.order.line'].browse(line_id)
        
        if not line.exists():
            raise UserError(_(f"Purchase order line not found. Line ID: {line_id}. Please refresh the dashboard and try again."))
        
        # Check for zero price
        if line.price_unit == 0.0:
            # Get vendor name from vendor_id parameter to avoid accessing potentially deleted order
            vendor = self.env['res.partner'].browse(vendor_id)
            vendor_name = vendor.name if vendor.exists() else 'Unknown Vendor'
            
            # Show confirmation wizard for zero price
            return {
                'name': _('Confirm Zero Price Product'),
                'type': 'ir.actions.act_window',
                'res_model': 'rfq.line.zero.price.confirm.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_line_id': line_id,
                    'default_vendor_id': vendor_id,
                    'default_product_id': product_id,
                    'default_requisition_id': requisition_id,
                    'default_product_name': line.product_id.name,
                    'default_vendor_name': vendor_name,
                }
            }
        
        # If price is valid, proceed with confirmation
        result = self._confirm_line_with_price(line_id, vendor_id, product_id, requisition_id)
        return result
    
    @api.model
    def _confirm_line_with_price(self, line_id, vendor_id, product_id, requisition_id):
        """Helper method to confirm line with valid price"""
        line = self.env['purchase.order.line'].browse(line_id)
        
        if not line.exists():
            raise UserError(_("Purchase order line not found."))
        
        # Get vendor name from vendor_id parameter
        vendor = self.env['res.partner'].browse(vendor_id)
        vendor_name = vendor.name if vendor.exists() else 'Unknown Vendor'
        
        # Create a new PO with just this line for the confirmed product
        confirmed_po = self.env['purchase.order'].create({
            'partner_id': vendor_id,
            'material_purchase_requisition_id': requisition_id,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_qty,
                'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
                'date_planned': line.date_planned,
            })],
            'state': 'draft',
        })
        
        # Confirm the new purchase order
        confirmed_po._add_supplier_to_product()
        if confirmed_po._approval_allowed():
            confirmed_po.button_approve()
        else:
            confirmed_po.write({'state': 'to approve'})
        
        # Remove the line from original RFQ (optional - keep for reference)
        # line.unlink()
        
        # Log the confirmation
        confirmed_po.message_post(
            body=_("Product %s confirmed from vendor %s at price %s") % (
                line.product_id.name,
                vendor_name,
                line.price_unit
            )
        )
        
        return True


class PurchaseRequisitionHistory(models.Model):
    _name = 'purchase.requisition.history'
    _description = 'Purchase Requisition State History'
    _order = 'date desc, id desc'
    
    requisition_id = fields.Many2one('material.purchase.requisition', string='Requisition', required=True, ondelete='cascade')
    from_state = fields.Char(string='From State')
    to_state = fields.Char(string='To State', required=True)
    state_label = fields.Char(string='State Label', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now)
    notes = fields.Text(string='Notes/Comments')
    ip_address = fields.Char(string='IP Address')
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.state_label} by {record.user_id.name} on {record.date.strftime('%Y-%m-%d %H:%M')}"
            result.append((record.id, name))
        return result


class RejectReasonWizard(models.TransientModel):
    _name = 'reject.reason.wizard'
    _description = 'Rejection Reason Wizard'
    
    requisition_id = fields.Many2one('material.purchase.requisition', string='Requisition')
    reason = fields.Text(string='Rejection Reason', required=True)
    
    def action_confirm_reject(self):
        """Confirm rejection with reason"""
        if self.requisition_id:
            self.requisition_id.reject_with_reason(self.reason)
        return {'type': 'ir.actions.act_window_close'}
