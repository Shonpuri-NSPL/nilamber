# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprProject(models.Model):
    _name = 'dpr.project'
    _description = 'Construction Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    # Odoo 19 compatible unique constraint using _uniques
    _uniques = [
        ('code', 'Project code must be unique!'),
    ]

    code = fields.Char(
        string='Project Code',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    name = fields.Char(
        string='Project Name',
        required=True
    )
    odoo_project_id = fields.Many2one(
        'project.project',
        string='Odoo Project',
        help='Link to Odoo default project'
    )
    description = fields.Text(
        string='Description'
    )
    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        domain=[('customer_rank', '>', 0)]
    )
    project_manager_id = fields.Many2one(
        'res.users',
        string='Project Manager',
        tracking=True
    )
    location = fields.Char(
        string='Site Location'
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today
    )
    end_date = fields.Date(
        string='Planned End Date'
    )
    actual_end_date = fields.Date(
        string='Actual End Date',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status',
        default='draft',
        tracking=True
    )
    estimated_budget = fields.Monetary(
        string='Estimated Budget'
    )
    actual_cost = fields.Monetary(
        string='Actual Cost',
        compute='_compute_actual_cost',
        store=True
    )
    latitude = fields.Float(
        string='GPS Latitude',
        digits=(10, 7)
    )
    longitude = fields.Float(
        string='GPS Longitude',
        digits=(10, 7)
    )
    project_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('infrastructure', 'Infrastructure'),
        ('other', 'Other')
    ], string='Project Type',
        default='commercial'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    task_ids = fields.One2many(
        'dpr.task',
        'project_id',
        string='Tasks'
    )
    dpr_report_ids = fields.One2many(
        'dpr.report',
        'project_id',
        string='DPR Reports'
    )
    employee_ids = fields.Many2many(
        'dpr.employee',
        string='Assigned Employees'
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        domain=[('company_id', '=', False)]
    )
    total_tasks = fields.Integer(
        string='Total Tasks',
        compute='_compute_total_tasks'
    )
    completed_tasks = fields.Integer(
        string='Completed Tasks',
        compute='_compute_completed_tasks'
    )
    overall_progress = fields.Float(
        string='Overall Progress %',
        compute='_compute_overall_progress',
        store=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Multi-company support
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company.id
    )

    # Budget control fields
    budget_warning_threshold = fields.Float(
        string='Budget Warning Threshold (%)',
        default=80.0,
        help='Percentage of budget at which warning is triggered'
    )
    cost_variance = fields.Float(
        string='Cost Variance (%)',
        compute='_compute_cost_variance',
        store=True
    )
    budget_status = fields.Selection([
        ('under_budget', 'Under Budget'),
        ('warning', 'Warning'),
        ('over_budget', 'Over Budget')
    ], compute='_compute_budget_status', store=True)

    # Overdue tracking fields
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_is_overdue',
        store=True
    )

    # Sync status with Odoo project
    odoo_project_synced = fields.Boolean(
        string='Odoo Project Synced',
        compute='_compute_odoo_project_synced',
        store=True
    )
    project_count = fields.Integer(
        string='Project Count',
        compute='_compute_project_count'
    )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('dpr.project')
        return super().create(vals_list)

    @api.depends('dpr_report_ids')
    def _compute_actual_cost(self):
        for project in self:
            labor_cost = sum(project.dpr_report_ids.mapped('total_labor_cost'))
            material_cost = sum(project.dpr_report_ids.mapped('total_material_cost'))
            equipment_cost = sum(project.dpr_report_ids.mapped('total_equipment_cost'))
            project.actual_cost = labor_cost + material_cost + equipment_cost

    def _compute_total_tasks(self):
        for project in self:
            project.total_tasks = len(project.task_ids)

    def _compute_completed_tasks(self):
        for project in self:
            project.completed_tasks = len(project.task_ids.filtered(lambda t: t.state == 'completed'))

    @api.depends('task_ids.progress_percentage', 'task_ids.state')
    def _compute_overall_progress(self):
        """Compute overall progress based on tasks"""
        for project in self:
            if not project.task_ids:
                project.overall_progress = 0.0
            else:
                # Only consider non-cancelled tasks for progress
                active_tasks = project.task_ids.filtered(lambda t: t.state != 'cancelled')
                if active_tasks:
                    project.overall_progress = sum(active_tasks.mapped('progress_percentage')) / len(active_tasks)
                else:
                    project.overall_progress = 0.0

    @api.depends('estimated_budget', 'actual_cost')
    def _compute_cost_variance(self):
        for project in self:
            if project.estimated_budget and project.estimated_budget > 0:
                project.cost_variance = (
                    (project.actual_cost - project.estimated_budget) / 
                    project.estimated_budget * 100
                )
            else:
                project.cost_variance = 0.0

    @api.depends('estimated_budget', 'actual_cost', 'cost_variance')
    def _compute_budget_status(self):
        for project in self:
            if not project.estimated_budget:
                project.budget_status = 'under_budget'
            elif project.cost_variance < project.budget_warning_threshold:
                project.budget_status = 'under_budget'
            elif project.cost_variance < (project.budget_warning_threshold + 10):
                project.budget_status = 'warning'
            else:
                project.budget_status = 'over_budget'

    @api.depends('end_date', 'state', 'actual_end_date')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for project in self:
            if project.state in ['active', 'on_hold'] and project.end_date:
                if project.end_date < today:
                    project.is_overdue = True
                    project.days_overdue = (today - project.end_date).days
                else:
                    project.is_overdue = False
                    project.days_overdue = 0
            else:
                project.is_overdue = False
                project.days_overdue = 0

    @api.depends('start_date', 'end_date')
    def _compute_odoo_project_synced(self):
        for project in self:
            if not project.odoo_project_id:
                project.odoo_project_synced = False
            else:
                odoo_proj = project.odoo_project_id
                synced = (
                    odoo_proj.date_start == project.start_date and
                    odoo_proj.date == project.end_date
                )
                project.odoo_project_synced = synced

    def _compute_project_count(self):
        for project in self:
            project.project_count = 1 if project.odoo_project_id else 0

    @api.constrains('start_date', 'end_date', 'actual_end_date')
    def _check_dates(self):
        """Validate project dates."""
        for record in self:
            if record.end_date and record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError(
                        _('Planned end date cannot be before start date!')
                    )
            if record.actual_end_date and record.start_date:
                if record.actual_end_date < record.start_date:
                    raise ValidationError(
                        _('Actual end date cannot be before start date!')
                    )

    @api.constrains('estimated_budget')
    def _check_budget(self):
        """Validate budget is positive."""
        for record in self:
            if record.estimated_budget < 0:
                raise ValidationError(
                    _('Estimated budget must be positive!')
                )

    def action_draft(self):
        self.state = 'draft'

    def action_activate(self):
        """Activate project with validation."""
        self.ensure_one()
        
        # Validation: Check if project manager is assigned
        if not self.project_manager_id:
            raise ValidationError(
                _('Please assign a Project Manager before activating the project.')
            )
        
        # Validation: Check if at least one employee is assigned
        if not self.employee_ids:
            raise ValidationError(
                _('Please assign at least one Employee before activating the project.')
            )
        
        # Create Odoo project if not already linked
        if not self.odoo_project_id:
            odoo_project_vals = {
                'name': self.name or self.code,
                'partner_id': self.client_id.id,
                'user_id': self.project_manager_id.id,
                'date_start': self.start_date,
                'date': self.end_date,
            }
            # If estimated budget exists, create budget in Odoo project
            if self.estimated_budget:
                odoo_project_vals['is_create_budget'] = True
                odoo_project_vals['budget_amount'] = self.estimated_budget
            
            odoo_project = self.env['project.project'].create(odoo_project_vals)
            self.odoo_project_id = odoo_project
            
            # Link analytic account from Odoo project if available
            if odoo_project.account_id and not self.analytic_account_id:
                self.analytic_account_id = odoo_project.account_id.id
        
        # Sync to Odoo project if linked
        if self.odoo_project_id:
            self._sync_to_odoo_project()
        self.state = 'active'

    def action_put_on_hold(self):
        self.state = 'on_hold'

    def action_complete(self):
        """Complete project with validation."""
        self.ensure_one()
        
        # Check for incomplete tasks
        incomplete_tasks = self.task_ids.filtered(
            lambda t: t.state not in ['completed', 'verified']
        )
        if incomplete_tasks:
            raise ValidationError(
                _('%d tasks are still incomplete!') % len(incomplete_tasks)
            )
        
        # Check for pending DPR reports
        pending_reports = self.dpr_report_ids.filtered(
            lambda r: r.state == 'draft'
        )
        if pending_reports:
            raise ValidationError(
                _('%d DPR reports are still in draft!') % len(pending_reports)
            )
        
        self.state = 'completed'
        self.actual_end_date = fields.Date.today()

    def action_cancel(self):
        self.state = 'cancelled'

    @api.onchange('odoo_project_id')
    def _onchange_project_id(self):
        """Onchange to set dates and budget from selected project."""
        if self.odoo_project_id:
            # Get the associated project.project record
            project = self.odoo_project_id
            
            # Set name from Odoo project
            self.name = project.name
            
            # Set start date from project
            if project.date_start:
                self.start_date = project.date_start
            
            # Set planned end date from project (date field is the planned end date)
            if project.date:
                self.end_date = project.date
            
            # Set analytic account from project (account_id is the analytic account in project.project)
            if hasattr(project, 'account_id') and project.account_id:
                self.analytic_account_id = project.account_id
            
            # Set budget if available (project.budget exists in some versions)
            if hasattr(project, 'budget') and project.budget:
                self.estimated_budget = project.budget
    
    def name_get(self):
        result = []
        for project in self:
            name = f"{project.code} - {project.name}"
            result.append((project.id, name))
        return result

    # =====================
    # Odoo Project Integration
    # =====================

    def _sync_to_odoo_project(self):
        """Sync DPR project data to linked Odoo project."""
        self.ensure_one()
        if self.odoo_project_id and not self._context.get('skip_odoo_sync'):
            self.odoo_project_id.with_context(skip_dpr_sync=True).write({
                'date_start': self.start_date,
                'date': self.end_date,
                'partner_id': self.client_id.id,
                'user_id': self.project_manager_id.id,
            })

    def _sync_from_odoo_project(self):
        """Pull data from linked Odoo project."""
        self.ensure_one()
        if self.odoo_project_id:
            self.write({
                'start_date': self.odoo_project_id.date_start or fields.Date.today(),
                'end_date': self.odoo_project_id.date,
                'client_id': self.odoo_project_id.partner_id.id,
                'project_manager_id': self.odoo_project_id.user_id.id,
            })

    def action_sync_from_odoo(self):
        """Action to sync from Odoo project."""
        self._sync_from_odoo_project()

    def action_sync_to_odoo(self):
        """Action to sync to Odoo project."""
        self._sync_to_odoo_project()

    def action_open_odoo_project(self):
        """Open linked Odoo project."""
        self.ensure_one()
        if self.odoo_project_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.project',
                'res_id': self.odoo_project_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise ValidationError(_('No Odoo project linked!'))

    def action_create_odoo_project(self):
        """Create a new Odoo project and link it."""
        self.ensure_one()
        if self.odoo_project_id:
            raise ValidationError(_('This DPR project is already linked to an Odoo project!'))
        
        odoo_project = self.env['project.project'].create({
            'name': self.code,
            'partner_id': self.client_id.id,
            'user_id': self.project_manager_id.id,
            'date_start': self.start_date,
            'date': self.end_date,
        })
        self.odoo_project_id = odoo_project
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': odoo_project.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        """Custom unlink method to delete related tasks first.
        
        Only allows deletion if ALL related tasks are in 'pending' state.
        Also deletes the linked Odoo project if exists.
        """
        for project in self:
            if project.task_ids:
                # Check if all tasks are in 'pending' state
                non_pending_tasks = project.task_ids.filtered(
                    lambda t: t.state != 'pending'
                )
                if non_pending_tasks:
                    raise ValidationError(
                        _('Cannot delete project "%s" because it has %d task(s) that are not in pending state. '
                          'Only projects with all tasks in pending state can be deleted.') % 
                        (project.name, len(non_pending_tasks))
                    )
                # All tasks are in pending state, delete them first
                project.task_ids.unlink()
            
            # Also delete the linked Odoo project if exists
            if project.odoo_project_id:
                project.odoo_project_id.unlink()
        
        return super(DprProject, self).unlink()
