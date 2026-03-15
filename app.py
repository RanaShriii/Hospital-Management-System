from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Doctor, Patient, Department, Appointment, Treatment, DoctorAvailability
from config import Config
from datetime import datetime, timedelta, date, time
from sqlalchemy import or_, and_, func
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

# Initialization 
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# RBAC route
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Database initialization
def init_db():
    with app.app_context():
        db.create_all()
        
        # creating admin if not created yet
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@hospital.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # departments
            departments = [
                Department(name='Cardiology', description='Heart and cardiovascular system'),
                Department(name='Neurology', description='Brain and nervous system'),
                Department(name='Orthopedics', description='Bones and joints'),
                Department(name='Pediatrics', description='Children healthcare'),
                Department(name='General Medicine', description='General health conditions')
            ]
            for dept in departments:
                db.session.add(dept)
            
            db.session.commit()
            print("Database initialized with admin user and departments!")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password, or account is inactive.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        blood_group = request.form.get('blood_group')
        address = request.form.get('address')
        emergency_contact = request.form.get('emergency_contact')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        # Create user and patient
        user = User(username=username, email=email, role='patient')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        patient = Patient(
            user_id=user.id,
            full_name=full_name,
            date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date() if dob else None,
            gender=gender,
            phone=phone,
            address=address,
            blood_group=blood_group,
            emergency_contact=emergency_contact
        )
        db.session.add(patient)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif current_user.role == 'patient':
        return redirect(url_for('patient_dashboard'))
    else:
        flash('Invalid user role!', 'danger')
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= date.today(),
        Appointment.status == 'Booked'
    ).count()
    
    recent_appointments = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         upcoming_appointments=upcoming_appointments,
                         recent_appointments=recent_appointments)

