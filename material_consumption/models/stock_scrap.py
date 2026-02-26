from odoo import models, fields

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    project_id = fields.Many2one('project.project', required=True)