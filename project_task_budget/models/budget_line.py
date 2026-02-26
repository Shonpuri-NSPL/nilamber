from odoo import fields, models


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    def action_open_budget_entries(self):
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        all_plan = project_plan + other_plans

        project = self.env['project.project'].search([('account_id', '=', self.account_id.id)])
        budget_analytic_lines = [self.id]
        budget_analytic_ids = [self.budget_analytic_id.id]
        account_ids = False
        task = self.env['project.task'].search([('analytic_account_id', '=', self.account_id.id)])
        if project:
            project_tasks = project.task_ids
            account_ids = [project.account_id.id]

            for task in project_tasks:
                if task.is_create_budget:
                    if task.analytic_account_id:
                        account_ids.append(task.analytic_account_id.id)

                    child_account_ids = task.child_ids.filtered(lambda l: l.is_create_budget).mapped(
                        'analytic_account_id.id')
                    account_ids.extend(child_account_ids)
                    account_ids = list(set(account_ids))

            budget_analytic_lines = self.env['budget.line'].search([('account_id', 'in', account_ids)])
            budget_analytic_ids = budget_analytic_lines and budget_analytic_lines.mapped('budget_analytic_id.id') or [self.budget_analytic_id.id]
            budget_analytic_lines = budget_analytic_lines and budget_analytic_lines.mapped('id') or [self.id]
        elif task and task.is_create_budget and task.analytic_account_id:
            account_ids = [task.analytic_account_id.id]
            child_account_ids = task.child_ids.filtered(lambda l: l.is_create_budget).mapped(
                'analytic_account_id.id')
            account_ids.extend(child_account_ids)
            budget_analytic_lines = self.env['budget.line'].search([('account_id', 'in', account_ids)])
            budget_analytic_ids = budget_analytic_lines and budget_analytic_lines.mapped('budget_analytic_id.id') or [
                self.budget_analytic_id.id]
            budget_analytic_lines = budget_analytic_lines and budget_analytic_lines.mapped('id') or [self.id]
        domain = [('budget_analytic_id', 'in', budget_analytic_ids), ('budget_line_id', 'in', budget_analytic_lines)]

        for plan in all_plan:
            fname = plan._column_name()
            account_ids = account_ids and account_ids or self[fname].ids
            if self[fname]:
                domain += [(fname, 'in', account_ids)]
        action = self.env['ir.actions.act_window']._for_xml_id('account_budget.budget_report_action')
        action['domain'] = domain
        return action