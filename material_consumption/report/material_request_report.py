from odoo import models, api

class MaterialRequestReport(models.AbstractModel):
    _name = 'report.material_consumption.material_request_report'
    _description = 'Material Request Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['material.request'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'material.request',
            'docs': docs,
            'data': data,
        }
