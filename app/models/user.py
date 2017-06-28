from flask import current_app
from flask_login import AnonymousUserMixin, UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import desc, asc, between
import json
from datetime import datetime, timedelta

from .. import db, login_manager


class Permission:
    GENERAL = 0x01
    ADMINISTER = 0xff


class Channels(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    public_name = db.Column(db.String(64))
    is_visible = db.Column(db.Boolean, default=True)

    def getName(self):
        return '%s' % (self.name)

    def __repr__(self):
        return ''


class Sites(db.Model):
    __tablename__ = 'user_sites'
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return ''


class UserData(db.Model):
    __tablename__ = 'user_earning'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day = db.Column(db.Date)
    channel = db.Column(db.Integer, db.ForeignKey('channels.id'))
    site = db.Column(db.Integer, db.ForeignKey('user_sites.id'))
    #country = db.Column(db.String(64),default='')
    #position= db.Column(db.String(64), default='')
    revenue = db.Column(db.Integer)

    def __repr__(self):
        return ''


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    index = db.Column(db.String(64))
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.GENERAL, 'main', True),
            'Administrator': (
                Permission.ADMINISTER,
                'admin',
                False  # grants all permissions
            )
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.index = roles[r][1]
            role.default = roles[r][2]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role \'%s\'>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    confirmed = db.Column(db.Boolean, default=False)
    first_name = db.Column(db.String(64), index=True)
    # last_name=db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['ADMIN_EMAIL']:
                self.role = Role.query.filter_by(
                    permissions=Permission.ADMINISTER).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def get_user_data(self):
        d = datetime.today() - timedelta(days=30)
        print(d)
        date_format = '%d-%m'
        date_labels = []
        for i in range(1, 31):
            date_labels.append((datetime.today() - timedelta(days=i)).strftime(date_format))
        user_sites = Sites.query.filter_by(user_id = self.id)
        out_dict = {
            "type": "line",
            "data": {
                "labels": list(reversed(date_labels)),
                "datasets": []
                }
        }
        colors = [
            "rgba(255, 99, 132, 0.9)",
            "rgba(23, 233, 76, 0.9)"
        ]

        site_count = 0


        for site in user_sites:
            user_data = reversed(UserData.query.filter_by(user_id=self.id).filter_by(site = site.id).order_by(UserData.day.desc()).limit(30).all()) 
            current_dataset = {
                "label": site.link,
                "data":[],
                "backgroundColor": "rgba(255, 255, 255, 0)",
                "borderColor": colors[site_count],
                "borderWidth": "1"
            }
            for row in user_data:
                if row.day.strftime(date_format) in date_labels:
                    current_dataset['data'].append(row.revenue)
                else:
                    current_dataset['data'].append(0)


            site_count += 1
            out_dict['data']['datasets'].append(current_dataset)

        """user_data = reversed(UserData.query.filter(UserData.day > d).filter_by(
            user_id=self.id).order_by(UserData.day.desc()).all())
        
        x_ = []
        y_ = []
        
        count = 0
        for row in user_data:
            date = row.day.strftime(date_format)
            if count > 0:
                if x_[count] != x_[count-1]:
                    x_.append(date)
                    y_.append(row.revenue)
                else:
                    y_[count-1] = y_[count-1] + row.revenue
            # if not y_[]
            # y_.append(row.revenue)
            #out_dict[date] = row.revenue
        # print(out_dict)
        count += 1
        out_dict = {
            "type": "line",
            "data": {
                "labels": x_,
                "datasets": [{
                    "label": "Revenue last 30 days",
                    "data": y_,
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgba(255,99,132,0.9)",
                    "borderWidth": "1",
                }]
            }
        }
        print(x_)"""
        # return out_dict
        # print(json.dumps(out_dict, ensure_ascii=False))
        return json.dumps(out_dict, ensure_ascii=False)

    def full_name(self):
        return '%s' % (self.first_name)

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_admin(self):
        return self.can(Permission.ADMINISTER)

    @property
    def password(self):
        raise AttributeError('`password` is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=604800):
        """Generate a confirmation token to email a new user."""

        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def generate_email_change_token(self, new_email, expiration=3600):
        """Generate an email change token to email an existing user."""
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def generate_password_reset_token(self, expiration=3600):
        """
        Generate a password reset change token to email to an existing user.
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def confirm_account(self, token):
        """Verify that the provided token is for this user's id."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except (BadSignature, SignatureExpired):
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def change_email(self, token):
        """Verify the new email for this user."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except (BadSignature, SignatureExpired):
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        db.session.commit()
        return True

    def reset_password(self, token, new_password):
        """Verify the new password for this user."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except (BadSignature, SignatureExpired):
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        db.session.commit()
        return True

    @staticmethod
    def generate_fake(count=100, **kwargs):
        """Generate a number of fake users for testing."""
        from sqlalchemy.exc import IntegrityError
        from random import seed, choice
        from faker import Faker

        fake = Faker()
        roles = Role.query.all()

        seed()
        for i in range(count):
            u = User(
                first_name=fake.first_name(),
                email=fake.email(),
                password=fake.password(),
                confirmed=True,
                role=choice(roles),
                **kwargs)
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __repr__(self):
        return '<User \'%s\'>' % self.full_name()


class AnonymousUser(AnonymousUserMixin):
    def can(self, _):
        return False

    def is_admin(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
