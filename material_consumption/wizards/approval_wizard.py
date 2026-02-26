# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ApprovalWizard(models.TransientModel):
    _name = 'material.consumption.approval.wizard'
    _description = 'Material Request Approval Wizard'

    request_id = fields.Many2one(
        'material.request',
        string='Material Request',
        required=True
    )
    action = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], string='Action', required=True)
    comments = fields.Text(string='Comments')

    def action_confirm(self):
        """Confirm the approval/rejection action"""
        self.ensure_one()
        if self.action == 'approve':
            self.request_id.action_approve(self.comments)
        elif self.action == 'reject':
            self.request_id.action_reject(self.comments)
        return {'type': 'ir.actions.act_window_close'}
