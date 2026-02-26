# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectSetupWizard(models.TransientModel):
    """
    Master wizard to create complete project structure
    """
    _name = 'project.setup.wizard'
    _description = 'Project Setup Wizard'

    # Step 1: Project Details
    step = fields.Selection([
        ('project', 'Project Details'),
        ('towers', 'Tower Configuration'),
        ('review', 'Review & Create'),
    ], string='Step', default='project', required=True)

    # Project Information
    project_name = fields.Char(
        string='Project Name',
        required=True,
        help='e.g., BELLISSIMO-04, SKYLINE TOWERS'
    )
    project_code = fields.Char(
        string='Project Code',
        required=True,
        help='e.g., PROJ-001'
    )
    project_location = fields.Char(
        string='Location',
        required=True,
        help='Project location/address'
    )
    project_start_date = fields.Date(
        string='Project Start Date',
        required=True,
        default=fields.Date.today
    )
    project_end_date = fields.Date(
        string='Project End Date',
        required=True
    )
    project_budget = fields.Float(
        string='Project Budget',
        required=True,
        digits=(16, 2)
    )


    # Tower Configuration
    tower_count = fields.Integer(
        string='Number of Towers',
        default=1,
        required=True,
        help='How many towers/buildings in this project?'
    )
    tower_line_ids = fields.One2many(
        'project.setup.wizard.tower',
        'wizard_id',
        string='Tower Configuration'
    )

    # Unit Configuration (Default for all units)
    default_unit_type = fields.Selection([
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
        ('other', 'Other')
    ], string='Default Unit Type',
        default='3bhk',
        help='Default type for all units (can be customized per floor)'
    )
    default_carpet_area = fields.Float(
        string='Default Carpet Area (sq.ft)',
        default=1200.0,
        help='Default carpet area for all units'
    )

    # Activity Configuration
    create_activities = fields.Boolean(
        string='Create Standard Activities',
        default=True,
        help='Create 19 standard activities for each unit'
    )
    activity_template_ids = fields.Many2many(
        'dpr.activity.template',
        string='Activity Templates',
        help='Select specific templates or leave empty for all'
    )

    # Summary
    total_towers = fields.Integer(
        string='Total Towers',
        compute='_compute_summary',
        store=True
    )
    total_floors = fields.Integer(
        string='Total Floors',
        compute='_compute_summary',
        store=True
    )
    total_units = fields.Integer(
        string='Total Units',
        compute='_compute_summary',
        store=True
    )
    total_activities = fields.Integer(
        string='Total Activities',
        compute='_compute_summary',
        store=True
    )

    @api.depends('tower_line_ids', 'tower_line_ids.floor_line_ids',
                 'tower_line_ids.floor_line_ids.units_per_floor', 'create_activities')
    def _compute_summary(self):
        for wizard in self:
            wizard.total_towers = len(wizard.tower_line_ids)
            wizard.total_floors = sum(wizard.tower_line_ids.mapped('floor_count'))
            wizard.total_units = sum(
                floor.units_per_floor
                for tower in wizard.tower_line_ids
                for floor in tower.floor_line_ids
            )

            # Calculate activities (19 per unit if enabled)
            if wizard.create_activities:
                template_count = len(wizard.activity_template_ids) if wizard.activity_template_ids else 19
                wizard.total_activities = wizard.total_units * template_count
            else:
                wizard.total_activities = 0

    @api.constrains('project_start_date', 'project_end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.project_end_date < wizard.project_start_date:
                raise ValidationError(_('Project end date cannot be before start date!'))

    @api.model
    def create(self, vals_list):
        """Auto-capitalize text fields on create"""
        # Handle both single dict and list of dicts
        if isinstance(vals_list, list):
            for vals in vals_list:
                if vals.get('project_name'):
                    vals['project_name'] = vals['project_name'].upper()
                if vals.get('project_code'):
                    vals['project_code'] = vals['project_code'].upper()
                if vals.get('project_location'):
                    vals['project_location'] = vals['project_location'].upper()
        else:
            if vals_list.get('project_name'):
                vals_list['project_name'] = vals_list['project_name'].upper()
            if vals_list.get('project_code'):
                vals_list['project_code'] = vals_list['project_code'].upper()
            if vals_list.get('project_location'):
                vals_list['project_location'] = vals_list['project_location'].upper()
        return super(ProjectSetupWizard, self).create(vals_list)

    def write(self, vals):
        """Auto-capitalize text fields on write"""
        if vals.get('project_name'):
            vals['project_name'] = vals['project_name'].upper()
        if vals.get('project_code'):
            vals['project_code'] = vals['project_code'].upper()
        if vals.get('project_location'):
            vals['project_location'] = vals['project_location'].upper()
        return super(ProjectSetupWizard, self).write(vals)

    @api.constrains('tower_count')
    def _check_tower_count(self):
        for wizard in self:
            if wizard.tower_count < 1 or wizard.tower_count > 50:
                raise ValidationError(_('Tower count must be between 1 and 50!'))

    @api.constrains('tower_line_ids')
    def _check_tower_lines(self):
        """Ensure all towers have floors configured"""
        for wizard in self:
            if wizard.step == 'review':
                for tower in wizard.tower_line_ids:
                    if not tower.floor_line_ids:
                        raise ValidationError(
                            _('Tower "%s" has no floors configured! Please set floor count.') % tower.tower_name
                        )
                    for floor in tower.floor_line_ids:
                        if not floor.floor_number:
                            raise ValidationError(
                                _('Floor in Tower "%s" is missing floor number!') % tower.tower_name
                            )

    def action_next_step(self):
        """Move to next step"""
        self.ensure_one()

        if self.step == 'project':
            # Generate tower lines based on tower_count
            if not self.tower_line_ids or len(self.tower_line_ids) != self.tower_count:
                self.tower_line_ids.unlink()
                for i in range(self.tower_count):
                    tower = self.env['project.setup.wizard.tower'].create({
                        'wizard_id': self.id,
                        'tower_name': f'Tower {chr(65 + i)}',  # A, B, C...
                        'tower_code': chr(65 + i),
                        'sequence': i + 1,
                        'floor_count': 10,  # Default 10 floors
                    })
                    # Trigger onchange to generate floors
                    tower._onchange_floor_count()
            self.step = 'towers'
        elif self.step == 'towers':
            # Validate towers have floors
            for tower in self.tower_line_ids:
                if not tower.floor_line_ids:
                    raise ValidationError(
                        _('Tower "%s" has no floors! Please set floor count.') % tower.tower_name
                    )
            self.step = 'review'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_previous_step(self):
        """Move to previous step"""
        self.ensure_one()

        if self.step == 'towers':
            self.step = 'project'
        elif self.step == 'review':
            self.step = 'towers'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_project(self):
        """Create entire project structure"""
        self.ensure_one()

        # Validate
        if not self.project_budget:
            raise ValidationError(_('Please Enter The Project Budget'))
        if not self.tower_line_ids:
            raise ValidationError(_('Please configure at least one tower!'))

        for tower in self.tower_line_ids:
            if not tower.floor_line_ids:
                raise ValidationError(_('Tower %s has no floors configured!') % tower.tower_name)

        # Get activity templates
        if self.create_activities:
            if self.activity_template_ids:
                templates = self.activity_template_ids
            else:
                templates = self.env['dpr.activity.template'].search([('active', '=', True)], order='sequence')

            if not templates:
                raise ValidationError(_('No activity templates found! Please create activity templates first.'))

        # Create DPR Project
        project = self.env['dpr.project'].create({
            'name': self.project_name,
            'code': self.project_code or self.env['ir.sequence'].next_by_code('dpr.project'),
            'start_date': self.project_start_date,
            'end_date': self.project_end_date,
            'estimated_budget': self.project_budget,
            'description': f'Location: {self.project_location}\n'
                           f'Towers: {self.total_towers}\n'
                           f'Floors: {self.total_floors}\n'
                           f'Units: {self.total_units}',
        })

        # Create Towers, Floors, Units, Activities
        for tower_line in self.tower_line_ids.sorted('sequence'):
            # Create Tower
            tower = self.env['dpr.task'].create({
                'name': tower_line.tower_name,
                'project_id': project.id,
                'task_level': 'tower',
                'tower_code': tower_line.tower_code,
                'planned_start_date': self.project_start_date,
                'planned_end_date': self.project_end_date,
                'sequence': tower_line.sequence,
                'description': f'{tower_line.floor_count} floors, '
                               f'{sum(tower_line.floor_line_ids.mapped("units_per_floor"))} units',
            })

            # Create Floors
            for floor_line in tower_line.floor_line_ids.sorted('floor_number'):
                floor = self.env['dpr.task'].create({
                    'name': floor_line.floor_name,
                    'project_id': project.id,
                    'parent_id': tower.id,
                    'task_level': 'floor',
                    'floor_number': floor_line.floor_number,
                    'floor_name': floor_line.floor_name,
                    'planned_start_date': self.project_start_date,
                    'planned_end_date': self.project_end_date,
                    'sequence': floor_line.floor_number,
                    'description': f'{floor_line.units_per_floor} units',
                })

                # Create Units
                for unit_num in range(1, floor_line.units_per_floor + 1):
                    # Generate unit number
                    if floor_line.floor_number >= 0:
                        unit_number = f'{floor_line.floor_number}{unit_num:02d}'
                    else:
                        unit_number = f'B{abs(floor_line.floor_number)}{unit_num:02d}'

                    unit = self.env['dpr.task'].create({
                        'name': f'Unit {unit_number}',
                        'project_id': project.id,
                        'parent_id': floor.id,
                        'task_level': 'unit',
                        'unit_number': unit_number,
                        'unit_type': floor_line.unit_type or self.default_unit_type,
                        'carpet_area': floor_line.carpet_area or self.default_carpet_area,
                        'planned_start_date': self.project_start_date,
                        'planned_end_date': self.project_end_date,
                        'sequence': unit_num,
                    })

                    # Create Activities
                    if self.create_activities:
                        for template in templates:
                            self.env['dpr.task'].create({
                                'name': template.name,
                                'project_id': project.id,
                                'parent_id': unit.id,
                                'task_level': 'activity',
                                'activity_template_id': template.id,
                                'activity_category': template.category,
                                'activity_status': 'not_started',
                                'planned_start_date': self.project_start_date,
                                'planned_end_date': self.project_end_date,
                                'estimated_hours': template.estimated_hours,
                                'sequence': template.sequence,
                            })

        # Show success message and open project
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': _(f'Project "{self.project_name}" created successfully!\n'
                             f'Towers: {self.total_towers}, Floors: {self.total_floors}, '
                             f'Units: {self.total_units}, Activities: {self.total_activities}'),
                'type': 'success',
                'sticky': False,
            }
        }


