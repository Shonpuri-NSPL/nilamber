import json
from collections import defaultdict
from odoo import fields, models, api, _
from datetime import datetime


class Project(models.Model):
    _inherit = "project.project"

    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget Analytic',
        ondelete='cascade',
        index=True,
    )
    sequence_code = fields.Char("Sequence", default=lambda self: _('New'))
    budget_amount = fields.Float("Budget Amount")
    budget_type = fields.Selection([
        ('expense', 'Expense'),
    ], string="Budget Type", default="expense")
    is_create_budget = fields.Boolean("Want to Create Budget??")
    word_of_budget_amount = fields.Char("Budget amount in word", compute='_compute_word_of_budget_amount', store=True)
    rate_analysis_count = fields.Integer(
        string='Rate Analysis Count',
        compute='_compute_rate_analysis_count'
    )

    def _compute_rate_analysis_count(self):
        for project in self:
            project.rate_analysis_count = self.env['rate.analysis'].search_count([
                ('project_id', '=', project.id)
            ])

    def action_view_rate_analysis(self):
        self.ensure_one()
        return {
            'name': _('Rate Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'rate.analysis',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
            },
        }

    @api.depends('budget_amount')
    def _compute_word_of_budget_amount(self):
        for record in self:
            if record.budget_amount:
                record.word_of_budget_amount = self._amount_to_text_indian(record.budget_amount)
            else:
                record.word_of_budget_amount = False

    def _amount_to_text_indian(self, amount):
        """Convert amount to Indian numbering system (Crore, Lakh)"""

        # Handle decimal part
        amount_str = str(amount).replace(',', '')
        if '.' in amount_str:
            integer_part = int(float(amount_str))
            decimal_part = str(amount).split('.')[1] if '.' in str(amount) else ''
        else:
            integer_part = int(float(amount))
            decimal_part = ''

        if integer_part == 0:
            return 'Zero Rupees'

        # Number to words mapping
        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
        teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
                 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']

        def convert_two_digits(n):
            """Convert numbers 0-99 to words"""
            if n == 0:
                return ''
            elif n < 10:
                return ones[n]
            elif n < 20:
                return teens[n - 10]
            else:
                result = tens[n // 10]
                if n % 10 != 0:
                    result += ' ' + ones[n % 10]
                return result

        # Break down into Indian numbering system
        crore = integer_part // 10000000  # 1 Crore = 1,00,00,000
        remaining = integer_part % 10000000

        lakh = remaining // 100000  # 1 Lakh = 1,00,000
        remaining = remaining % 100000

        thousand = remaining // 1000  # 1 Thousand = 1,000
        remaining = remaining % 1000

        hundred = remaining // 100
        tens_ones = remaining % 100

        result = []

        # Build the words
        if crore > 0:
            # Handle crores recursively for large numbers
            if crore >= 100:
                result.append(self._amount_to_text_indian(crore).replace(' Rupees', '') + ' Crore')
            else:
                crore_words = convert_two_digits(crore)
                result.append(crore_words + ' Crore')

        if lakh > 0:
            result.append(convert_two_digits(lakh) + ' Lakh')

        if thousand > 0:
            result.append(convert_two_digits(thousand) + ' Thousand')

        if hundred > 0:
            result.append(ones[hundred] + ' Hundred')

        if tens_ones > 0:
            result.append(convert_two_digits(tens_ones))

        # Join all parts
        words = ' '.join(result)

        # Add currency name
        currency_name = self.company_id.currency_id.name or 'Rupees'
        words += ' ' + currency_name

        # Add decimal part (paise)
        if decimal_part:
            decimal_int = int(decimal_part[:2].ljust(2, '0'))
            if decimal_int > 0:
                words += ' And ' + convert_two_digits(decimal_int) + ' Paise'

        return words

    @api.onchange('project_expense')
    def get_budget(self):
        self.budget_amount = self.project_expense or 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence_code', 'New') == 'New':
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code('sequence.project.code') or _('New')

        res = super(Project, self).create(vals_list)

        for rec in res:
            # dpr_project = self.env['dpr.project'].create({
            #     'start_date': datetime.today(),
            #     'company_id' : rec.company_id.id,
            # })
            budget_analytic_id = False
            existing_budget_analytic_id = self.env['budget.analytic'].search([
                ('name', '=', rec.sequence_code + ' : ' + rec.name)
            ])
            existing_analytic_account = self.env['account.analytic.account'].search([
                ('name', '=', rec.sequence_code)
            ])
            account_id = False
            project_account_id = rec.account_id and rec.account_id.id or False
            if not existing_analytic_account and rec.is_create_budget:
                account_id = self.env['account.analytic.account'].create({
                    'name': rec.sequence_code,
                    'code': rec.name,
                    'partner_id': rec.partner_id and rec.partner_id.id or False,
                    'company_id': self.env.company.id,
                    'plan_id': self.env.ref('analytic.analytic_plan_projects').id
                })

            if not existing_budget_analytic_id and rec.is_create_budget:
                budget_analytic_id = self.env['budget.analytic'].create({
                    'name': rec.sequence_code + ' : ' + rec.name,
                    'user_id': self.env.user.id,
                    'budget_type': rec.budget_type,
                    'date_from': rec.date_start,
                    'date_to': rec.date,
                    'parent_id': False,
                    'company_id': self.env.company.id,
                })
                budget_analytic_id.action_budget_confirm()

                if account_id:
                    project_account_id = account_id.id
                self.env['budget.line'].create({
                    'budget_analytic_id': budget_analytic_id and budget_analytic_id.id or False,
                    'account_id': project_account_id or False,
                    'budget_amount': rec.budget_amount,
                })

            if budget_analytic_id:
                rec.write({
                    'account_id': project_account_id,
                    'budget_analytic_id': budget_analytic_id.id,
                    'company_id': self.env.company.id,
                })
                # dpr_project.write({
                #     'company_id' : rec.company_id.id,
                #     'analytic_account_id' :  project_account_id,
                #     'budget_analytic_id': budget_analytic_id.id,
                #     'estimated_budget'    : rec.budget_amount,
                # })

        return res

    def write(self, vals):
        res = super(Project, self).write(vals)
        if 'budget_amount' in vals:
            for rec in self:
                if rec.budget_analytic_id and rec.account_id:
                    budget_line = self.env['budget.line'].search([
                        ('budget_analytic_id', '=', rec.budget_analytic_id.id),
                        ('account_id', '=', rec.account_id.id)
                    ], limit=1)
                    if budget_line:
                        budget_line.write({
                            'budget_amount': vals['budget_amount']
                        })
        return res

    def _get_budget_items(self, with_action=True):
        self.ensure_one()
        if not self.account_id:
            return
        project_tasks = self.task_ids
        account_ids = [self.account_id.id]

        def collect_task_and_subtask_accounts(task):
            task_accounts = []
            if task.is_create_budget and task.analytic_account_id:
                task_accounts.append(task.analytic_account_id.id)

            for child_task in task.child_ids:
                task_accounts.extend(collect_task_and_subtask_accounts(child_task))

            return task_accounts

        for task in project_tasks:
            task_account_ids = collect_task_and_subtask_accounts(task)
            account_ids.extend(task_account_ids)

        account_ids = list(set(account_ids))

        budget_lines = self.env['budget.line'].sudo()._read_group(
            [
                ('account_id', 'in', account_ids),
                ('budget_analytic_id', '!=', False),
                ('budget_analytic_id.state', 'in', ['confirmed', 'done']),
            ],
            ['budget_analytic_id', 'company_id'],
            ['budget_amount:sum', 'achieved_amount:sum', 'id:array_agg'],
        )

        has_company_access = False
        for line in budget_lines:
            if line[1].id in self.env.context.get('allowed_company_ids', []):
                has_company_access = True
                break
        total_allocated = total_spent = 0.0
        can_see_budget_items = with_action and has_company_access and (
                self.env.user.has_group('account.group_account_readonly')
                or self.env.user.has_group('analytic.group_analytic_accounting')
        )
        budget_data_per_budget = defaultdict(
            lambda: {
                'allocated': 0,
                'spent': 0,
                **({
                       'ids': [],
                       'budgets': [],
                   } if can_see_budget_items else {})
            }
        )

        budget_line = self.env['budget.line']
        project_budget_id = self.env['budget.line'].search([('account_id', '=', self.account_id.id)]) or False

        for budget_analytic, dummy, allocated, spent, ids in budget_lines:
            budget_line_id = budget_line.browse(ids)
            account_id = budget_line_id and budget_line_id.account_id.id or False
            project_id = self.env['project.project'].search([('account_id', '=', account_id)]) or False

            task_id = self.env['project.task'].search([('analytic_account_id', '=', account_id)], limit=1) or False
            is_task = False
            is_subtask = False

            if task_id:
                if task_id.parent_id:
                    is_subtask = True
                else:
                    is_task = True

            total = project_budget_id and sum(project_budget_id.mapped('budget_amount')) or 0
            budget_data = budget_data_per_budget[budget_analytic]
            budget_data['id'] = budget_analytic.id
            budget_data['name'] = budget_analytic.display_name
            budget_data['is_project'] = project_id and True or False
            budget_data['is_task'] = is_task
            budget_data['is_subtask'] = is_subtask
            budget_data['allocated'] += allocated
            budget_data['spent'] += spent
            total_allocated = total
            total_spent += spent if not project_id else 0
            # total_allocated += allocated
            # total_spent += spent

            if can_see_budget_items:
                budget_item = {
                    'id': budget_analytic.id,
                    'name': budget_analytic.display_name,
                    'allocated': allocated,
                    'spent': spent,
                    'progress': allocated and (spent - allocated) / abs(allocated),
                }
                budget_data['budgets'].append(budget_item)
                budget_data['ids'] += ids
            else:
                budget_data['budgets'] = []

        for budget_data in budget_data_per_budget.values():
            budget_data['progress'] = budget_data['allocated'] and (
                    budget_data['spent'] - budget_data['allocated']) / abs(budget_data['allocated'])

        budget_data_per_budget = list(budget_data_per_budget.values())
        if can_see_budget_items:
            for budget_data in budget_data_per_budget:
                if len(budget_data['budgets']) == 1:
                    budget_data['budgets'].clear()
                budget_data['action'] = {
                    'name': 'action_view_budget_lines',
                    'type': 'object',
                    'args': json.dumps([[('id', 'in', budget_data.pop('ids'))]]),
                }

        can_add_budget = with_action and self.env.user.has_group('account.group_account_user')
        budget_items = {
            'data': budget_data_per_budget,
            'total': {
                'allocated': total_allocated,
                'spent': total_spent,
                'progress': total_allocated and (total_spent - total_allocated) / abs(total_allocated),
            },
            'can_add_budget': can_add_budget,
        }
        if can_add_budget:
            budget_items['form_view_id'] = self.env.ref('project_account_budget.view_budget_analytic_form_dialog').id
            budget_items['company_id'] = self.company_id.id or self.env.company.id
        return budget_items

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        project_tasks = self.task_ids
        account_ids = []

        for task in project_tasks:
            if task.is_create_budget:
                if task.analytic_account_id:
                    account_ids.append(task.analytic_account_id.id)

                child_account_ids = task.child_ids.filtered(lambda l: l.is_create_budget).mapped(
                    'analytic_account_id.id')
                account_ids.extend(child_account_ids)
        target_accounts = account_ids and {str(account_id) for account_id in account_ids} or {}
        if self.account_id or account_ids:
            invoice_lines = self.env['account.move.line'].sudo().search_fetch([
                ('parent_state', 'in', ['draft', 'posted']),
                ('analytic_distribution', 'in', account_ids),
                ('purchase_line_id', '!=', False),
            ], ['parent_state', 'currency_id', 'price_subtotal', 'analytic_distribution'])
            purchase_order_line_invoice_line_ids = self._get_already_included_profitability_invoice_line_ids()
            with_action = with_action and (
                    self.env.user.has_group('purchase.group_purchase_user')
                    or self.env.user.has_group('account.group_account_invoice')
                    or self.env.user.has_group('account.group_account_readonly')
            )
            if invoice_lines:
                amount_invoiced = amount_to_invoice = 0.0
                purchase_order_line_invoice_line_ids.extend(invoice_lines.ids)
                for line in invoice_lines:
                    analytic_dist = line.analytic_distribution or {}
                    matched_keys = set(analytic_dist.keys()) & target_accounts

                    if not matched_keys:
                        continue

                    analytic_contribution = sum(analytic_dist[k] for k in matched_keys) / 100.0

                    price_subtotal = line.currency_id._convert(line.price_subtotal, self.currency_id, self.company_id)
                    cost = price_subtotal * analytic_contribution * (-1 if line.is_refund else 1)
                    if line.parent_state == 'posted':
                        amount_invoiced -= cost
                    else:
                        amount_to_invoice -= cost
                costs = profitability_items['costs']
                costs['total']['billed'] = 0
                costs['total']['to_bill'] = 0
                section_id = 'purchase_order'
                purchase_order_costs = {'id': section_id,
                                        'sequence': self._get_profitability_sequence_per_invoice_type()[section_id],
                                        'billed': amount_invoiced, 'to_bill': amount_to_invoice}
                if with_action:
                    args = [section_id, [('id', 'in', invoice_lines.purchase_line_id.ids)]]
                    if len(invoice_lines.purchase_line_id) == 1:
                        args.append(invoice_lines.purchase_line_id.id)
                    action = {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}
                    purchase_order_costs['action'] = action
                existing = next((i for i in costs['data'] if i['id'] == section_id), None)
                if existing:
                    existing['billed'] = amount_invoiced
                    existing['to_bill'] = amount_to_invoice
                else:
                    costs['data'].append(purchase_order_costs)
                costs['total']['billed'] += amount_invoiced
                costs['total']['to_bill'] += amount_to_invoice
            domain = [
                ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                ('parent_state', 'in', ['draft', 'posted']),
                ('price_subtotal', '!=', 0),
                ('id', 'not in', purchase_order_line_invoice_line_ids),
            ]
            self._get_costs_items_from_purchase(domain, profitability_items, with_action=with_action)
        return profitability_items