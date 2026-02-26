# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DprTask(models.Model):
    _name = 'dpr.task'
    _description = 'Construction Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, planned_start_date desc'
    _parent_name = 'parent_id'
    _parent_store = True

    # Odoo 19 compatible unique constraints
    _uniques = [
        ('task_code', 'Task code must be unique!'),
    ]

    name = fields.Char(
        string='Task Name',
        required=True,
        tracking=True
    )
    project_id = fields.Many2one(
        'dpr.project',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    task_code = fields.Char(
        string='Task Code',
        required=True,
        readonly=True,
        copy=False,
        index='btree',
        default=lambda self: _('New')
    )

    # =====================
    # HIERARCHY SUPPORT - Tower → Floor → Unit → Activity
    # =====================
    parent_id = fields.Many2one(
        'dpr.task',
        string='Parent Task',
        ondelete='cascade',
        index=True,
        help='Parent task for hierarchy (Tower → Floor → Unit → Activity)'
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'dpr.task',
        'parent_id',
        string='Sub-tasks'
    )
    task_level = fields.Selection([
        ('tower', 'Tower/Building'),
        ('floor', 'Floor'),
        ('unit', 'Unit/Flat'),
        ('activity', 'Activity'),
        ('other', 'Other Task')
    ], string='Task Level',
        default='other',
        required=True,
        tracking=True,
        help='Hierarchy level: Tower → Floor → Unit → Activity'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order within same level'
    )

    # =====================
    # TOWER FIELDS
    # =====================
    tower_code = fields.Char(
        string='Tower Code',
        help='Tower identifier: A, B, C, D, E',
        index=True
    )

    # =====================
    # FLOOR FIELDS
    # =====================
    floor_number = fields.Integer(
        string='Floor Number',
        help='Floor number: 14, 13, 12... 0 (GF), -1 (B1), -2 (B2)'
    )
    floor_name = fields.Char(
        string='Floor Name',
        help='Display name: 14th Floor, Ground Floor, Basement-1'
    )

    # =====================
    # UNIT FIELDS
    # =====================
    unit_number = fields.Char(
        string='Unit Number',
        help='Unit identifier: 1401, 1402, 101, 102, Club',
        index=True
    )
    unit_type = fields.Selection([
        ('1bhk', '1 BHK'),
        ('2bhk', '2 BHK'),
        ('3bhk', '3 BHK'),
        ('3.5bhk', '3.5 BHK'),
        ('4bhk', '4 BHK'),
        ('4.5bhk', '4.5 BHK'),
        ('5bhk', '5 BHK'),
        ('penthouse', 'Penthouse'),
        ('duplex', 'Duplex'),
        ('studio', 'Studio'),
        ('shop', 'Shop'),
        ('office', 'Office'),
        ('club', 'Club House'),
        ('amenity', 'Amenity'),
        ('other', 'Other')
    ], string='Unit Type')
    carpet_area = fields.Float(
        string='Carpet Area (sq.ft)',
        help='Carpet area in square feet'
    )
    built_up_area = fields.Float(
        string='Built-up Area (sq.ft)',
        help='Built-up area in square feet'
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer/Owner',
        domain=[('customer_rank', '>', 0)],
        help='Customer who purchased this unit'
    )
    is_sold = fields.Boolean(
        string='Is Sold',
        default=False,
        help='Whether this unit has been sold'
    )
    sale_date = fields.Date(
        string='Sale Date',
        help='Date when unit was sold'
    )
    possession_date = fields.Date(
        string='Possession Date',
        help='Expected/Actual possession date'
    )

    # =====================
    # ACTIVITY FIELDS
    # =====================
    activity_template_id = fields.Many2one(
        'dpr.activity.template',
        string='Activity Template',
        help='Standard activity template'
    )
    activity_category = fields.Selection([
        ('structural', 'Structural Work'),
        ('masonry', 'Masonry Work'),
        ('electrical', 'Electrical Work'),
        ('plumbing', 'Plumbing Work'),
        ('waterproofing', 'Waterproofing'),
        ('flooring', 'Flooring Work'),
        ('tiling', 'Tiling Work'),
        ('carpentry', 'Carpentry Work'),
        ('painting', 'Painting Work'),
        ('finishing', 'Finishing Work'),
        ('fixtures', 'Fixtures & Fittings'),
        ('other', 'Other')
    ], string='Activity Category')
    activity_status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('client_scope', 'Client Scope'),
        ('not_in_scope', 'Not in Our Scope'),
        ('on_hold', 'On Hold'),
        ('rework', 'Rework Required')
    ], string='Activity Status',
        default='not_started',
        tracking=True,
        help='Current status of the activity'
    )

    # =====================
    # COMPUTED HIERARCHY REFERENCES
    # =====================
    tower_id = fields.Many2one(
        'dpr.task',
        string='Tower',
        compute='_compute_hierarchy_refs',
        store=True,
        help='Reference to tower in hierarchy'
    )
    floor_id = fields.Many2one(
        'dpr.task',
        string='Floor',
        compute='_compute_hierarchy_refs',
        store=True,
        help='Reference to floor in hierarchy'
    )
    unit_id = fields.Many2one(
        'dpr.task',
        string='Unit',
        compute='_compute_hierarchy_refs',
        store=True,
        help='Reference to unit in hierarchy'
    )

    # =====================
    # PROGRESS TRACKING
    # =====================
    child_count = fields.Integer(
        string='Sub-tasks Count',
        compute='_compute_child_stats',
        store=True
    )
    activities_total = fields.Integer(
        string='Total Activities',
        compute='_compute_activity_stats',
        store=True,
        help='Total number of activities (recursive)'
    )
    activities_completed = fields.Integer(
        string='Completed Activities',
        compute='_compute_activity_stats',
        store=True,
        help='Number of completed activities'
    )
    activities_in_progress = fields.Integer(
        string='In Progress Activities',
        compute='_compute_activity_stats',
        store=True
    )
    activities_not_started = fields.Integer(
        string='Not Started Activities',
        compute='_compute_activity_stats',
        store=True
    )
    activities_progress_pct = fields.Float(
        string='Activities Progress %',
        compute='_compute_activity_stats',
        store=True,
        help='Percentage of completed activities'
    )

    # Link to Odoo project.task
    odoo_task_id = fields.Many2one(
        'project.task',
        string='Odoo Task',
        domain="[('project_id', '=', parent.odoo_project_id)]",
        help='Link to Odoo default task'
    )

    # Sync status
    is_synced = fields.Boolean(
        string='Synced with Odoo',
        compute='_compute_is_synced',
        store=True
    )
    description = fields.Text(
        string='Description'
    )
    assigned_to_id = fields.Many2one(
        'dpr.employee',
        string='Assigned To'
    )
    planned_start_date = fields.Date(
        string='Planned Start Date',
        required=True
    )
    planned_end_date = fields.Date(
        string='Planned End Date',
        required=True
    )
    actual_start_date = fields.Date(
        string='Actual Start Date'
    )
    actual_end_date = fields.Date(
        string='Actual End Date'
    )
    progress_percentage = fields.Float(
        string='Progress %',
        default=0.0,
        tracking=True
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('blocked', 'Blocked')
    ], string='Status',
        default='pending',
        tracking=True
    )
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Priority',
        default='medium'
    )
    task_type_id = fields.Many2one(
        'dpr.task.type',
        string='Task Type'
    )
    task_type = fields.Char(
        string='Task Type Name',
        compute='_compute_task_type',
        store=True
    )
    estimated_hours = fields.Float(
        string='Estimated Hours'
    )
    actual_hours = fields.Float(
        string='Actual Hours',
        compute='_compute_actual_hours',
        store=True
    )
    dpr_report_ids = fields.One2many(
        'dpr.report',
        'task_id',
        string='DPR Reports'
    )
    labor_ids = fields.One2many(
        'dpr.labor',
        'task_id',
        string='Labor Entries'
    )
    material_ids = fields.One2many(
        'dpr.material',
        'task_id',
        string='Material Entries'
    )
    equipment_ids = fields.One2many(
        'dpr.equipment',
        'task_id',
        string='Equipment Entries'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Multi-company support
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='project_id.company_id',
        store=True
    )

    # Overdue tracking
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('task_code', _('New')) == _('New'):
                vals['task_code'] = self.env['ir.sequence'].next_by_code('dpr.task')
        return super().create(vals_list)

    # =====================
    # HIERARCHY COMPUTED FIELDS
    # =====================

    @api.depends('parent_id', 'parent_id.task_level', 'task_level')
    def _compute_hierarchy_refs(self):
        """Compute tower, floor, unit references based on hierarchy"""
        for task in self:
            tower = floor = unit = False

            if task.task_level == 'tower':
                tower = task.id
            elif task.task_level == 'floor':
                floor = task.id
                tower = task.parent_id.id if task.parent_id and task.parent_id.task_level == 'tower' else False
            elif task.task_level == 'unit':
                unit = task.id
                floor = task.parent_id.id if task.parent_id and task.parent_id.task_level == 'floor' else False
                tower = task.parent_id.parent_id.id if floor and task.parent_id.parent_id and task.parent_id.parent_id.task_level == 'tower' else False
            elif task.task_level == 'activity':
                unit = task.parent_id.id if task.parent_id and task.parent_id.task_level == 'unit' else False
                floor = task.parent_id.parent_id.id if unit and task.parent_id.parent_id and task.parent_id.parent_id.task_level == 'floor' else False
                tower = task.parent_id.parent_id.parent_id.id if floor and task.parent_id.parent_id.parent_id and task.parent_id.parent_id.parent_id.task_level == 'tower' else False

            task.tower_id = tower
            task.floor_id = floor
            task.unit_id = unit

    @api.depends('child_ids')
    def _compute_child_stats(self):
        """Compute child task statistics"""
        for task in self:
            task.child_count = len(task.child_ids)

    @api.depends('child_ids.activity_status', 'child_ids.task_level', 'task_level', 'activity_status')
    def _compute_activity_stats(self):
        """Compute activity completion statistics recursively"""
        for task in self:
            if task.task_level == 'activity':
                # For activity level, count self
                task.activities_total = 1
                task.activities_completed = 1 if task.activity_status == 'done' else 0
                task.activities_in_progress = 1 if task.activity_status == 'in_progress' else 0
                task.activities_not_started = 1 if task.activity_status == 'not_started' else 0
            else:
                # For tower/floor/unit, count all activities recursively
                activities = task._get_all_activities()
                task.activities_total = len(activities)
                task.activities_completed = len(activities.filtered(lambda a: a.activity_status == 'done'))
                task.activities_in_progress = len(activities.filtered(lambda a: a.activity_status == 'in_progress'))
                task.activities_not_started = len(activities.filtered(lambda a: a.activity_status == 'not_started'))

            # Calculate progress percentage
            if task.activities_total > 0:
                task.activities_progress_pct = (task.activities_completed / task.activities_total) * 100
            else:
                task.activities_progress_pct = 0.0

    def _get_all_activities(self):
        """Recursively get all activity-level tasks under this task"""
        self.ensure_one()
        activities = self.env['dpr.task']

        for child in self.child_ids:
            if child.task_level == 'activity':
                activities |= child
            else:
                # Recursively get activities from children
                activities |= child._get_all_activities()

        return activities

    @api.depends('labor_ids.hours_worked')
    def _compute_actual_hours(self):
        for task in self:
            task.actual_hours = sum(task.labor_ids.mapped('hours_worked'))

    @api.depends('task_type_id')
    def _compute_task_type(self):
        for task in self:
            task.task_type = task.task_type_id.name or ''

    @api.depends('odoo_task_id', 'state', 'progress_percentage')
    def _compute_is_synced(self):
        for task in self:
            if not task.odoo_task_id:
                task.is_synced = False
            else:
                task.is_synced = task.odoo_task_id.state in ['1_done', '1_canceled'] or \
                                 (task.odoo_task_id.progress == task.progress_percentage)

    @api.depends('planned_end_date', 'state', 'actual_end_date')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for task in self:
            if task.state in ['pending', 'in_progress', 'blocked'] and task.planned_end_date:
                if task.planned_end_date < today:
                    task.is_overdue = True
                    task.days_overdue = (today - task.planned_end_date).days
                else:
                    task.is_overdue = False
                    task.days_overdue = 0
            else:
                task.is_overdue = False
                task.days_overdue = 0

    @api.constrains('progress_percentage')
    def _check_progress(self):
        for task in self:
            if task.progress_percentage < 0 or task.progress_percentage > 100:
                raise ValidationError(_('Progress percentage must be between 0 and 100!'))

    @api.constrains('planned_start_date', 'planned_end_date')
    def _check_dates(self):
        """Validate task dates."""
        for task in self:
            if task.planned_end_date and task.planned_start_date:
                if task.planned_end_date < task.planned_start_date:
                    raise ValidationError(
                        _('Planned end date cannot be before start date!')
                    )

    @api.constrains('parent_id', 'task_level')
    def _check_hierarchy(self):
        """Validate hierarchy rules"""
        for task in self:
            if task.parent_id:
                parent_level = task.parent_id.task_level
                child_level = task.task_level

                # Define valid parent-child relationships
                valid_hierarchy = {
                    'tower': ['floor'],
                    'floor': ['unit'],
                    'unit': ['activity'],
                    'activity': [],  # Activities cannot have children
                }

                if parent_level in valid_hierarchy:
                    if child_level not in valid_hierarchy[parent_level]:
                        raise ValidationError(
                            _('Invalid hierarchy: %s cannot be a child of %s') % (child_level, parent_level)
                        )

    def action_start(self):
        self.state = 'in_progress'
        if not self.actual_start_date:
            self.actual_start_date = fields.Date.today()

        # For activities, also update activity_status
        if self.task_level == 'activity' and self.activity_status == 'not_started':
            self.activity_status = 'in_progress'

    def action_complete(self):
        self.state = 'completed'
        self.progress_percentage = 100.0
        self.actual_end_date = fields.Date.today()

        # For activities, also update activity_status
        if self.task_level == 'activity':
            self.activity_status = 'done'

    def action_verify(self):
        self.state = 'verified'

    def action_block(self):
        self.state = 'blocked'

    def action_reset(self):
        self.state = 'pending'

        # For activities, also reset activity_status
        if self.task_level == 'activity':
            self.activity_status = 'not_started'

    def name_get(self):
        """Enhanced name display based on task level"""
        result = []
        for task in self:
            if task.task_level == 'tower':
                name = f"🏢 Tower {task.tower_code or task.name}"
            elif task.task_level == 'floor':
                name = f"🏗️ {task.floor_name or task.name}"
            elif task.task_level == 'unit':
                name = f"🏠 Unit {task.unit_number or task.name}"
            elif task.task_level == 'activity':
                name = f"✓ {task.name}"
            else:
                name = f"{task.task_code} - {task.name}"
            result.append((task.id, name))
        return result

    # =====================
    # HIERARCHY ACTIONS
    # =====================

    def action_view_children(self):
        """View child tasks"""
        self.ensure_one()
        return {
            'name': _('Sub-tasks of %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dpr.task',
            'view_mode': 'list,form,kanban',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_project_id': self.project_id.id,
            },
        }

    def action_view_activities(self):
        """View all activities under this task"""
        self.ensure_one()
        activities = self._get_all_activities()
        return {
            'name': _('Activities of %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dpr.task',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', activities.ids)],
            'context': {
                'default_project_id': self.project_id.id,
            },
        }

    # =====================
    # Odoo Task Integration
    # =====================

    def _map_dpr_state_to_odoo(self):
        """Map DPR task state to Odoo task state."""
        mapping = {
            'pending': '01_in_progress',
            'in_progress': '01_in_progress',
            'completed': '1_done',
            'verified': '1_done',
            'blocked': '04_waiting_normal',
        }
        return mapping.get(self.state, '01_in_progress')

    def _sync_to_odoo_task(self):
        """Sync DPR task data to linked Odoo task."""
        self.ensure_one()
        if self.odoo_task_id and not self._context.get('skip_odoo_sync'):
            self.odoo_task_id.with_context(skip_dpr_sync=True).write({
                'name': self.name,
                'date_deadline': self.planned_end_date,
                'planned_date_begin': self.planned_start_date,
            })

    def _sync_from_odoo_task(self):
        """Pull data from linked Odoo task."""
        self.ensure_one()
        if self.odoo_task_id:
            self.write({
                'name': self.odoo_task_id.name,
                'planned_start_date': self.odoo_task_id.create_date.date() if self.odoo_task_id.create_date else fields.Date.today(),
                'planned_end_date': self.odoo_task_id.date_deadline.date() if self.odoo_task_id.date_deadline else False,
            })

    def action_sync_from_odoo(self):
        """Action to sync from Odoo task."""
        self._sync_from_odoo_task()

    def action_sync_to_odoo(self):
        """Action to sync to Odoo task."""
        self._sync_to_odoo_task()

    def action_open_odoo_task(self):
        """Open linked Odoo task."""
        self.ensure_one()
        if self.odoo_task_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'res_id': self.odoo_task_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise ValidationError(_('No Odoo task linked!'))

    def action_create_odoo_task(self):
        """Create a new Odoo task and link it."""
        self.ensure_one()
        if not self.project_id.odoo_project_id:
            raise ValidationError(_('Link an Odoo project to this DPR project first!'))
        if self.odoo_task_id:
            raise ValidationError(_('This DPR task is already linked to an Odoo task!'))

        odoo_task = self.env['project.task'].create({
            'name': self.name,
            'project_id': self.project_id.odoo_project_id.id,
            'date_deadline': self.planned_end_date,
            'planned_date_begin': self.planned_start_date,
        })
        self.odoo_task_id = odoo_task
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': odoo_task.id,
            'view_mode': 'form',
            'target': 'current',
        }
