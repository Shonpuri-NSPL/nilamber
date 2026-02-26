from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    project_id = fields.Many2one('project.project', string='Project')