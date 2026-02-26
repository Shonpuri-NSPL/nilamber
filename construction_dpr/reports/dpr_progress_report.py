# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DprProgressReport(models.AbstractModel):
    _name = 'report.construction_dpr.dpr_progress'
    _description = 'DPR Progress Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'dpr.report',
            'docs': self.env['dpr.report'].browse(docids),
            'data': data,
        }


class DprLaborReport(models.AbstractModel):
    _name = 'report.construction_dpr.dpr_labor'
    _description = 'DPR Labor Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'dpr.report',
            'docs': self.env['dpr.report'].browse(docids),
            'data': data,
        }


class DprMaterialReport(models.AbstractModel):
    _name = 'report.construction_dpr.dpr_material'
    _description = 'DPR Material Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'dpr.report',
            'docs': self.env['dpr.report'].browse(docids),
            'data': data,
        }


class DprEquipmentReport(models.AbstractModel):
    _name = 'report.construction_dpr.dpr_equipment'
    _description = 'DPR Equipment Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'dpr.report',
            'docs': self.env['dpr.report'].browse(docids),
            'data': data,
        }
