# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class MaterialRequest(models.Model):
    _name = 'material.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Material Request'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    request_date = fields.Date(string='Request Date', required=True, default=fields.Date.context_today)
    requested_by = fields.Many2one('res.users', string='Requested By', required=True,
                                   default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')

    # Request Type
    request_type = fields.Selection([
        ('project', 'Project'),
    ], string='Request Type', required=True, default='project')

    # Project Reference
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')

    # Customer Reference
    partner_id = fields.Many2one('res.partner', string='Customer')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    # Lines
    line_ids = fields.One2many('material.request.line', 'request_id', string='Material Lines')

    # Approval History
    approval_history_ids = fields.One2many('material.approval.history', 'request_id', string='Approval History')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', track_visibility='onchange')

    # Approval Level Configuration (automatically set based on amount)
    approval_level_config_id = fields.Many2one('approval.level.configuration', string='Approval Configuration',
                                               domain="[('company_id', '=', company_id), ('active', '=', True)]",
                                               help="Select the approval configuration to use. Leave empty to auto-select based on amount.",
                                               readonly=True)
    current_approval_level = fields.Integer(string='Current Level', default=1, readonly=True)
    required_approval_level = fields.Integer(string='Required Level', default=1,
                                             help="Required approval level for this request. Will be set based on configuration or amount.",
                                             readonly=True)

    # Approval Levels (for multi-level approval)
    approval_level_ids = fields.One2many('material.request.approval.level', 'request_id', string='Approval Levels')

    # Billing Information
    is_billable = fields.Boolean(string='Billable', default=False)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    pricing_type = fields.Selection([
        ('free', 'Free'),
        ('billable', 'Billable')
    ], string='Pricing Type', default='free')

    # Stock Information
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', readonly=True)

    # Notes
    notes = fields.Text(string='Notes')

    # Total Amount
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', store=True)

    # Priority
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1')

    # Computed field to check if current user can approve
    can_current_user_approve = fields.Boolean(
        string='Can Current User Approve',
        compute='_compute_can_current_user_approve',
        compute_sudo=True
    )
    dest_location_id = fields.Many2one('stock.location', string='Destination Location')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    @api.onchange('is_billable')
    def _onchange_is_billable(self):
        """Clear billing fields when is_billable is unchecked"""
        if not self.is_billable:
            self.pricing_type = 'free'
            self.sale_order_id = False

    @api.onchange('approval_level_config_id')
    def _onchange_approval_level_config_id(self):
        """When user selects an approval configuration, automatically set required_approval_level"""
        if self.approval_level_config_id:
            self.required_approval_level = self.approval_level_config_id.level_number

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'material.request'
                ) or _('New')
        return super().create(vals_list)

    def write(self, vals):
        for record in self:
            if record.state in ('approved', 'issued', 'rejected', 'cancelled'):
                # Allow state changes and some specific fields for internal operations
                allowed_fields = {'state', 'current_approval_level', 'required_approval_level', 'picking_id',
                                  'approval_level_config_id'}
                if not set(vals.keys()).issubset(allowed_fields):
                    raise UserError(_('You cannot modify a material request that has been %s.') % record.state)
        return super(MaterialRequest, self).write(vals)

    @api.depends('line_ids.subtotal', 'current_approval_level', 'required_approval_level', 'approval_level_config_id')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(line.subtotal for line in record.line_ids)

    @api.depends('current_approval_level', 'approval_level_config_id')
    def _compute_can_current_user_approve(self):
        """Check if current user can approve at the current approval level"""
        for record in self:
            if record.state != 'submitted':
                record.can_current_user_approve = False
                continue

            level_config = record._get_level_config(record.current_approval_level)
            if not level_config:
                record.can_current_user_approve = False
                continue

            # If no approver groups defined, allow any user to approve
            if not level_config.approver_group_ids:
                record.can_current_user_approve = True
                continue

            # Check if current user is in any of the approver groups
            user_groups = self.env.user.group_ids
            has_permission = any(g.id in level_config.approver_group_ids.ids for g in user_groups)
            record.can_current_user_approve = has_permission

    def _get_approval_config_for_amount(self, amount):
        """Get approval configuration based on amount"""
        self.ensure_one()
        # If amount is zero, return level 1 configuration
        if amount <= 0:
            return self.env['approval.level.configuration'].sudo().search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True),
                ('level_number', '=', 1),
            ], limit=1)

        # Search for amount-based configuration matching the total amount
        # First try to find a configuration where the amount falls within the range
        configs = self.env['approval.level.configuration'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
            ('approval_type', '=', 'amount'),
            ('min_amount', '<=', amount),
            '|',
            ('max_amount', '>=', amount),
            ('max_amount', '=', False)
        ], order='level_number asc')

        # Return the configuration with highest level_number that matches
        if configs:
            return configs[-1]

        # If no amount-based config found, return level 1
        return self.env['approval.level.configuration'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
            ('level_number', '=', 1),
        ], limit=1)

    def action_submit(self):
        """Submit the material request for approval - automatically determines approval level based on amount"""
        for record in self:
            if not record.line_ids:
                raise UserError(_('Please add at least one material line before submitting.'))

            # Validate that tracked products have lot numbers
            for line in record.line_ids:
                if line.product_id.tracking != 'none' and not line.lot_id:
                    raise UserError(
                        _('Lot/Serial number is required for product "%s" in line %s')
                        % (line.product_id.name, line.sequence)
                    )

            # Auto-assign approval configuration based on amount
            config = record._get_approval_config_for_amount(record.total_amount)
            if config:
                record.write({
                    'approval_level_config_id': config.id,
                    'required_approval_level': config.level_number,
                    'current_approval_level': 1,
                })
            else:
                # No configuration found, use default level 1
                record.write({
                    'required_approval_level': 1,
                    'current_approval_level': 1,
                })

            record.state = 'submitted'

            # Post to chatter
            record.message_post(
                body=_(
                    'Material Request submitted for approval. Required approval level: %s') % record.required_approval_level,
                subject=_('Material Request Submitted')
            )

            # Create approval history
            record.approval_history_ids.create({
                'request_id': record.id,
                'action': 'submit',
                'approval_level': record.current_approval_level
            })

    def _get_level_config(self, level_number):
        """Get approval level configuration for a specific level"""
        self.ensure_one()
        return self.env['approval.level.configuration'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('level_number', '=', level_number),
            ('active', '=', True)
        ], limit=1)

    def action_approve(self):
        """Approve the material request - automatically proceeds to next level or approves if last level"""
        for record in self:
            # Check if user has permission to approve at this level
            level_config = record._get_level_config(record.current_approval_level)
            if level_config and level_config.approver_group_ids:
                user_groups = self.env.user.group_ids
                has_permission = any(g.id in level_config.approver_group_ids.ids for g in user_groups)
                if not has_permission:
                    raise UserError(
                        _('You do not have permission to approve at level %s. Please contact an approver from the designated group.') % record.current_approval_level)

            # Increment current level
            record.current_approval_level += 1

            # Check if we reached the required approval level
            if record.current_approval_level > record.required_approval_level:
                record.state = 'approved'
                record.current_approval_level = record.required_approval_level
                # Post approval message
                record.message_post(
                    body=_('Material Request has been fully approved at level %s') % record.required_approval_level,
                    subject=_('Material Request Approved')
                )
            else:
                # Post level approval message
                record.message_post(
                    body=_('Material Request approved at level %s. Waiting for level %s approval.') % (
                        record.current_approval_level - 1, record.required_approval_level),
                    subject=_('Level Approval')
                )

            # Create approval history
            record.approval_history_ids.create({
                'request_id': record.id,
                'user_id': self.env.user.id,
                'action': 'approve',
                'approval_level': record.current_approval_level
            })

    def action_reject(self):
        """Reject the material request"""
        for record in self:
            record.state = 'rejected'

            # Post rejection message to chatter
            record.message_post(
                body=_('Material Request has been rejected at approval level %s') % record.current_approval_level,
                subject=_('Material Request Rejected')
            )

            # Create approval history
            record.approval_history_ids.create({
                'request_id': record.id,
                'user_id': self.env.user.id,
                'action': 'reject',
                'approval_level': record.current_approval_level
            })

    def action_issue_material(self):
        """Issue materials from stock"""
        StockMoveLine = self.env['stock.move.line']
        for record in self:
            if record.state != 'approved':
                raise UserError(_('Material Request must be approved before issuing materials.'))

            # Get the first line's location as the picking's source location
            first_line = record.line_ids[0] if record.line_ids else False
            source_location_id = first_line.location_id.id if first_line and first_line.location_id else self.env.ref(
                'stock.stock_location_stock').id

            picking_vals = {
                'partner_id': False,
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'location_id': source_location_id,
                'location_dest_id': record.dest_location_id.id,
                'origin': record.name,
                'request_id': record.id,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            for line in record.line_ids:
                # Use the line's location if available, otherwise use the picking's location
                move_location_id = line.location_id.id if line.location_id else source_location_id

                move = self.env['stock.move'].create({
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'location_id': move_location_id,
                    'location_dest_id': picking.location_dest_id.id,
                    'description_picking': line.product_id.display_name,
                })

                move._action_confirm()

                move._action_assign()

                # LOT HANDLING
                if line.product_id.tracking != 'none':
                    if not line.lot_id:
                        raise UserError(
                            _('Lot/Serial number required for product %s')
                            % line.product_id.display_name
                        )

                    StockMoveLine.create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.uom_id.id,
                        'qty_done': line.quantity,
                        'location_id': move_location_id,
                        'location_dest_id': picking.location_dest_id.id,
                        'lot_id': line.lot_id.id,
                    })
                else:
                    StockMoveLine.create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.uom_id.id,
                        'qty_done': line.quantity,
                        'location_id': move_location_id,
                        'location_dest_id': picking.location_dest_id.id,
                    })

            # VALIDATE PICKING
            picking.button_validate()

            record.picking_id = picking.id
            record.state = 'issued'

            # Post issuance message to chatter
            record.message_post(
                body=_('Materials have been issued. Stock Picking: %s') % picking.name,
                subject=_('Materials Issued')
            )

    def action_cancel(self):
        """Cancel the material request"""
        for record in self:
            if record.state == 'issued':
                raise UserError(_('Cannot cancel a request that has been issued.'))
            record.state = 'cancelled'

            # Post cancellation message to chatter
            record.message_post(
                body=_('Material Request has been cancelled'),
                subject=_('Material Request Cancelled')
            )

    def action_draft(self):
        """Reset to draft - approval configuration will be recalculated on next submit"""
        for record in self:
            record.state = 'draft'
            record.current_approval_level = 1
            record.required_approval_level = 1
            record.approval_level_config_id = False

            # Post reset to draft message to chatter
            record.message_post(
                body=_('Material Request has been reset to draft'),
                subject=_('Reset to Draft')
            )

    def action_view_picking(self):
        pass

    def action_print_report(self):
        """Print the material request report"""
        self.ensure_one()
        return self.env.ref('material_consumption.action_material_request_report').report_action(self)

