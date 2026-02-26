# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprPhoto(models.Model):
    _name = 'dpr.photo'
    _description = 'Site Progress Photos'
    _rec_name = 'photo_name'
    _order = 'captured_time desc'

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
    photo = fields.Binary(
        string='Photo',
        required=True
    )
    photo_url = fields.Char(
        string='Photo URL'
    )
    photo_name = fields.Char(
        string='Photo Description',
        required=True
    )
    photo_type = fields.Selection([
        ('progress', 'Progress'),
        ('safety', 'Safety'),
        ('issue', 'Issue'),
        ('delivery', 'Delivery'),
        ('completion', 'Completion'),
        ('other', 'Other')
    ], string='Photo Type',
        default='progress'
    )
    latitude = fields.Float(
        string='GPS Latitude',
        digits=(10, 7)
    )
    longitude = fields.Float(
        string='GPS Longitude',
        digits=(10, 7)
    )
    captured_by_id = fields.Many2one(
        'dpr.employee',
        string='Captured By'
    )
    captured_time = fields.Datetime(
        string='Captured Time',
        default=fields.Datetime.now
    )
    notes = fields.Text(
        string='Notes'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for photo in self:
            if photo.latitude and (photo.latitude < -90 or photo.latitude > 90):
                raise ValidationError(_('Latitude must be between -90 and 90!'))
            if photo.longitude and (photo.longitude < -180 or photo.longitude > 180):
                raise ValidationError(_('Longitude must be between -180 and 180!'))
