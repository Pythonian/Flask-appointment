from datetime import datetime, timedelta
from app import db, Appointment, User

now = datetime.now()

# Add a user
user = User(email='user@email.com', password='password')

# Add some sample appointments.

appt = Appointment(
    user_id=user.id,
    title='My Appointment',
    start=now,
    end=now + timedelta(seconds=1800),
    allday=False)

appt1 = Appointment(
    user_id=user.id,
    title='Important Meeting',
    start=now + timedelta(days=3),
    end=now + timedelta(days=3, seconds=3600),
    allday=False,
    location='The Office')


appt2 = Appointment(
    user_id=user.id,
    title='Past Meeting',
    start=now - timedelta(days=3, seconds=3600),
    end=now - timedelta(days=3),
    allday=False,
    location='The Office')

appt3 = Appointment(
    user_id=user.id,
    title='Follow Up',
    start=now + timedelta(days=4),
    end=now + timedelta(days=4, seconds=3600),
    allday=False,
    location='The Office')

appt4 = Appointment(
    user_id=user.id,
    title='Day Off',
    start=now + timedelta(days=5),
    end=now + timedelta(days=5),
    allday=True)

db.session.add_all([user, appt, appt1, appt2, appt3, appt4])
db.session.commit()

# Demonstration Queries

# Get all appointments before right now, after right now.
appts = Appointment.query.filter(
    Appointment.start < datetime.now()).all()
appts = Appointment.filter(
    Appointment.start >= datetime.now()).all()

# Get all appointments before a certain date.
appts = Appointment.filter(
    Appointment.start <= datetime(2013, 5, 1)).all()

# Get the first appointment matching the filter query.
appt = Appointment.filter(
    Appointment.start <= datetime(2013, 5, 1)).first()
