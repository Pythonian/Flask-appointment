from datetime import datetime

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   url_for, request)

from flask_bootstrap import Bootstrap
from flask_login import (LoginManager, current_user, UserMixin,
                         login_required, login_user, logout_user)
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import (BooleanField, DateTimeField, StringField, TextAreaField,
                     PasswordField, SubmitField)
from wtforms.validators import DataRequired, Length, Email, ValidationError

from filters import do_date, do_datetime, do_duration, do_nl2br

# Creates a Python object (WSGI) app
# The __name__ argument tells Flask to look at the current
# python module to find resources associated with the app
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.jinja_env.filters['date'] = do_date
app.jinja_env.filters['datetime'] = do_datetime
app.jinja_env.filters['duration'] = do_duration
app.jinja_env.filters['nl2br'] = do_nl2br

db = SQLAlchemy(app)
bootstrap = Bootstrap(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'
login_manager.login_message = 'Please login to access this page'
login_manager.login_message_category = 'info'


# Models

@login_manager.user_loader
def user_id(id):
    """Flask-Login hook to load a User instance from ID."""
    return User.query.get(int(id))


class User(db.Model, UserMixin):
    """A user login, with credentials and authentication."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(128))
    created = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def password(self):
        """
        Prevents password from being accessed
        """
        raise AttributeError('password is not a readable attribute.')

    @password.setter
    def password(self, password):
        """
        Set password to a hashed password
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        Check if hashed password matches actual password
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User: {self.email}>'


class Appointment(db.Model):
    """An appointment on the calendar."""
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship(User, lazy='joined', join_depth=1, viewonly=True)

    title = db.Column(db.String(255))
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    allday = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(255))
    description = db.Column(db.Text)

    @property
    def duration(self):
        """
        Calculate the length of the appointment, in seconds.
        """
        # If the datetime type were supported natively on all database
        # management systems (is not on SQLite), then this could be a
        # hybrid_property, where filtering clauses could compare
        # Appointment.duration. Without that support, we leave duration as an
        # instance property, where appt.duration is calculated for us.
        delta = self.end - self.start
        return delta.days * 24 * 60 * 60 + delta.seconds

    def __repr__(self):
        # <Appointment: 1>
        return (u'<{self.__class__.__name__}: {self.id}>'.format(self=self))


# Forms

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Email()])
    password = PasswordField()
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), Email()])
    password = PasswordField()
    confirm_password = PasswordField()
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("This email already exists.")


class AppointmentForm(FlaskForm):
    """Render HTML input for Appointment model & validate submissions.

    This matches the models.Appointment class very closely. Where
    models.Appointment represents the domain and its persistence, this class
    represents how to display a form in HTML & accept/reject the results.
    """
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=1, max=255)])
    start = DateTimeField('Start', validators=[DataRequired()])
    end = DateTimeField('End')
    allday = BooleanField('All Day')
    location = StringField('Location', validators=[Length(max=255)])
    description = TextAreaField('Description')
    submit = SubmitField('Submit')


# Views

@app.route('/')
@login_required
def appointment_list():
    """Provide HTML page listing all appointments in the database."""
    # Query: Get all Appointment objects, sorted by the appointment date.
    appts = Appointment.query.filter_by(user_id=current_user.id) \
                             .order_by(Appointment.start.asc()).all()
    return render_template('appointment/index.html', appts=appts)


@app.route('/<int:appointment_id>/')
@login_required
def appointment_detail(appointment_id):
    """Provide HTML page with all details on a given appointment."""
    # Query: get Appointment object by ID.
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.user_id != current_user.id:
        # Abort with Not Found.
        abort(404)
    return render_template('appointment/detail.html', appt=appt)


@app.route('/create/', methods=['GET', 'POST'])
@login_required
def appointment_create():
    """Provide HTML form to create a new appointment record."""
    form = AppointmentForm()
    if form.validate_on_submit():
        appt = Appointment(
            title=form.title.data,
            start=form.start.data,
            end=form.end.data,
            allday=form.allday.data,
            location=form.location.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(appt)
        db.session.commit()
        flash('You have created a new appointment.', 'success')
        return redirect(url_for('appointment_detail', appointment_id=appt.id))
    return render_template('appointment/edit.html', form=form)


@app.route('/<int:appointment_id>/edit/', methods=['GET', 'POST'])
@login_required
def appointment_edit(appointment_id):
    """Provide HTML form to edit a given appointment."""
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.user_id != current_user.id:
        abort(404)
    form = AppointmentForm(obj=appt)
    if form.validate_on_submit():
        form.populate_obj(appt)
        db.session.commit()
        return redirect(url_for('appointment_detail', appointment_id=appt.id))
    return render_template('appointment/edit.html', form=form)


@app.route('/<int:appointment_id>/delete/', methods=['DELETE'])
@login_required
def appointment_delete(appointment_id):
    """Delete a record using HTTP DELETE, respond with JSON for JavaScript."""
    appt = Appointment.query.get_or_404(appointment_id)
    if appt is None:
        # Abort with simple response indicating appointment not found.
        response = jsonify({'status': 'Not Found'})
        response.status_code = 404
        return response
    if appt.user_id != current_user.id:
        # Abort with simple response indicating forbidden.
        response = jsonify({'status': 'Forbidden'})
        response.status_code = 403
        return response
    db.session.delete(appt)
    db.session.commit()
    return jsonify({'status': 'OK'})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('appointment_list'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('You have been logged in', 'success')
            return redirect(next_page) if next_page else redirect(
                url_for('appointment_list'))
        flash('Invalid email or password.', 'warning')
    return render_template('appointment/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('appointment_list'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('appointment_list'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created. You can login', 'success')
        return redirect(url_for('login'))
    return render_template('appointment/register.html', form=form)


@app.errorhandler(404)
def error_not_found(error):
    return render_template('404.html'), 404