class ProjectSetupWizardTower(models.TransientModel):
    """Tower configuration line"""
    _name = 'project.setup.wizard.tower'
    _description = 'Tower Configuration'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'project.setup.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    tower_name = fields.Char(
        string='Tower Name',
        required=True,
        help='e.g., Tower A, Tower B'
    )
    tower_code = fields.Char(
        string='Tower Code',
        required=True,
        help='e.g., A, B, C'
    )
    floor_count = fields.Integer(
        string='Number of Floors',
        default=10,
        required=True,
        help='How many floors in this tower?'
    )
    floor_line_ids = fields.One2many(
        'project.setup.wizard.floor',
        'tower_id',
        string='Floor Configuration'
    )
    total_units = fields.Integer(
        string='Total Units',
        compute='_compute_total_units',
        store=True
    )

    @api.depends('floor_line_ids', 'floor_line_ids.units_per_floor')
    def _compute_total_units(self):
        for tower in self:
            tower.total_units = sum(tower.floor_line_ids.mapped('units_per_floor'))

    @api.model
    def create(self, vals_list):
        """Override create to auto-generate floors"""
        # Handle both single dict and list of dicts
        if isinstance(vals_list, list):
            for vals in vals_list:
                if vals.get('tower_name'):
                    vals['tower_name'] = vals['tower_name'].upper()
                if vals.get('tower_code'):
                    vals['tower_code'] = vals['tower_code'].upper()
            towers = super().create(vals_list)
            for tower in towers:
                if tower.floor_count and not tower.floor_line_ids:
                    tower._onchange_floor_count()
            return towers
        else:
            if vals_list.get('tower_name'):
                vals_list['tower_name'] = vals_list['tower_name'].upper()
            if vals_list.get('tower_code'):
                vals_list['tower_code'] = vals_list['tower_code'].upper()
            tower = super().create(vals_list)
            if tower.floor_count and not tower.floor_line_ids:
                tower._onchange_floor_count()
            return tower

    def write(self, vals):
        """Auto-capitalize text fields on write"""
        if vals.get('tower_name'):
            vals['tower_name'] = vals['tower_name'].upper()
        if vals.get('tower_code'):
            vals['tower_code'] = vals['tower_code'].upper()
        return super(ProjectSetupWizardTower, self).write(vals)

    @api.onchange('floor_count')
    def _onchange_floor_count(self):
        """Auto-generate floor lines when floor count changes"""
        if self.floor_count and self.floor_count > 0:
            # Only regenerate if count changed
            current_count = len(self.floor_line_ids)
            if current_count != self.floor_count:
                # Clear existing lines
                self.floor_line_ids = [(5, 0, 0)]

                # Generate new lines
                floor_lines = []
                for floor_num in range(1, self.floor_count + 1):
                    floor_lines.append((0, 0, {
                        'floor_number': floor_num,
                        'floor_name': self._get_floor_name(floor_num),
                        'units_per_floor': 4,  # Default 4 units
                    }))
                self.floor_line_ids = floor_lines

    def _get_floor_name(self, floor_num):
        """Generate floor name based on number"""
        if floor_num == 0:
            return 'Ground Floor'
        elif floor_num < 0:
            return f'Basement {abs(floor_num)}'
        elif floor_num == 1:
            return '1st Floor'
        elif floor_num == 2:
            return '2nd Floor'
        elif floor_num == 3:
            return '3rd Floor'
        else:
            return f'{floor_num}th Floor'

    def action_configure_floors(self):
        """Open floor configuration"""
        self.ensure_one()
        
        # Trigger onchange to regenerate floors if count changed
        self._onchange_floor_count()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Configure Floors - {self.tower_name}',
            'res_model': 'project.setup.wizard.floor',
            'view_mode': 'list,form',
            'domain': [('tower_id', '=', self.id)],
            'context': {
                'default_tower_id': self.id,
                'form_view_initial_mode': 'edit',
            },
            'target': 'new',
        }

    def action_refresh_floors(self):
        """Manually regenerate floors based on floor_count"""
        self.ensure_one()
        self._onchange_floor_count()
        # Return action to reload the wizard form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.setup.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }


