# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import hashlib


class DprEmployee(models.Model):
    _name = 'dpr.employee'
    _description = 'DPR Employee for Mobile Authentication'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Employee Name',
        required=True,
        tracking=True
    )
    employee_code = fields.Char(
        string='Employee Code',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    hr_employee_id = fields.Many2one(
        'hr.employee',
        string='Odoo Employee',
        tracking=True,
        help='Link to Odoo HR Employee'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Linked Odoo User',
        compute='_compute_user_id',
        store=True,
        readonly=False
    )
    phone = fields.Char(
        string='Phone Number',
        required=True
    )
    email = fields.Char(
        string='Email Address'
    )
    designation = fields.Char(
        string='Designation'
    )
    department = fields.Char(
        string='Department'
    )
    mobile_login_enabled = fields.Boolean(
        string='Mobile Login Enabled',
        default=False,
        tracking=True
    )
    pin = fields.Char(
        string='Mobile PIN',
        size=6,
        help='4-6 digit PIN for mobile app authentication',
        copy=False
    )
    pin_hash = fields.Char(
        string='PIN Hash',
        readonly=True,
        copy=False
    )
    project_ids = fields.Many2many(
        'dpr.project',
        string='Assigned Projects'
    )
    access_ids = fields.One2many(
        'dpr.employee.access',
        'employee_id',
        string='Access Control',
        help='Define which towers/floors/units this employee can access'
    )
    hourly_rate = fields.Float(
        string='Default Hourly Rate'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    auth_token = fields.Char(
        string='Authentication Token',
        readonly=True,
        copy=False
    )
    token_expiry = fields.Datetime(
        string='Token Expiry',
        readonly=True
    )
    last_login = fields.Datetime(
        string='Last Login',
        readonly=True
    )
    login_count = fields.Integer(
        string='Login Count',
        default=0
    )
    photo = fields.Binary(
        string='Photo',
        attachment=True,
        help='Employee photo. This field can be set manually or automatically populated when HR Employee is selected.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company.id if self.env.company else False,
        required=True,
        tracking=True,
        help='Company associated with this employee'
    )

    _uniques = [
        ('code_unique', 'UNIQUE(employee_code)', 'Employee code must be unique!'),
        ('phone_unique', 'UNIQUE(phone)', 'Phone number must be unique!'),
        ('pin_length', 'CHECK(pin IS NULL OR LENGTH(pin) >= 4)',
         'PIN must be at least 4 digits!'),
    ]

    @api.depends('hr_employee_id')
    def _compute_user_id(self):
        """Auto-fill user_id from hr_employee_id"""
        for employee in self:
            if employee.hr_employee_id and employee.hr_employee_id.user_id:
                employee.user_id = employee.hr_employee_id.user_id.id
            elif employee.hr_employee_id:
                # Try to match by email
                if employee.hr_employee_id.work_email:
                    user = self.env['res.users'].search([('email', '=', employee.hr_employee_id.work_email)], limit=1)
                    if user:
                        employee.user_id = user.id

    @api.onchange('hr_employee_id')
    def _onchange_hr_employee_id(self):
        """Auto-fill fields from hr_employee_id"""
        if self.hr_employee_id:
            self.name = self.hr_employee_id.name
            self.email = self.hr_employee_id.work_email
            self.phone = self.hr_employee_id.work_phone or self.hr_employee_id.mobile_phone
            self.designation = self.hr_employee_id.job_title
            if self.hr_employee_id.department_id:
                self.department = self.hr_employee_id.department_id.name
            if self.hr_employee_id.user_id:
                self.user_id = self.hr_employee_id.user_id.id
            # Copy photo from hr_employee_id if available
            if self.hr_employee_id.image_1024:
                self.photo = self.hr_employee_id.image_1024
            # Copy company from hr_employee_id if available
            if self.hr_employee_id.company_id:
                self.company_id = self.hr_employee_id.company_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_code', _('New')) == _('New'):
                vals['employee_code'] = self.env['ir.sequence'].next_by_code('dpr.employee')
        return super().create(vals_list)

    def _encrypt_pin(self, pin):
        """Encrypt PIN using SHA256"""
        if not pin:
            return False
        return hashlib.sha256(pin.encode()).hexdigest()

    @api.onchange('pin')
    def _onchange_pin(self):
        """Auto-encrypt PIN when changed"""
        if self.pin:
            self.pin_hash = self._encrypt_pin(self.pin)
        else:
            self.pin_hash = False

    def set_pin(self, pin):
        """Set employee PIN (encrypted)"""
        self.ensure_one()
        self.write({
            'pin': '',  # Don't store raw PIN
            'pin_hash': self._encrypt_pin(pin)
        })

    def verify_pin(self, pin):
        """Verify PIN against stored hash"""
        self.ensure_one()
        if not self.pin_hash or not self.mobile_login_enabled:
            return False
        return self.pin_hash == self._encrypt_pin(pin)

    def generate_auth_token(self):
        """Generate new authentication token"""
        self.ensure_one()
        import secrets
        from datetime import timedelta
        token = secrets.token_urlsafe(32)
        expiry = fields.Datetime.now() + timedelta(hours=24)
        self.write({
            'auth_token': token,
            'token_expiry': expiry,
            'last_login': fields.Datetime.now(),
            'login_count': self.login_count + 1
        })
        return token

    def invalidate_token(self):
        """Invalidate current auth token"""
        self.ensure_one()
        self.write({
            'auth_token': False,
            'token_expiry': False
        })

    def is_token_valid(self):
        """Check if auth token is valid and not expired"""
        self.ensure_one()
        if not self.auth_token or not self.token_expiry:
            return False
        return fields.Datetime.now() < self.token_expiry

    @api.constrains('phone')
    def _check_phone(self):
        for employee in self:
            if employee.phone:
                # Remove spaces and special characters
                phone = ''.join(filter(str.isdigit, employee.phone))
                if len(phone) < 10:
                    raise ValidationError(_('Phone number must be at least 10 digits!'))

    @api.constrains('pin')
    def _check_pin(self):
        for employee in self:
            if employee.pin:
                if not employee.pin.isdigit():
                    raise ValidationError(_('PIN must contain only digits!'))
                if len(employee.pin) < 4:
                    raise ValidationError(_('PIN must be at least 4 digits!'))

    def action_enable_mobile_login(self):
        self.mobile_login_enabled = True

    def action_disable_mobile_login(self):
        self.mobile_login_enabled = False
        self.invalidate_token()

    def action_reset_pin(self):
        """Reset PIN to null"""
        self.write({
            'pin': '',
            'pin_hash': ''
        })

    def name_get(self):
        result = []
        for employee in self:
            name = f"{employee.employee_code} - {employee.name}"
            result.append((employee.id, name))
        return result

    def get_accessible_tasks(self):
        """Get tasks that this employee can access based on access control settings.
        
        Returns:
            Recordset of dpr.task that the employee can access
        """
        self.ensure_one()
        
        # If no access rules, return empty
        if not self.access_ids:
            return self.env['dpr.task']
        
        accessible_tasks = self.env['dpr.task']
        
        for access in self.access_ids.filtered(lambda a: a.active):
            # If project selected but no tower, get all tasks in project
            if not access.tower_id:
                accessible_tasks |= access.project_id.task_ids
            
            # If tower selected but no floor, get tower and all its children
            elif access.tower_id and not access.floor_id:
                accessible_tasks |= access.tower_id
                accessible_tasks |= access.tower_id.child_ids
            
            # If floor selected but no unit, get floor and all its children
            elif access.floor_id and not access.unit_id:
                accessible_tasks |= access.floor_id
                accessible_tasks |= access.floor_id.child_ids
            
            # If unit selected, get unit and all its children (activities)
            elif access.unit_id:
                accessible_tasks |= access.unit_id
                accessible_tasks |= access.unit_id.child_ids
        
        return accessible_tasks
