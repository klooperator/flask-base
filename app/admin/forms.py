from flask_wtf import Form
from wtforms import ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import PasswordField, StringField, SubmitField
from wtforms.fields.html5 import EmailField
from wtforms.validators import Email, EqualTo, InputRequired, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired


from .. import db
from ..models import Role, User, Sites, Channels


class ChangeUserEmailForm(Form):
    email = EmailField(
        'New email', validators=[InputRequired(), Length(1, 64), Email()])
    submit = SubmitField('Update email')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

#################################################
#                                               #
#               AddNewDataForm                  #
#                                               #
#################################################
class AddNewDataForm(Form):

    site = QuerySelectField(
        'Site',
        validators=[InputRequired()],
        get_label='link')

    network = QuerySelectField(
        'Network',
        #validators=[InputRequired()],
        get_label='name',
        query_factory=lambda: db.session.query(Channels))

    upload = FileField('file', validators=[
        FileRequired()
    ])
    submit = SubmitField('Add')

#################################################
#                                               #
#               AddNewSiteForm                  #
#                                               #
#################################################
class AddNewSite(Form):
    site = StringField(
        'New site', validators=[InputRequired(), Length(1, 64)])
    submit = SubmitField('Add')

    def validate_site(self, field):
        if Sites.query.filter_by(link=field.data).first():
            raise ValidationError('Site already exists.') 

#################################################
#                                               #
#               AddNewNetworkForm               #
#                                               #
#################################################
class AddNewNetworkForm(Form):
    channel = StringField(
        'Channel name', validators=[InputRequired(), Length(1, 64)])
    channel_secret = StringField(
        'Channel public name', validators=[InputRequired(), Length(1, 64)])
    submit = SubmitField('Add')

    def validate_site(self, field):
        if Channels.query.filter_by(name=field.data).first():
            raise ValidationError('Site already exists.') 

class ChangeAccountTypeForm(Form):
    role = QuerySelectField(
        'New account type',
        validators=[InputRequired()],
        get_label='name',
        query_factory=lambda: db.session.query(Role).order_by('permissions'))
    submit = SubmitField('Update role')


class InviteUserForm(Form):
    user_id = ''
    def setUser(self, user_id):
        self.user_id=user_id
    role = QuerySelectField(
        'For site: ' + user_id,
        validators=[InputRequired()],
        get_label='email',
        query_factory=lambda: db.session.query(User))
    first_name = StringField(
        'First name', validators=[InputRequired(), Length(1, 64)])
    # last_name = StringField(
        # 'Last name', validators=[InputRequired(), Length(1, 64)])
    email = EmailField(
        'Email', validators=[InputRequired(), Length(1, 64), Email()])
    submit = SubmitField('Invite')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class AddNewUserHelper(Form):
    role = QuerySelectField(
        'Account type',
        validators=[InputRequired()],
        get_label='name',
        query_factory=lambda: db.session.query(Role).order_by('permissions'))
    first_name = StringField(
        'First name', validators=[InputRequired(), Length(1, 64)])
    email = EmailField(
        'Email', validators=[InputRequired(), Length(1, 64), Email()])
    submit = SubmitField('Invite')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class NewUserForm(AddNewUserHelper):
    password = PasswordField(
        'Password',
        validators=[
            InputRequired(), EqualTo('password2', 'Passwords must match.')
        ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])

    submit = SubmitField('Create')


