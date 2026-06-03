# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class LibraryIssue(models.Model):
    _name = 'library.issue'
    _description = 'Book Issue Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc'   # newest issues shown first
    _rec_name = 'reference'

    # ── IDENTITY ──────────────────────────────────────────────────
    reference = fields.Char(
        string='Issue Reference',
        readonly=True,
        copy=False,
        default='New',
    )

    # ── THE KEY RELATIONS ─────────────────────────────────────────

    book_id = fields.Many2one(
        # ↑ THIS is what book.py's One2many is waiting for
        # inverse_name='book_id' on book.issue_ids points HERE
        comodel_name='library.book',
        string='Book',
        required=True,
        tracking=True,
        ondelete='restrict',
        # ondelete='restrict' means:
        # if someone tries to DELETE a book that has issue records
        # Odoo will BLOCK the deletion and show an error
        # This protects your data integrity
        domain="[('is_available', '=', True), ('is_reference_only', '=', False)]",
        # domain= filters the dropdown
        # When librarian clicks Book field dropdown
        # it ONLY shows books that are: available AND not reference-only
        # User cannot accidentally issue a book that's already issued
    )

    member_id = fields.Many2one(
        comodel_name='library.member',
        string='Member',
        required=True,
        tracking=True,
        ondelete='restrict',
    )

    # ── DATES ─────────────────────────────────────────────────────
    issue_date = fields.Date(
        string='Issue Date',
        default=fields.Date.today,
        required=True,
        tracking=True,
    )

    due_date = fields.Date(
        string='Due Date',
        required=True,
        tracking=True,
    )

    return_date = fields.Date(
        string='Actual Return Date',
        tracking=True,
        readonly=True,
    )

    # ── STATE MACHINE ─────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft',    'Draft'),
            ('issued',   'Issued'),
            ('returned', 'Returned'),
            ('overdue',  'Overdue'),
            ('lost',     'Lost'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    # ── FINE CALCULATION ──────────────────────────────────────────
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_fine',
        store=True,
    )

    fine_amount = fields.Float(
        string='Fine Amount (₹)',
        compute='_compute_fine',
        store=True,
        digits=(10, 2),
    )

    fine_per_day = fields.Float(
        string='Fine Per Day (₹)',
        default=2.0,
        help='Fine charged per day after due date',
    )

    fine_paid = fields.Boolean(
        string='Fine Paid',
        default=False,
        tracking=True,
    )

    @api.depends('due_date', 'return_date', 'state')
    def _compute_fine(self):
        for record in self:
            if not record.due_date:
                record.days_overdue = 0
                record.fine_amount = 0.0
                continue
                # 'continue' skips to next record in the loop
                # like 'pass' but for loops — moves to next iteration

            # Use return_date if returned, otherwise use today
            check_date = record.return_date or date.today()

            if check_date > record.due_date:
                delta = check_date - record.due_date
                record.days_overdue = delta.days
                record.fine_amount = delta.days * record.fine_per_day
            else:
                record.days_overdue = 0
                record.fine_amount = 0.0

    notes = fields.Text(string='Notes')

    # ── ISSUE DATE AUTO-SET DUE DATE ──────────────────────────────
    @api.onchange('issue_date')
    def _onchange_issue_date(self):
        # When librarian sets issue_date,
        # auto-calculate due_date as 14 days later
        if self.issue_date:
            self.due_date = self.issue_date + timedelta(days=14)
            # This runs in the BROWSER — before saving
            # User sees due_date fill automatically as they pick issue_date

    # ── VALIDATION ────────────────────────────────────────────────
    @api.constrains('member_id', 'state')
    def _check_member_book_limit(self):
        for record in self:
            if record.state == 'issued':
                member = record.member_id
                # Check how many books this member currently has
                active_issues = self.search_count([
                    ('member_id', '=', member.id),
                    ('state', '=', 'issued'),
                    ('id', '!=', record.id),  # exclude current record
                ])
                if active_issues >= member.max_books_allowed:
                    raise ValidationError(
                        f"Member '{member.name}' has already borrowed "
                        f"{active_issues} book(s). "
                        f"Maximum allowed: {member.max_books_allowed}."
                    )

    @api.constrains('book_id')
    def _check_book_not_reference(self):
        for record in self:
            if record.book_id.is_reference_only:
                raise ValidationError(
                    f"'{record.book_id.name}' is a Reference Only book "
                    f"and cannot be issued."
                )

    # ══════════════════════════════════════════════════════════════
    # STATE MACHINE BUTTON METHODS
    # Each method moves the record from one state to another
    # Called when user clicks the button in the form header
    # ══════════════════════════════════════════════════════════════

    def action_issue(self):
        """Draft → Issued"""
        for record in self:
            # Guard: only allow from draft state
            if record.state != 'draft':
                raise UserError(
                    "Only Draft records can be issued."
                )

            # Check book is still available
            if not record.book_id.is_available:
                raise UserError(
                    f"Book '{record.book_id.name}' is no longer available."
                )

            # Move to issued state
            record.state = 'issued'

            # Mark the book as unavailable
            record.book_id.is_available = False

            # Log in chatter
            record.message_post(
                body=f"Book issued to <b>{record.member_id.name}</b>. "
                     f"Due date: <b>{record.due_date}</b>",
                message_type='notification',
            )

    def action_return(self):
        """Issued/Overdue → Returned"""
        for record in self:
            if record.state not in ('issued', 'overdue'):
                raise UserError(
                    "Only Issued or Overdue books can be returned."
                )

            record.state = 'returned'
            record.return_date = date.today()

            # Mark the book as available again
            record.book_id.is_available = True

            # Log in chatter
            msg = f"Book returned by <b>{record.member_id.name}</b>."
            if record.fine_amount > 0:
                msg += f" Fine: <b>₹{record.fine_amount:.2f}</b>"
                if not record.fine_paid:
                    msg += " (Unpaid)"
            record.message_post(body=msg, message_type='notification')

    def action_mark_lost(self):
        """Issued/Overdue → Lost"""
        for record in self:
            if record.state not in ('issued', 'overdue'):
                raise UserError(
                    "Only Issued or Overdue books can be marked as lost."
                )
            record.state = 'lost'
            # Book remains unavailable since it's lost
            record.message_post(
                body=f"Book marked as <b>LOST</b> by {record.member_id.name}.",
                message_type='notification',
            )

    def action_mark_overdue(self):
        """Issued → Overdue (called by cron job later)"""
        for record in self:
            if record.state == 'issued' and record.due_date < date.today():
                record.state = 'overdue'

    def action_reset_draft(self):
        """Any state → Draft (for corrections, admin only)"""
        for record in self:
            # If we're resetting from issued state,
            # make the book available again
            if record.state == 'issued':
                record.book_id.is_available = True
            record.state = 'draft'
            record.return_date = False

    # ── ORM OVERRIDE ──────────────────────────────────────────────
    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'library.issue.sequence'
            ) or 'LIB/ISS/0001'
        return super().create(vals)