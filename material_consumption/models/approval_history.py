# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ApprovalHistory(models.Model):
    _name = 'material.approval.history'
    _description = 'Material Consumption Approval History'
    _order = 'create_date desc'
    _rec_name = 'request_id'
    
    request_id = fields.Many2one('material.request', string='Material Request', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Approver', required=True, default=lambda self: self.env.user)
    action = fields.Selection([
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('issue', 'Issued'),
        ('cancel', 'Cancelled')
    ], string='Action', required=True)
    approval_level = fields.Integer(string='Approval Level')
    comments = fields.Text(string='Comments')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    
    def name_get(self):
        result = []
        for record in self:
            name = '%s - %s' % (record.request_id.name, record.action)
            result.append((record.id, name))
        return result


