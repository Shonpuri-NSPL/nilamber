# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DprConfig(models.Model):
    _name = 'dpr.config'
    _description = 'DPR Configuration Settings'
    _rec_name = 'config_name'

    config_name = fields.Char(
        string='Configuration Name',
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    default_hourly_rate_skilled = fields.Float(
        string='Default Skilled Labor Rate',
        default=500.0
    )
    default_hourly_rate_unskilled = fields.Float(
        string='Default Unskilled Labor Rate',
        default=350.0
    )
    default_hourly_rate_supervisor = fields.Float(
        string='Default Supervisor Rate',
        default=800.0
    )
    require_approval = fields.Boolean(
        string='Require DPR Approval',
        default=True
    )
    auto_submit_time = fields.Float(
        string='Auto Submit Time (Hours)',
        help='Hours after which draft reports are auto-submitted',
        default=24.0
    )
    photo_max_size = fields.Integer(
        string='Max Photo Size (MB)',
        default=5
    )
    enable_gps_verification = fields.Boolean(
        string='Enable GPS Verification',
        default=True
    )
    enable_offline_sync = fields.Boolean(
        string='Enable Offline Sync',
        default=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.model
    def get_config(self):
        """Get active configuration or create default"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({
                'config_name': 'Default Configuration',
                'active': True
            })
        return config
