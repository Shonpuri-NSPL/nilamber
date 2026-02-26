# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprApprovalWizard(models.TransientModel):
    _name = 'dpr.approval.wizard'
    _description = 'DPR Approval Wizard'

    report_ids = fields.Many2many(
        'dpr.report',
        string='Reports to Approve'
    )
    action_type = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject')
    ], string='Action',
        required=True,
        default='approve'
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=False
    )
    approve_all = fields.Boolean(
        string='Approve All Pending Reports',
        default=False
    )

    def action_apply(self):
        """Apply approval or rejection"""
        self.ensure_one()

        if self.approve_all:
            # Approve all pending reports
            reports = self.env['dpr.report'].search([('state', '=', 'submitted')])
        else:
            reports = self.report_ids

        if not reports:
            raise ValidationError(_('No reports selected for approval/rejection.'))

        if self.action_type == 'approve':
            for report in reports:
                if report.state == 'submitted':
                    report.action_approve()
            message = _('Reports approved successfully')
        else:
            if not self.rejection_reason:
                raise ValidationError(_('Rejection reason is required.'))
            for report in reports:
                if report.state == 'submitted':
                    report.action_reject(self.rejection_reason)
            message = _('Reports rejected successfully')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('DPR Approval'),
                'message': message,
                'sticky': False,
                'type': 'success',
            }
        }

    @api.model
    def default_get(self, fields):
        """Get default values"""
        res = super().default_get(fields)
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            res['report_ids'] = [(6, 0, active_ids)]
        return res
