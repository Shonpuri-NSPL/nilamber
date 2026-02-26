# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

CLOSED_STATES = {
    '1_done': 'Done',
    '1_canceled': 'Cancelled',
}
_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = "project.task"

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        ondelete='cascade',
        index=True,
    )
    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget Analytic',
        ondelete='cascade',
        index=True,
    )
    sequence_code = fields.Char("Sequence", default=lambda self: _('New'))
    budget_amount = fields.Float("Budget Amount", compute='_compute_amount',
                                 store=True, readonly=False)
    budget_type = fields.Selection([
        ('expense', 'Expense'),
    ], string="Budget Type", default="expense")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    is_create_budget = fields.Boolean("Want to Create Budget??")
    unit_id = fields.Many2one('uom.uom', string='Unit')
    quantity = fields.Float(string='Quantity', store=True, )
    rate = fields.Float(string='Rate', store=True, )
    remarks = fields.Char(string='Remarks')
    is_used_rate_and_qty = fields.Boolean("Want to Use Rate and Qty?")
    display_type = fields.Selection([
        ('line_section', 'Section'),
    ], string='Display Type', default=False)
    section_subtotal = fields.Float(
        string='',
        compute='_compute_section_subtotal',
        store=False
    )
    is_land_acquisition = fields.Boolean("Want to Add Land Acquisition?")
    total_quantity = fields.Float(string="Acres")

    calculation_type = fields.Selection([
        ('manual', 'Manual Entry'),
        ('sum_children', 'Sum of Child Tasks'),
        ('add_percentage', 'Add Percentage'),
    ], string='Calculation Type', default='manual')

    percentage_value = fields.Float(string='Percentage', default=0.0)
    reference_task_id = fields.Many2one('project.task', string='Reference Task')
    reference_task_ids = fields.Many2many(
        'project.task',
        'project_task_reference_rel',
        'task_id',
        'reference_task_id',
        string='Reference Tasks'
    )
    word_of_budget_amount = fields.Char("Budget amount in word", compute='_compute_word_of_budget_amount', store=True)
    task_no = fields.Char(string='Seq', compute='_compute_task_no', store=True)
    no = fields.Char(string='No')
    uid_no = fields.Char(string='UID')
    land_holder_name = fields.Char(string='Name of land holder')
    father_name = fields.Char(string='Father Name')
    category = fields.Char(string='Category')
    cast = fields.Char(string='Cast')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', default='male')

    total_tree_symbol = fields.Float(string='The Total Symbol Of The Tree')
    reallocation_funds = fields.Float(string='Reallocation Funds')
    compensation_payable = fields.Float(string='Compensation Payable')
    compensation_payment = fields.Float(string='Compensation Payment')
    due_date = fields.Date("Due Date")
    status = fields.Selection([
        ('payment', 'Payment'),
        ('pending', 'Pending'),
    ], string='Status', default='pending')
    is_village = fields.Boolean("Is Village?")
    is_person = fields.Boolean("Is Person?")
    can_be_village = fields.Boolean(string="Can Be Village", compute='_compute_can_be_village', store=False)
    can_be_person = fields.Boolean(string="Can Be Person", compute='_compute_can_be_person', store=False)
    is_warehouse = fields.Boolean('Warehouse available')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    spend_amount = fields.Float("Spend Amount", readonly=True)

    @api.depends('child_ids')
    def _compute_subtask_count(self):
        if not any(self._ids):
            for task in self:
                task.subtask_count, task.closed_subtask_count = len(task.child_ids), len(
                    task.child_ids.filtered(lambda r: r.state in CLOSED_STATES))
            return
        total_and_closed_subtask_count_per_parent_id = {
            parent.id: (count, sum(s in CLOSED_STATES for s in states))
            for parent, states, count in self.env['project.task']._read_group(
                [
                    ('parent_id', 'in', self.ids),
                    ('display_type', 'not in', ['line_section'])
                ],
                ['parent_id'],
                ['state:array_agg', '__count']
            )

        }
        for task in self:
            task.subtask_count, task.closed_subtask_count = total_and_closed_subtask_count_per_parent_id.get(task.id,
                                                                                                             (0, 0))

    @api.depends('parent_id', 'parent_id.is_land_acquisition', 'parent_id.is_village')
    def _compute_can_be_village(self):
        for task in self:
            if task.parent_id and task.parent_id.is_land_acquisition:
                task.can_be_village = True
            else:
                task.can_be_village = False

    @api.depends('parent_id', 'parent_id.is_village')
    def _compute_can_be_person(self):
        for task in self:
            if task.parent_id and task.parent_id.is_village:
                task.can_be_person = True
            else:
                task.can_be_person = False

    @api.onchange('is_village')
    def _onchange_is_village(self):
        if self.is_village:
            self.is_person = True
        else:
            self.is_person = False
            self._clear_person_fields()

    def _clear_person_fields(self):
        self.total_quantity = 0.0
        self.no = False
        self.uid_no = False
        self.land_holder_name = False
        self.father_name = False
        self.category = False
        self.cast = False
        self.gender = 'male'
        self.total_tree_symbol = 0.0
        self.reallocation_funds = 0.0
        self.compensation_payable = 0.0
        self.compensation_payment = 0.0
        self.status = 'payment'

    @api.depends('parent_id', 'parent_id.child_ids', 'parent_id.child_ids.sequence',
                 'parent_id.child_ids.display_type', 'display_type', 'sequence')
    def _compute_task_no(self):
        for task in self:
            if not task.parent_id:
                task.task_no = ''
                continue
            if task.display_type in ('line_section', 'line_note'):
                task.task_no = ''
                continue
            all_siblings = task.parent_id.child_ids.sorted(key=lambda r: r.sequence)
            seq_number = 0
            for sibling in all_siblings:
                if sibling.display_type not in ('line_section', 'line_note'):
                    seq_number += 1
                if sibling.id == task.id:
                    break
            task.task_no = str(seq_number)


    @api.depends('budget_amount')
    def _compute_word_of_budget_amount(self):
        for record in self:
            if record.budget_amount:
                currency = record.company_id.currency_id or self.env.company.currency_id
                record.word_of_budget_amount = currency.amount_to_text(record.budget_amount)
            else:
                record.word_of_budget_amount = False


    @api.onchange('calculation_type')
    def _onchange_calculation_type(self):
        for task in self:
            if task.calculation_type in ['sum_children','percentage', 'add_percentage']:
                task.is_used_rate_and_qty = False

    @api.depends('parent_id.child_ids.budget_amount', 'parent_id.child_ids.display_type')
    def _compute_section_subtotal(self):
        for task in self:
            if task.display_type == 'line_section' and task.parent_id:
                all_siblings = task.parent_id.child_ids.sorted(key=lambda r: r.sequence)
                current_index = 0
                for idx, sibling in enumerate(all_siblings):
                    if sibling.id == task.id:
                        current_index = idx
                        break
                subtotal = 0.0
                for idx in range(current_index + 1, len(all_siblings)):
                    sibling = all_siblings[idx]
                    if sibling.display_type == 'line_section':
                        break
                    if not sibling.display_type:
                        subtotal += sibling.budget_amount
                task.section_subtotal = subtotal
            else:
                task.section_subtotal = 0.0

    @api.depends('quantity', 'rate', 'is_used_rate_and_qty', 'child_ids.budget_amount',
                 'calculation_type', 'percentage_value', 'reference_task_id.budget_amount')
    def _compute_amount(self):
        for task in self:
            if task.display_type:
                task.budget_amount = 0.0
                continue
            if task.is_used_rate_and_qty:
                task.budget_amount = task.quantity * task.rate
            elif task.calculation_type == 'sum_children':
                for subtask in self.reference_task_ids:
                    task.budget_amount += subtask.budget_amount
            elif task.calculation_type == 'add_percentage':
                if task.reference_task_id:
                    base_amount = task.reference_task_id.budget_amount
                    task.budget_amount = base_amount + (base_amount * task.percentage_value / 100.0)

    @api.onchange('planned_date_begin', 'date_deadline')
    def get_task_date(self):
        self.date_from = self.planned_date_begin and self.planned_date_begin.date() or False
        self.date_to = self.date_deadline and self.date_deadline.date() or False

    def create_analytic_budget(self, task_id):
        if task_id and task_id.budget_amount:
            account_id = False
            budget_analytic_id = False
            existing_analytic_account = self.env['account.analytic.account'].search([
                ('name', '=', task_id.sequence_code)
            ])
            if not existing_analytic_account:
                account_id = self.env['account.analytic.account'].create({
                    'name': task_id.sequence_code,
                    'code': task_id.name,
                    'partner_id': task_id.partner_id.id,
                    'company_id': self.env.company.id,
                    'plan_id': self.env.ref('analytic.analytic_plan_projects').id
                })

            existing_budget_analytic_id = self.env['budget.analytic'].search([
                ('name', '=', task_id.sequence_code + ' : ' + task_id.name)
            ])
            if not existing_budget_analytic_id:
                budget_analytic_id = self.env['budget.analytic'].create({
                    'name': task_id.sequence_code + ' : ' + task_id.name,
                    'user_id': self.env.user.id,
                    'budget_type': task_id.budget_type,
                    'date_from': task_id.date_from,
                    'date_to': task_id.date_to,
                    'parent_id': False,
                    'company_id': self.env.company.id,
                })
                budget_analytic_id.action_budget_confirm()
                self.env['budget.line'].create({
                    'budget_analytic_id': budget_analytic_id and budget_analytic_id.id or False,
                    'account_id': account_id and account_id.id or False,
                    'budget_amount': task_id.budget_amount,
                })

            if account_id and budget_analytic_id:
                task_id.write({
                    'analytic_account_id': account_id.id,
                    'budget_analytic_id': budget_analytic_id.id,
                    'company_id': self.env.company.id,
                })
                task_id.project_id.write({
                    'company_id': self.env.company.id,
                })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence_code', 'New') == 'New' and not vals.get('parent_id'):
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code('sequence.project.task.code') or _('New')
            if vals.get('sequence_code', 'New') == 'New' and vals.get('parent_id'):
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code('sequence.sub.task.code') or _('New')
        tasks = super(ProjectTask, self).create(vals_list)

        for task in tasks:
            if task.calculation_type != 'manual':
                continue

            project_budget_id = self.env['budget.line'].search([('account_id', '=', task.project_id.account_id.id)],
                                                               limit=1)
            # if not project_budget_id:
            #     raise ValidationError(_("Please first configure budget for your project!!"))

            if task.is_create_budget and not task.parent_id and task.budget_amount and \
                    task.budget_amount > 0 and project_budget_id:
                all_project_task_amount = task.project_id and sum(
                    task.project_id.task_ids.mapped('budget_amount')) or 0.0
                if project_budget_id and all_project_task_amount > project_budget_id.budget_amount:
                    raise ValidationError(_("Task Budget Amount is greater than overall Project Budget!!"))
                task.create_analytic_budget(task)

            if task.is_create_budget and task.parent_id and task.parent_id.is_create_budget \
                    and task.budget_amount and task.budget_amount > 0 and project_budget_id:
                all_sub_task_amount = task.parent_id.child_ids and sum(
                    task.parent_id.child_ids.mapped('budget_amount')) or 0.0
                # if all_sub_task_amount > task.parent_id.budget_amount:
                #     raise ValidationError(_("Sub Task Budget Amount cannot exceed its Parent Task Amount!!"))
                task.create_analytic_budget(task)
        return tasks

    def write(self, vals):
        tasks = super(ProjectTask, self).write(vals)
        if 'budget_amount' in vals:
            for task in self:
                if task.budget_analytic_id and task.analytic_account_id:
                    budget_line = self.env['budget.line'].search([
                        ('budget_analytic_id', '=', task.budget_analytic_id.id),
                        ('account_id', '=', task.analytic_account_id.id)
                    ], limit=1)
                    if budget_line:
                        budget_line.write({
                            'budget_amount': vals['budget_amount']
                        })
        for task in self:
            if task.calculation_type != 'manual':
                continue

            project_budget_id = self.env['budget.line'].search([('account_id', '=', task.project_id.account_id.id)],
                                                               limit=1)
            if task.is_create_budget and not task.parent_id and task.budget_amount and \
                    task.budget_amount > 0 and project_budget_id:
                all_project_task_amount = task.project_id and sum(
                    task.project_id.task_ids.mapped('budget_amount')) or 0.0
                # if project_budget_id and all_project_task_amount > project_budget_id.budget_amount:
                #     raise ValidationError(_("Task Budget Amount is greater than overall Project Budget!!"))
                if not task.analytic_account_id and not task.budget_analytic_id:
                    task.create_analytic_budget(task)

            if task.is_create_budget and task.parent_id and task.parent_id.is_create_budget \
                    and task.budget_amount and task.budget_amount > 0 and project_budget_id:
                all_sub_task_amount = task.parent_id.child_ids and sum(
                    task.parent_id.child_ids.mapped('budget_amount')) or 0.0
                # if all_sub_task_amount > task.parent_id.budget_amount:
                #     raise ValidationError(_("Sub Task Budget Amount cannot exceed its Parent Task Amount!!"))
                if not task.analytic_account_id and not task.budget_analytic_id:
                    task.create_analytic_budget(task)
        return tasks