class ProjectSetupWizardFloor(models.TransientModel):
    """Floor configuration line"""
    _name = 'project.setup.wizard.floor'
    _description = 'Floor Configuration'
    _order = 'floor_number'

    tower_id = fields.Many2one(
        'project.setup.wizard.tower',
        string='Tower',
        required=True,
        ondelete='cascade'
    )
    floor_number = fields.Integer(
        string='Floor Number',
        # required=True,
        help='Floor number (0=Ground, negative=Basement)'
    )
    floor_name = fields.Char(
        string='Floor Name',
        # required=True,
        help='e.g., 1st Floor, Ground Floor, Basement 1'
    )
    units_per_floor = fields.Integer(
        string='Units on This Floor',
        default=4,
        # required=True,
        help='How many units on this floor?'
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
    ], string='Unit Type',
        help='Leave empty to use default from wizard'
    )
    carpet_area = fields.Float(
        string='Carpet Area (sq.ft)',
        help='Leave empty to use default from wizard'
    )

    @api.constrains('units_per_floor')
    def _check_units(self):
        for floor in self:
            if floor.units_per_floor < 1 or floor.units_per_floor > 50:
                raise ValidationError(_('Units per floor must be between 1 and 50!'))

    @api.model
    def create(self, vals_list):
        """Auto-capitalize floor name on create"""
        if isinstance(vals_list, list):
            for vals in vals_list:
                if vals.get('floor_name'):
                    vals['floor_name'] = vals['floor_name'].upper()
        else:
            if vals_list.get('floor_name'):
                vals_list['floor_name'] = vals_list['floor_name'].upper()
        return super(ProjectSetupWizardFloor, self).create(vals_list)

    def write(self, vals):
        """Auto-capitalize floor name on write"""
        if vals.get('floor_name'):
            vals['floor_name'] = vals['floor_name'].upper()
        return super(ProjectSetupWizardFloor, self).write(vals)

    def action_back_to_wizard(self):
        """Navigate back to the project setup wizard"""
        self.ensure_one()
        # Get the wizard through tower -> wizard_id
        wizard = self.tower_id.wizard_id
        if wizard:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.setup.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }
        return {'type': 'ir.actions.act_window_close'}
