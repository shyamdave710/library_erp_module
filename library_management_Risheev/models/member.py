# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class LibraryMember(models.Model):
    _name='library.member'
    _description = "Library Member"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    #  ---- IDENTITY ------
    name = fields.Char(
        string='Member Name',
        required= True,
        tracking=True,
    )
    member_id= fields.Char(
        string='Member ID',
        readonly=True,
        copy=False,
        default='New',
    )
    photo = fields.Binary(
        string='Photo',
        attachment=True,
    )
    photo_filename=fields.Char()

    # ------ PERSONAL INFO ------------
    email = fields.Char(string='Email', tracking=True)
    phone=fields.Char(string='Phone')
    date_of_birth = fields.Date(string="Date of Birth")

    # Link this member record to an odoo user account
    #  This is what record rules use to indentify "current logged-in member"
    user_id = fields.Many2one(
        comodel_name='res.users',
        string = 'Portal User Account',
        help = 'Link this member to their odoo login account.\nRequired for member portal access and record rules.',
        copy=False,
    )

    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
    )
    @api.depends('date_of_birth')
    def _compute_age(self):
        for record in self:
            if record.date_of_birth:
                today= date.today()
                record.age= today.year - record.date_of_birth.year
            else:
                record.age=0

    # ------ MEMBERSHIP ------------
    membership_type = fields.Selection(
        selection=[
            ('student', 'Student'),
            ('faculty', 'Faculty'),
            ('staff', 'Staff'),
            ('public', 'Public Member'),
        ],
        string="Membership Type",
        required=True,
        default='student',
        tracking = True,
    )

    membership_start = fields.Date(
        string='Membership Start',
        default=fields.Date.today,
    )

    membership_end= fields.Date(
        string = 'Membership End',
        tracking=True,
    )

    is_expired = fields.Boolean(
        string='Membership Expired',
        compute='_compute_is_expired',
        store=True,
    )

    @api.depends('membership_end')
    def _compute_is_expired(self):
        for record in self:
            if record.membership_end:
                record.is_expired= record.membership_end < date.today()
            else:
                record.is_expired = False

    max_books_allowed = fields.Integer(
        string='Max Books Allowed',
        default=3,
        help = "Maximum number of books the member can borrow at one time",
    )

    # ---- RELATED ISSUES --------------
    issue_ids = fields.One2many(
        comodel_name='library.issue',
        inverse_name='member_id',
        string='Issue History',
    )

    active_issue_count = fields.Integer(
        string="Books Currently Borrowed",
        compute='_compute_active_issue_count',
        store=True,
    )

    @api.depends('issue_ids', 'issue_ids.state')
    def _compute_active_issue_count(self):
        for record in self:
            record.active_issue_count=len(
                record.issue_ids.filtered(
                    lambda i: i.state == 'issued'
                )
            )

    # ----------- ORM OVERRIDE -----------------
    @api.model
    def create(self, vals):
        if vals.get('member_id', 'New')=='New':
            vals['member_id']=self.env['ir.sequence'].next_by_code(
                'library.member.sequence'
            ) or 'LIB/MEM/0001'
        return super().create(vals)

    # -------- CONSTRAINT --------------------
    @api.constrains('membership_end', 'membership_start')
    def _check_membership_dates(self):
        for record in self:
            if record.membership_end and record.membership_start:
                if record.membership_end < record.membership_start:
                    raise ValidationError(
                        "Membership end date cannot be before start date!"
                    )