@app.route('/admin/doctors', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_doctors():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            department_id = request.form.get('department_id')
            specialization = request.form.get('specialization')
            phone = request.form.get('phone')
            qualification = request.form.get('qualification')
            experience = request.form.get('experience_years')
            fee = request.form.get('consultation_fee')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists!', 'danger')
                return redirect(url_for('manage_doctors'))
            
            user = User(username=username, email=email, role='doctor')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            
            doctor = Doctor(
                user_id=user.id,
                full_name=full_name,
                department_id=department_id,
                specialization=specialization,
                phone=phone,
                qualification=qualification,
                experience_years=experience,
                consultation_fee=fee
            )
            db.session.add(doctor)
            db.session.commit()
            flash('Doctor added successfully!', 'success')
        
        elif action == 'edit':
            doctor_id = request.form.get('doctor_id')
            doctor = db.session.get(Doctor, doctor_id)
            if doctor:
                doctor.full_name = request.form.get('full_name')
                doctor.department_id = request.form.get('department_id')
                doctor.specialization = request.form.get('specialization')
                doctor.phone = request.form.get('phone')
                doctor.qualification = request.form.get('qualification')
                doctor.experience_years = request.form.get('experience_years')
                doctor.consultation_fee = request.form.get('consultation_fee')
                db.session.commit()
                flash('Doctor details updated successfully!', 'success')
        
        elif action == 'blacklist':
            doctor_id = request.form.get('doctor_id')
            doctor = db.session.get(Doctor, doctor_id)
            if doctor:
                user = db.session.get(User, doctor.user_id)
                user.is_active = False  # Blacklist instead of delete
                db.session.commit()
                flash('Doctor blacklisted successfully!', 'success')
        
        return redirect(url_for('manage_doctors'))
    
    search_query = request.args.get('search', '')
    if search_query:
        doctors = Doctor.query.join(User).filter(
            User.is_active == True,
            or_(
                Doctor.full_name.ilike(f'%{search_query}%'),
                Doctor.specialization.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        doctors = Doctor.query.join(User).filter(User.is_active == True).all()
    
    departments = Department.query.all()
    return render_template('admin/manage_doctors.html', doctors=doctors, departments=departments)
@app.route('/admin/patients', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_patients():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'edit':
            patient_id = request.form.get('patient_id')
            patient = db.session.get(Patient, patient_id)
            if patient:
                patient.full_name = request.form.get('full_name')
                patient.phone = request.form.get('phone')
                patient.blood_group = request.form.get('blood_group')
                patient.emergency_contact = request.form.get('emergency_contact')
                patient.address = request.form.get('address')
                db.session.commit()
                flash('Patient details updated successfully!', 'success')
        
        elif action == 'blacklist':
            patient_id = request.form.get('patient_id')
            patient = db.session.get(Patient, patient_id)
            if patient:
                user = db.session.get(User, patient.user_id)
                user.is_active = False  # Blacklist
                db.session.commit()
                flash('Patient blacklisted successfully!', 'success')
        
        return redirect(url_for('manage_patients'))
    
    search_query = request.args.get('search', '')
    if search_query:
        patients = Patient.query.join(User).filter(
            User.is_active == True,
            or_(
                Patient.full_name.ilike(f'%{search_query}%'),
                Patient.phone.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        patients = Patient.query.join(User).filter(User.is_active == True).all()
    
    return render_template('admin/manage_patients.html', patients=patients)

@app.route('/admin/appointments')
@login_required
@role_required('admin')
def view_all_appointments():
    appointments = Appointment.query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('admin/view_appointments.html', appointments=appointments)

@app.route('/doctor/dashboard')
@login_required
@role_required('doctor')
def doctor_dashboard():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    today = date.today()
    next_week = today + timedelta(days=7)
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= today,
        Appointment.appointment_date <= next_week,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    patients_count = db.session.query(func.count(func.distinct(Appointment.patient_id))).filter(
        Appointment.doctor_id == doctor.id
    ).scalar()
    
    return render_template('doctor/dashboard.html',
                         doctor=doctor,
                         upcoming_appointments=upcoming_appointments,
                         patients_count=patients_count)

@app.route('/doctor/appointments', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def doctor_appointments():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id')
        action = request.form.get('action')
        
        appointment = db.session.get(Appointment, appointment_id)
        if appointment and appointment.doctor_id == doctor.id:
            if action == 'complete':
                diagnosis = request.form.get('diagnosis')
                prescription = request.form.get('prescription')
                notes = request.form.get('notes')
                appointment.status = 'Completed'
                treatment = Treatment(
                    appointment_id=appointment.id,
                    diagnosis=diagnosis,
                    prescription=prescription,
                    notes=notes
                )
                db.session.add(treatment)
                db.session.commit()
                flash('Appointment completed and treatment recorded!', 'success')
            elif action == 'edit_treatment':
                treatment = appointment.treatment
                if treatment:
                    treatment.diagnosis = request.form.get('diagnosis')
                    treatment.prescription = request.form.get('prescription')
                    treatment.notes = request.form.get('notes')
                    db.session.commit()
                    flash('Treatment updated successfully!', 'success')
                else:
                    flash('No treatment record found for this appointment!', 'danger')
            elif action == 'cancel':
                appointment.status = 'Cancelled'
                db.session.commit()
                flash('Appointment cancelled!', 'success')
        return redirect(url_for('doctor_appointments'))
    
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('doctor/appointments.html', appointments=appointments, doctor=doctor)

@app.route('/doctor/patient-history/<int:patient_id>')
@login_required
@role_required('doctor')
def patient_history(patient_id): 
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    
    appointments = Appointment.query.filter_by(
        patient_id=patient_id,
        doctor_id=doctor.id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('doctor/patient_history.html', patient=patient, appointments=appointments)

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def doctor_availability():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        availability_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Check if already exists
        existing = DoctorAvailability.query.filter_by(
            doctor_id=doctor.id,
            date=availability_date,
            start_time=start_time_obj
        ).first()
        
        if not existing:
            availability = DoctorAvailability(
                doctor_id=doctor.id,
                date=availability_date,
                start_time=start_time_obj,
                end_time=end_time_obj
            )
            db.session.add(availability)
            db.session.commit()
            flash('Availability added successfully!', 'success')
        else:
            flash('Availability already exists for this time slot!', 'warning')
        
        return redirect(url_for('doctor_availability'))
    
    today = date.today()
    next_week = today + timedelta(days=7)
    
    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week
    ).order_by(DoctorAvailability.date, DoctorAvailability.start_time).all()
    
    return render_template('doctor/availability.html', availabilities=availabilities, doctor=doctor)

# ===== PATIENT ROUTES =====

@app.route('/patient/dashboard')
@login_required
@role_required('patient')
def patient_dashboard():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    departments = Department.query.all()
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= date.today(),
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    return render_template('patient/dashboard.html',
                         patient=patient,
                         departments=departments,
                         upcoming_appointments=upcoming_appointments)

@app.route('/patient/department/<int:dept_id>')
@login_required
@role_required('patient')
def department_doctors(dept_id):
    today = date.today()
    next_week = today + timedelta(days=7)
    department = db.session.get(Department, dept_id)
    
    if not department:
        flash('Department not found!', 'danger')
        return redirect(url_for('patient_dashboard'))
    
    # GETTING active doctors in department
    doctors = Doctor.query.join(User).filter(
        Doctor.department_id == dept_id,
        User.is_active == True
    ).all()
    
    # For each doctor, get their availabilities for the next 7 days
    availabilities = {}
    for doc in doctors:
        avs = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doc.id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= next_week,
            DoctorAvailability.is_available == True
        ).order_by(DoctorAvailability.date, DoctorAvailability.start_time).all()
        availabilities[doc.id] = avs
    
    return render_template('patient/department_doctors.html',
                         department=department,
                         doctors=doctors,
                         availabilities=availabilities,
                         today=today,
                         next_week=next_week)

@app.route('/patient/book-appointment', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def book_appointment():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        appointment_date_str = request.form.get('appointment_date')
        appointment_time_str = request.form.get('appointment_time')
        reason = request.form.get('reason')
        
        appointment_date_obj = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
        appointment_time_obj = datetime.strptime(appointment_time_str, '%H:%M').time()
        
        # Check if doctor has availability on this date and time
        availability = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.date == appointment_date_obj,
            DoctorAvailability.start_time <= appointment_time_obj,
            DoctorAvailability.end_time > appointment_time_obj,
            DoctorAvailability.is_available == True
        ).first()
        
        if not availability:
            flash('Doctor is not available at the selected date and time! Please check doctor availability.', 'danger')
            return redirect(url_for('book_appointment'))
        
        # Check for conflicts - only Booked and Completed appointments block the slot
        existing = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date_obj,
            Appointment.appointment_time == appointment_time_obj,
            Appointment.status.in_(['Booked', 'Completed'])
        ).first()
        
        if existing:
            flash('This time slot is already booked! Please choose another time.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id, date=appointment_date_str))
        
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            appointment_date=appointment_date_obj,
            appointment_time=appointment_time_obj,
            reason=reason,
            status='Booked'
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('my_appointments'))
    
    # Get pre-selected doctor from query params
    preselected_doctor_id = request.args.get('doctor_id', type=int)
    preselected_date = request.args.get('date')
    
    # Get doctors with availability
    today = date.today()
    next_week = today + timedelta(days=7)
    
    doctors = Doctor.query.join(User).filter(User.is_active == True).all()
    departments = Department.query.all()
    
    # Get availability data for all doctors
    availability_data = {}
    for doctor in doctors:
        slots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor.id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= next_week,
            DoctorAvailability.is_available == True
        ).all()
        availability_data[doctor.id] = {
            'dates': [slot.date.strftime('%Y-%m-%d') for slot in slots],
            'slots': {slot.date.strftime('%Y-%m-%d'): {
                'start': slot.start_time.strftime('%H:%M'),
                'end': slot.end_time.strftime('%H:%M')
            } for slot in slots}
        }
    
    # Get booked appointments to exclude them (excluding cancelled)
    booked_appointments = Appointment.query.filter(
        Appointment.appointment_date >= today,
        Appointment.appointment_date <= next_week,
        Appointment.status.in_(['Booked', 'Completed'])
    ).all()
    
    booked_slots = {}
    for appt in booked_appointments:
        key = f"{appt.doctor_id}_{appt.appointment_date.strftime('%Y-%m-%d')}"
        if key not in booked_slots:
            booked_slots[key] = []
        booked_slots[key].append(appt.appointment_time.strftime('%H:%M'))
    
    return render_template('patient/book_appointment.html',
                         doctors=doctors,
                         departments=departments,
                         patient=patient,
                         availability_data=availability_data,
                         booked_slots=booked_slots,
                         preselected_doctor_id=preselected_doctor_id,
                         preselected_date=preselected_date)

@app.route('/patient/my-appointments', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def my_appointments():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id')
        action = request.form.get('action')
        
        appointment = Appointment.query.get(appointment_id)
        if appointment and appointment.patient_id == patient.id:
            if action == 'cancel':
                appointment.status = 'Cancelled'
                db.session.commit()
                flash('Appointment cancelled successfully!', 'success')
        
        return redirect(url_for('my_appointments'))
    
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('patient/my_appointments.html', appointments=appointments, patient=patient)

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def patient_profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        patient.full_name = request.form.get('full_name')
        patient.phone = request.form.get('phone')
        patient.address = request.form.get('address')
        patient.blood_group = request.form.get('blood_group')
        patient.emergency_contact = request.form.get('emergency_contact')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient_profile'))
    
    return render_template('patient/profile.html', patient=patient)

# API Routes (Optional)

@app.route('/api/doctors/<int:department_id>')
@login_required
def api_doctors_by_department(department_id):
    doctors = Doctor.query.filter_by(department_id=department_id).all()
    return {
        'doctors': [{
            'id': d.id,
            'name': d.full_name,
            'specialization': d.specialization,
            'fee': d.consultation_fee
        } for d in doctors]
    }



@app.route('/api/availability/<int:doctor_id>/<string:date_str>')
@login_required
def api_doctor_availability(doctor_id, date_str):
    availability_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    availabilities = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        date=availability_date,
        is_available=True
    ).all()
    
    return {
        'slots': [{
            'start_time': av.start_time.strftime('%H:%M'),
            'end_time': av.end_time.strftime('%H:%M')
        } for av in availabilities]
    }

if __name__ == '__main__':
    init_db()
    app.run(debug=True)