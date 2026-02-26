from odoo import models, fields, api


class RateAnalysis(models.Model):
    _name = 'rate.analysis'
    _description = 'Analysis of Rates'
    _rec_name = 'analysis_code'

    analysis_code = fields.Char(string="Analysis Code", required=True)
    material_name = fields.Char(string="Material Name", required=True)
    project_id = fields.Many2one('project.project', string='Project')
    rate_analysis_line_ids = fields.One2many(
        'rate.analysis.line',
        'analysis_id',
        string="Rate Breakup Lines"
    )


class RateAnalysisLine(models.Model):
    _name = 'rate.analysis.line'
    _description = 'Rate Analysis Line'

    analysis_id = fields.Many2one(
        'rate.analysis',
        string="Rate Analysis",
        ondelete='cascade',
        required=True
    )
    description = fields.Char(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    rate = fields.Float(string="Rate")
    unit = fields.Many2one('uom.uom', string='Unit')
    amount = fields.Float(
        string="Amount",
        compute="_compute_amount",
        store=True
    )

    @api.depends('quantity', 'rate')
    def _compute_amount(self):
        for line in self:
            if line.quantity and line.rate:
                line.amount = line.quantity * line.rate
            else:
                line.amount = line.rate
