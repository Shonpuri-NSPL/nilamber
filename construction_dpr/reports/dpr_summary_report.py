# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DprSummaryReport(models.AbstractModel):
    _name = 'report.construction_dpr.dpr_summary_report'
    _description = 'DPR Summary Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['dpr.report'].browse(docids)
        projects = set(docs.mapped('project_id'))

        return {
            'docs': docs,
            'projects': projects,
            'data': data,
        }


class DprProgressReport(models.AbstractModel):
    _name = 'report.construction_dpr.dpr_progress_report'
    _description = 'DPR Progress Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['dpr.report'].browse(docids)
        return {
            'docs': docs,
            'data': data,
        }
