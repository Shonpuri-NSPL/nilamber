# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprWeather(models.Model):
    _name = 'dpr.weather'
    _description = 'Weather Conditions'
    _rec_name = 'weather_condition'

    report_id = fields.Many2one(
        'dpr.report',
        string='DPR Report',
        required=True,
        ondelete='cascade'
    )
    weather_condition = fields.Selection([
        ('sunny', 'Sunny'),
        ('cloudy', 'Cloudy'),
        ('partly_cloudy', 'Partly Cloudy'),
        ('rainy', 'Rainy'),
        ('stormy', 'Stormy'),
        ('foggy', 'Foggy'),
        ('windy', 'Windy'),
        ('snowy', 'Snowy'),
        ('hot', 'Hot'),
        ('humid', 'Humid')
    ], string='Weather Condition',
        required=True,
        default='sunny'
    )
    temperature = fields.Float(
        string='Temperature (°C)'
    )
    humidity = fields.Float(
        string='Humidity (%)'
    )
    wind_speed = fields.Float(
        string='Wind Speed (km/h)'
    )
    rainfall_mm = fields.Float(
        string='Rainfall (mm)'
    )
    working_hours_lost = fields.Float(
        string='Working Hours Lost',
        default=0.0
    )
    weather_impact = fields.Text(
        string='Impact on Work'
    )
    recorded_at = fields.Datetime(
        string='Recorded At',
        default=fields.Datetime.now
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.constrains('humidity', 'temperature')
    def _check_values(self):
        for weather in self:
            if weather.humidity and (weather.humidity < 0 or weather.humidity > 100):
                raise ValidationError(_('Humidity must be between 0 and 100!'))
