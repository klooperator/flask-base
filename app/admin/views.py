from flask import abort, flash, redirect, render_template, url_for, request, current_app
from flask_login import current_user, login_required
from flask_rq import get_queue
from werkzeug.utils import secure_filename

from .forms import (ChangeAccountTypeForm, ChangeUserEmailForm, InviteUserForm,
                    NewUserForm, AddNewDataForm, AddNewSite, AddNewNetworkForm)
from . import admin
from .. import db
from ..decorators import admin_required
from ..email import send_email
from ..models import Role, User, EditableHTML, Sites, Channels, UserData
import os
import csv
from datetime import datetime


@admin.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard page."""
    return render_template('admin/index.html')


@admin.route('/new-user', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """Create a new user."""
    form=NewUserForm()
    if form.validate_on_submit():
        user=User(
            role=form.role.data,
            first_name=form.first_name.data,
            email=form.email.data,
            password=form.password.data,
            confirmed=True)
        db.session.add(user)
        db.session.commit()
        flash('User {} successfully created'.format(user.full_name()),
              'form-success')
    return render_template('admin/new_user.html', form=form)

@admin.route('/add-network', methods=['GET', 'POST'])
@login_required
@admin_required
def add_network():
    """Create a new user."""
    form=AddNewNetworkForm()
    if form.validate_on_submit():
        channel=Channels(
            name=form.channel.data,
            public_name=form.channel_secret.data,
            is_visible=True)
        db.session.add(channel)
        db.session.commit()
        flash('User {} successfully created'.format(channel.getName()),
              'form-success')
    return render_template('admin/new_channel.html', form=form)


@admin.route('/invite-user', methods=['GET', 'POST'])
@login_required
@admin_required
def invite_user():
    """Invites a new user to create an account and set their own password."""
    form=InviteUserForm()
    if form.validate_on_submit():
        user=User(
            role=form.role.data,
            first_name=form.first_name.data,
            # last_name=form.last_name.data,
            email=form.email.data)
        db.session.add(user)
        db.session.commit()
        token=user.generate_confirmation_token()
        invite_link=url_for(
            'account.join_from_invite',
            user_id=user.id,
            token=token,
            _external=True)
        get_queue().enqueue(
            send_email,
            recipient=user.email,
            subject='You Are Invited To Join',
            template='account/email/invite',
            user=user,
            invite_link=invite_link, )
        flash('User {} successfully invited'.format(user.full_name()),
              'form-success')
    return render_template('admin/new_user.html', form=form)


@admin.route('/users')
@login_required
@admin_required
def registered_users():
    """View all registered users."""
    users=User.query.all()
    roles=Role.query.all()
    return render_template(
        'admin/registered_users.html', users=users, roles=roles)


@admin.route('/user/<int:user_id>')
@admin.route('/user/<int:user_id>/info')
@login_required
@admin_required
def user_info(user_id):
    """View a user's profile."""
    user=User.query.filter_by(id=user_id).first()
    sites=Sites.query.filter_by(user_id=user_id).all()
    if user is None:
        abort(404)
    return render_template('admin/manage_user.html', user=user, sites=sites)


