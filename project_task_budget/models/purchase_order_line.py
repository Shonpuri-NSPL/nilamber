from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', 'order_id.partner_id', 'order_id.project_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        ProjectProject = self.env['project.project']
        for line in self:
            project_id = line.env.context.get('project_id')
            project = ProjectProject.browse(project_id) if project_id else line.order_id.project_id
            if line.display_type or not project:
                continue
            if line.analytic_distribution:
                if any(task.is_create_budget for task in project.task_ids):
                    account_ids = []
                    for task in project.task_ids:
                        if task.is_create_budget:
                            if task.analytic_account_id:
                                account_ids.append(task.analytic_account_id.id)

                            child_account_ids = task.child_ids.filtered(lambda l: l.is_create_budget).mapped(
                                'analytic_account_id.id')
                            account_ids.extend(child_account_ids)
                            account_ids = list(set(account_ids))
                    account_id = account_ids and min(account_ids) or []
                    if account_id:
                        task_analytic = self.env['account.analytic.account'].browse(account_id)
                        if task_analytic:
                            percentage = next(iter(line.analytic_distribution.values()))

                            line.analytic_distribution = {
                                str(task_analytic.id): percentage
                            }
                else:
                    applied_root_plans = self.env['account.analytic.account'].browse(
                    list({int(account_id) for ids in line.analytic_distribution for account_id in ids.split(",")})
                    ).root_plan_id
                    if accounts_to_add := project._get_analytic_accounts().filtered(
                            lambda account: account.root_plan_id not in applied_root_plans
                    ):
                        line.analytic_distribution = {
                            f"{account_ids},{','.join(map(str, accounts_to_add.ids))}": percentage
                            for account_ids, percentage in line.analytic_distribution.items()
                        }
            else:
                line.analytic_distribution = project._get_analytic_distribution()
