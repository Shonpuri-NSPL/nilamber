# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApprovalLevelConfiguration(models.Model):
    _name = 'approval.level.configuration'
    _description = 'Approval Level Configuration'
    _order = 'sequence asc'

    name = fields.Char(string='Level Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10, required=True)
    level_number = fields.Integer(string='Level Number', required=True, help='The approval level number (1, 2, 3, etc.)')
    description = fields.Text(string='Description')
    
    # Approval Type - can be based on amount or fixed
    approval_type = fields.Selection([
        ('amount', 'Based on Amount'),
        ('fixed', 'Fixed Level')
    ], string='Approval Type', default='fixed', required=True)
    
    # Amount thresholds (for amount-based approval)
    min_amount = fields.Monetary(string='Minimum Amount', currency_field='currency_id')
    max_amount = fields.Monetary(string='Maximum Amount', currency_field='currency_id', help='Leave empty for unlimited')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Required approver groups
    approver_group_ids = fields.Many2many('res.groups', string='Approver Groups', 
                                          help='Users in these groups can approve at this level')
    
    # Is active
    active = fields.Boolean(string='Active', default=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.constrains('sequence', 'level_number', 'company_id')
    def _check_unique_level(self):
        """Ensure unique level number per company"""
        for record in self:
            existing = self.search([
                ('id', '!=', record.id),
                ('level_number', '=', record.level_number),
                ('company_id', '=', record.company_id.id)
            ])
            if existing:
                raise ValidationError(_('Level number %d already exists for this company.') % record.level_number)
    
    @api.constrains('min_amount', 'max_amount')
    def _check_amount_range(self):
        """Validate amount range"""
        for record in self:
            if record.approval_type == 'amount':
                if record.min_amount and record.max_amount and record.min_amount > record.max_amount:
                    raise ValidationError(_('Minimum amount cannot be greater than maximum amount.'))
    
    def name_get(self):
        result = []
        for record in self:
            name = '%s (Level %d)' % (record.name, record.level_number)
            result.append((record.id, name))
        return result


class MaterialRequestApprovalLevel(models.Model):
    _name = 'material.request.approval.level'
    _description = 'Material Request Approval Level'
    _order = 'level_number asc'

    configuration_id = fields.Many2one('approval.level.configuration', string='Configuration', required=True)
    level_number = fields.Integer(string='Level Number', related='configuration_id.level_number', store=True)
    request_id = fields.Many2one('material.request', string='Material Request', required=True, ondelete='cascade')
    approver_id = fields.Many2one('res.users', string='Approver', default=lambda self: self.env.user)
    approved_date = fields.Datetime(string='Approved Date')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending')
    comments = fields.Text(string='Comments')
    
    def action_approve(self):
        """Approve this level"""
        for record in self:
            record.write({
                'state': 'approved',
                'approved_date': fields.Datetime.now()
            })
            # Check if all levels are approved
            record.request_id._check_all_approval_levels()
    
    def action_reject(self):
        """Reject this level"""
        for record in self:
            record.write({
                'state': 'rejected'
            })
            # Update request state to rejected
            record.request_id.write({'state': 'rejected'})
    
    def name_get(self):
        result = []
        for record in self:
            name = '%s - Level %d - %s' % (record.request_id.name, record.level_number, record.state)
            result.append((record.id, name))
        return result