@admin.route('/user/<int:user_id>/change-email', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_email(user_id):
    """Change a user's email."""
    user=User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    form=ChangeUserEmailForm()
    if form.validate_on_submit():
        user.email=form.email.data
        db.session.add(user)
        db.session.commit()
        flash('Email for user {} successfully changed to {}.'
              .format(user.full_name(), user.email), 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)

#################################################
#                                               #
#               Cretate directory and path      #
#                                               #
#################################################
def network_file_path(network):
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'],network)
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    return file_path
    #return (file_path + '/' + network)

#################################################
#                                               #
#               To DATE                         #
#                                               #
#################################################

def parse_date(dateString, format):
    return datetime.strptime(dateString, format).date()

#################################################
#                                               #
#               Data parser                     #
#                                               #
#################################################
def file_parser(network, file, site):
    if network == '33across':
        return parse_33across(os.path.join(network_file_path(network),file), site)

def parse_33across(file, site):
    
    date_format = '%Y-%m-%d'
    """ifile  = open(os.path.join(current_app.config['UPLOAD_FOLDER']) + '/' + file, 'rt')
    reader = csv.DictReader(next(ifile), delimiter=',')"""
    with open(file) as csvfile:
        next(csvfile)
        reader=csv.DictReader(csvfile)
        # next(reader)
        data = {}
        for line in reader:
            if line['Login'].lower()==site.lower():
                data_str = str(line['Date'])
                #print(data_str)
                date = parse_date(data_str, date_format)
                revenue=0
                if data_str in data:
                    revenue = data[data_str]['revenue'] + float(line['Estimated Revenue'].replace('$', ''))
                    #print('IS')
                else:
                    #data[data_str] = {'revenue': float(line['Estimated Revenue'].replace('$', ''))}
                    revenue = float(line['Estimated Revenue'].replace('$', ''))
                data[data_str] = {'revenue':revenue, 'day':date}
                #print(data)
            else:
                print('not site...:::' + line['Login'].lower())
    return data

#################################################
#                                               #
#               Add Data                        #
#                                               #
#################################################
@admin.route('/user/<int:user_id>/add-data', methods=['GET', 'POST'])
@login_required
@admin_required
def add_data(user_id):
    txt=0
    #data=''
    """Change a user's email."""
    user=User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)

    query=db.session.query(Sites).filter_by(user_id=user_id)
    form=AddNewDataForm()
    form.site.query=query

    if form.validate_on_submit():
        # return'success' + str(request.files)
        network = form.network.data.name
        if request.method == 'POST':
            if 'upload' not in request.files:
                flash('no file')
                return 'fail'
            """else:
                return 'success'"""
            file=request.files['upload']
            filename=secure_filename(file.filename)

            """file.save(os.path.join(current_app.config[
                      'UPLOAD_FOLDER'], filename))"""
            file.save(os.path.join(network_file_path(network),filename))
            
            data=file_parser(network, filename,form.site.data.link)
            for k in data:
                print(txt)
                txt += 1
                q = UserData.query.filter_by(day=data[k]['day']).filter_by(site=form.site.data.id).first()
                #print(type(q))
                #print(q.revenue)
                if not q:
                    to_db = UserData(
                            user_id=user_id,
                            day=data[k]['day'],
                            channel = form.network.data.id,
                            site = form.site.data.id,
                            #country = '',
                            #position = '',
                            revenue = data[k]['revenue']
                            )
                    db.session.add(to_db)
                else:
                    print('exists...')
            db.session.commit()


    return render_template('admin/manage_user.html', user=user, form=form, txt=txt)

#################################################
#                                               #
#               Add Site                        #
#                                               #
#################################################
@admin.route('/user/<int:user_id>/add-site', methods=['GET', 'POST'])
@login_required
@admin_required
def add_site(user_id):
    """Change a user's email."""
    user=User.query.filter_by(id=user_id).first()
    # site.user_id = user_id
    if user is None:
        abort(404)
    form=AddNewSite()
    if form.validate_on_submit():
        site=Sites(
            user_id=user_id,
            link=form.site.data)
        db.session.add(site)
        db.session.commit()
    return render_template('admin/manage_user.html', user=user, form=form)
##########################################################################


@admin.route(
    '/user/<int:user_id>/change-account-type', methods=['GET', 'POST'])
@login_required
@admin_required
def change_account_type(user_id):
    """Change a user's account type."""
    if current_user.id == user_id:
        flash('You cannot change the type of your own account. Please ask '
              'another administrator to do this.', 'error')
        return redirect(url_for('admin.user_info', user_id=user_id))

    user=User.query.get(user_id)
    if user is None:
        abort(404)
    form=ChangeAccountTypeForm()
    if form.validate_on_submit():
        user.role=form.role.data
        db.session.add(user)
        db.session.commit()
        flash('Role for user {} successfully changed to {}.'
              .format(user.full_name(), user.role.name), 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)


@admin.route('/user/<int:user_id>/delete', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_user_request(user_id):
    """Request deletion of a user's account."""
    user=User.query.filter_by(id=user_id).first()
    # sites = Sites.query.filter_by(user_id=user_id).all()
    req='nista novo'
    if user is None:
        abort(404)
    if request.method == 'POST':
        req=request.values['site']
        sites=Sites.query.filter_by(
            user_id=user_id).filter_by(link=req).all()
        for s in sites:
            db.session.delete(s)
        # db.session.delete(sites)
        db.session.commit()
    sites=Sites.query.filter_by(user_id=user_id).all()

    return render_template('admin/manage_user.html', user=user, sites=sites)


@admin.route('/user/<int:user_id>/_delete')
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user's account."""
    if current_user.id == user_id:
        flash('You cannot delete your own account. Please ask another '
              'administrator to do this.', 'error')
    else:
        user=User.query.filter_by(id=user_id).first()
        db.session.delete(user)
        db.session.commit()
        flash('Successfully deleted user %s.' % user.full_name(), 'success')
    return redirect(url_for('admin.registered_users'))


@admin.route('/_update_editor_contents', methods=['POST'])
@login_required
@admin_required
def update_editor_contents():
    """Update the contents of an editor."""

    edit_data=request.form.get('edit_data')
    editor_name=request.form.get('editor_name')

    editor_contents=EditableHTML.query.filter_by(
        editor_name=editor_name).first()
    if editor_contents is None:
        editor_contents=EditableHTML(editor_name=editor_name)
    editor_contents.value=edit_data

    db.session.add(editor_contents)
    db.session.commit()

    return 'OK', 200
