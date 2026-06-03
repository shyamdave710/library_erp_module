# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import SQL

class LibraryBook(models.Model):
    # MODEL IDENTITY
    _name = 'library.book'          # becomes DB table: library_book
    _description = 'Library Book'
    _order = 'name asc'             # default sort: alphabetical
    _rec_name = 'name'              # which field shows as the record's display name
    _inherit = ['mail.thread','mail.activity.mixin'] # for tracking purpose

    # Basic fields (Used mostly)

    name = fields.Char(
        string='Book Title',
        required=True,              # cannot  be empty
        size=200,                   # max characters
        index=True,                 # creates DB index - faster searching
        tracking=True,              # logs changes in Chatter

    )

    book_id = fields.Char(
        string='Book ID',
        readonly=True,
        copy=False,
        default='New',
    )

    isbn = fields.Char(
        string='ISBN',
        size=20,
        copy=False,                 # when duplicating record, this field is cleared
    )

    author = fields.Char(
        string = 'Author Name',
        required= True,
        tracking= True,
    )

    description = fields.Text(      # Text = multiline, char = Single line
        string = 'Description / Synopsis',
        help= 'Brief description of the book content', # tooltip show to  user
    )

    total_pages = fields.Integer(
        string= 'Total Pages',
        default= 0,
    )

    price = fields.Float(
        string= 'Book Price (₹)',
        digits= (10,2),              # (total digits, decimal places)
    )

    published_date = fields.Date(
        string= "Published Date",
    )

    date_added = fields.Datetime(
        string= "Added to Library",
        default= fields.Datetime.now(), # auto-set to current datetime on create
        readonly=True,                  # user cannot edit this field
    )

    cover_image = fields.Binary(
        string='Cover Image',
        attachment=True,                # stores as attachments, not in DB Column
    )

    cover_image_filename = fields.Char( # binary needs a companion filename field
        string="Cover Name"
    )

    notes = fields.Html(                # Html = rich text editor (bold, italic, etc.)
        string = 'Internal Notes'
    )

    # ------- SELECTION FIELD --------------------------
    # Like a dropdown - value stored in DB, label shown to user

    genre = fields.Selection(
        selection = [
            ('Fiction','Fiction'),
            ('Non-Fiction','Non-Fiction'),
            ('Science & Technology', 'Science & Technology'),
            ('History', 'History'),
            ('Biography', 'Biography'),
            ("Children's  Books", "Children's  Books"),
            ('Reference','Reference'),
            ('Academic / Textbook','Academic / Textbook'),
        ],
        string = 'Genre',
        required=True,
        default='Fiction',
        tracking=True,
    )

    language = fields.Selection(
        selection=[
            ('english', 'English'),
            ('hindi', 'Hindi'),
            ('gujarati', 'Gujarati'),
            ('other', 'Other'),
        ],
        string="Language",
        default='english',
    )

    # ---------- BOOLEAN FIELDS ----------------------------

    is_available = fields.Boolean(
        string = 'Available for Issue',
        default = True,
        tracking = True,
    )

    is_reference_only = fields.Boolean(
        string='Reference Only (Cannot be issued)',
        default = False,
        help = 'Reference books can be read inside library only, not taken home',
    )


    # ----------- RELATIONAL FIELDS ----------------------------

    # Many2one = Many books -> one rack
    rack_id = fields.Many2one(
        comodel_name='library.rack',         # links to library.rack model
        string = 'Rack/Shelf Location',
        ondelete="set null",                 # if rack deleted, set this field to empty
    )

    # Many2many = Many books <-> Many tags
    tag_ids = fields.Many2many(
        comodel_name='library.book.tag',      # links to library.book.tag model
        string="Tags",
        help="e.g: Bestseller, Award Winner, New Arrival",
    )

    # One2many = One book -> Many issue records
    issue_ids = fields.One2many(
        comodel_name='library.issue',       # links  to library.issue model
        inverse_name='book_id',             # the Many2one field on library.issue
        string='Issue History',
        readonly=True,
    )


    # -------- COMPUTED FIELDS ----------------------------
    #  These are the calculated automatically - NOT stored by user

    total_issue = fields.Integer(
        string='Total Times Issued',
        compute='_compute_total_issues',       # point to method below
        store=True,                             # store=True saves in DB (Faster read)
                                                # store=False computes on every read
    )

    @api.depends('issue_ids')                   # recalculate when issue_ids changes
    def _compute_total_issues(self):
        # 'self' is a RECORDSET - could be 1 record or 1000 records
        # always loop with 'for record in self'
        for record in self:
            record.total_issue = len(record.issue_ids)


    # ----------- SEQUENCE FIELD --------------------------
    # auto-generates : LIB/BK/0001, LIB/BK/0002, etc.

    reference = fields.Char(
        string='Book Reference',
        readonly=True,
        copy=False,
        default='New',
    )

    # ----- ORM OVERRIDE: create() ------------------------
    # called automatically every time a new book record is created

    @api.model
    def create(self, vals):
        # generate  reference number using ir.sequence
        if vals.get('reference', 'New')=='New':
            vals['reference']=self.env['ir.sequence'].next_by_code(
                'library.book.sequence'
            ) or 'LIB/BK/0001'

        # call the original create() to actually save the record
        return super(LibraryBook, self).create(vals)


    # ---------------- CONSTRAINT: VALIDATION ------------------------
    # Runs on create AND write (save). Raises error if condition fails.

    @api.constrains('total_pages')
    def _check_total_pages(self):
        for record in self:
            if record.total_pages < 0:
                raise ValidationError(
                    "Total pages cannot be negative..!!"
                    f"You entered {record.total_pages} for '{record.name}"
                )


    # ---------- SQL CONSTRAINT --------------------------
    # Enforced at DATABASE level - Faster, bulletproof

    # _sql_constraints = [
    #     (
    #         'isbn_unique',                  # constraint name
    #         'UNIQUE(isbn)',                 # SQL constraint
    #         'This ISBN already exists. Each book must have a unique  ISBN.',        # error message
    #     )
    # ]

    _isbn_unique = models.Constraint(
        'UNIQUE(isbn)',
        'This ISBN already exists. Each book must have a unique ISBN.',
    )

    # ------------ NAME DISPLAY -------------------------
    # controls how this record appears in dropdown/search fields

    def name_get(self):
        result=[]
        for record in self:
            name=f"[{record.reference}] {record.name}"
            if record.author:
                name += f" - {record.author}"
            result.append((record.id, name))

        return result


# ---------- SUPPORTING MODELS -----------------------

class LibraryRack(models.Model):
    """Physical location of books in  the library"""
    _name = 'library.rack'
    _description = "Library Rack / Shelf"
    _order = 'name'

    name = fields.Char(string="Rack name", required=True)
    # e.g: "Section A - Shelf - 3", "Ground Floor - Fiction"

    location_description = fields.Text(string="Location Description")

    book_id = fields.One2many(
        comodel_name="library.book",
        inverse_name='rack_id',
        string='Books on this Rack'
    )

    book_count = fields.Integer(
        string='Number of Books',
        compute='_compute_book_count',
        store=True,
    )

    @api.depends('book_id')
    def _compute_book_count(self):
        for record in self:
            record.book_count = len(record.book_id)


class LibraryBookTags(models.Model):
    """"Tags/Labels  for books like 'Bestseller', 'New Arrival' """

    _name = "library.book.tag"
    _description = 'Book Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string="Color Index")            # odoo's 0-11 color palette