from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    prepared_by_name = fields.Char(string="Prepared By")
    approved_by_name = fields.Char(string="Approved By")

    def button_confirm(self):
        for order in self:
            for line in order.order_line:
                if not line.analytic_distribution and order.project_id:
                    raise ValidationError(_("Please configure analytic distribution on purchase line!!"))
                if line.analytic_distribution and not order.project_id:
                    raise ValidationError(
                        _("You have configured analytic distribution so please add related project for this Purchase Order!!"))
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            for line in order.order_line:
                distribution = line.analytic_distribution or {}
                distribution = {str(k): v for k, v in distribution.items()}
                project_distribution = order.project_id._get_analytic_distribution()
                project_distribution = {str(k): v for k, v in project_distribution.items()}
                distribution.update(project_distribution)
                for analytic_id_str, percentage in list(distribution.items()):
                    analytic_id = int(analytic_id_str)
                    task = self.env['project.task'].search([
                        ('analytic_account_id', '=', analytic_id),
                        ('is_create_budget', '=', True)
                    ], limit=1)
                    if task:
                        parent_task = task.parent_id
                        while parent_task:
                            if parent_task.is_create_budget and parent_task.analytic_account_id:
                                parent_analytic_id = str(parent_task.analytic_account_id.id)
                                if parent_analytic_id not in distribution:
                                    distribution[parent_analytic_id] = percentage
                                else:
                                    distribution[parent_analytic_id] += percentage
                            parent_task = parent_task.parent_id
                line.analytic_distribution = distribution
        return res