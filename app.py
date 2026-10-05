import base64
import io
import os
import secrets
from datetime import date, datetime, time, timedelta
from functools import wraps
from pathlib import Path

import click
import qrcode
from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   send_from_directory, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Ensure upload directory structure exists (essential for production / gunicorn deployments)
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
for _folder in ["reports", "prescriptions", "profiles"]:
    (Path(app.config["UPLOAD_FOLDER"]) / _folder).mkdir(parents=True, exist_ok=True)


class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(30))
    blood_group = db.Column(db.String(10))
    allergies = db.Column(db.Text)
    phone = db.Column(db.String(30))
    photo_path = db.Column(db.String(255))
    emergency_contact_name = db.Column(db.String(120))
    emergency_contact_number = db.Column(db.String(30))
    notifications_enabled = db.Column(db.Boolean, default=True)
    voice_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Medicine(db.Model):
    __tablename__ = "medicines"
    medicine_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    medicine_name = db.Column(db.String(120), nullable=False)
    medicine_type = db.Column(db.String(30), nullable=False)
    dosage = db.Column(db.String(80), nullable=False)
    frequency = db.Column(db.String(80), nullable=False)
    time = db.Column(db.Time, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    meal_instruction = db.Column(db.String(80))
    quantity = db.Column(db.Integer, default=0)
    refill_threshold = db.Column(db.Integer, default=3)
    notes = db.Column(db.Text)


class MedicineHistory(db.Model):
    __tablename__ = "medicine_history"
    history_id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.medicine_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="pending")
    taken_at = db.Column(db.DateTime)
    medicine = db.relationship("Medicine")


class Appointment(db.Model):
    __tablename__ = "appointments"
    appointment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    doctor_name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(120))
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    clinic_name = db.Column(db.String(160))
    purpose = db.Column(db.Text)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="upcoming")


class Report(db.Model):
    __tablename__ = "reports"
    report_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    report_name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    report_date = db.Column(db.Date)
    doctor_hospital = db.Column(db.String(160))
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    prescription_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    doctor_name = db.Column(db.String(120), nullable=False)
    prescription_date = db.Column(db.Date)
    clinic_name = db.Column(db.String(160))
    file_path = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class MedicineInteraction(db.Model):
    __tablename__ = "medicine_interactions"
    interaction_id = db.Column(db.Integer, primary_key=True)
    medicine_one = db.Column(db.String(120), nullable=False)
    medicine_two = db.Column(db.String(120), nullable=False)
    warning = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(30), default="moderate")


class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(40), default="info")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to access MediCare+.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def owned_or_404(model, item_id, field):
    item = model.query.filter_by(**{field: item_id, "user_id": session["user_id"]}).first()
    if not item:
        abort(404)
    return item


def add_notification(user_id, title, message, type_="info"):
    db.session.add(Notification(user_id=user_id, title=title, message=message, type=type_))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def parse_time(value):
    return datetime.strptime(value, "%H:%M").time() if value else None


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(24)
    return session["csrf_token"]


@app.context_processor
def common_context():
    user = current_user()
    notifications = []
    unread_count = 0
    if user:
        notifications = Notification.query.filter_by(user_id=user.user_id).order_by(Notification.created_at.desc()).limit(6).all()
        unread_count = Notification.query.filter_by(user_id=user.user_id, is_read=False).count()
    return {"current_user": user, "csrf_token": csrf_token, "nav_notifications": notifications,
            "unread_count": unread_count, "today": date.today()}


@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
            abort(400, "Invalid or missing form security token. Please refresh and try again.")


@app.errorhandler(413)
def file_too_large(_error):
    flash("Upload must be smaller than 10 MB.", "danger")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        required = ["name", "email", "password", "confirm_password", "age", "gender", "blood_group", "emergency_contact_name", "emergency_contact_number"]
        if any(not request.form.get(key, "").strip() for key in required):
            flash("Please complete all required registration fields.", "danger")
        elif request.form["password"] != request.form["confirm_password"]:
            flash("Passwords do not match.", "danger")
        elif len(request.form["password"]) < 8:
            flash("Use a password with at least 8 characters.", "danger")
        elif User.query.filter(func.lower(User.email) == request.form["email"].strip().lower()).first():
            flash("An account with that email already exists.", "danger")
        else:
            user = User(name=request.form["name"].strip(), email=request.form["email"].strip().lower(),
                        password=generate_password_hash(request.form["password"]), age=int(request.form["age"]),
                        gender=request.form["gender"], blood_group=request.form["blood_group"],
                        emergency_contact_name=request.form["emergency_contact_name"].strip(),
                        emergency_contact_number=request.form["emergency_contact_number"].strip())
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.user_id
            flash("Welcome to MediCare+. Your account is ready.", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = User.query.filter(func.lower(User.email) == request.form.get("email", "").strip().lower()).first()
        if user and check_password_hash(user.password, request.form.get("password", "")):
            session.clear()
            session["user_id"] = user.user_id
            csrf_token()
            session.permanent = bool(request.form.get("remember"))
            flash(f"Welcome back, {user.name.split()[0]}!", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for("index"))


def today_schedule(user_id):
    meds = Medicine.query.filter_by(user_id=user_id).filter(
        or_(Medicine.start_date.is_(None), Medicine.start_date <= date.today()),
        or_(Medicine.end_date.is_(None), Medicine.end_date >= date.today())
    ).order_by(Medicine.time).all()
    result = []
    for med in meds:
        scheduled = datetime.combine(date.today(), med.time)
        history = MedicineHistory.query.filter_by(medicine_id=med.medicine_id, user_id=user_id, scheduled_time=scheduled).first()
        result.append({"medicine": med, "scheduled": scheduled, "history": history, "status": history.status if history else "pending"})
    return result


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    schedule = today_schedule(user.user_id)
    taken = MedicineHistory.query.filter_by(user_id=user.user_id, status="taken").count()
    records = MedicineHistory.query.filter_by(user_id=user.user_id).count()
    adherence = round((taken / records) * 100) if records else 0
    upcoming = Appointment.query.filter_by(user_id=user.user_id, status="upcoming").filter(Appointment.appointment_date >= date.today()).count()
    reports_count = Report.query.filter_by(user_id=user.user_id).count()
    activity = []
    for offset in range(5, -1, -1):
        day = date.today() - timedelta(days=offset)
        activity.append(MedicineHistory.query.filter_by(user_id=user.user_id).filter(func.date(MedicineHistory.scheduled_time) == day).count())
    appointment_history = [Appointment.query.filter_by(user_id=user.user_id).filter(func.extract("month", Appointment.appointment_date) == month).count() for month in range(1, 7)]
    return render_template("dashboard.html", schedule=schedule, stats={"medicines": Medicine.query.filter_by(user_id=user.user_id).count(), "doses": len(schedule), "appointments": upcoming, "reports": reports_count, "adherence": adherence}, activity=activity, appointment_history=appointment_history)


@app.route("/medicine-status/<int:medicine_id>", methods=["POST"])
@login_required
def medicine_status(medicine_id):
    med = owned_or_404(Medicine, medicine_id, "medicine_id")
    status = request.form.get("status", "taken")
    if status not in {"taken", "skipped", "missed"}:
        abort(400)
    scheduled = datetime.combine(date.today(), med.time)
    history = MedicineHistory.query.filter_by(medicine_id=med.medicine_id, user_id=med.user_id, scheduled_time=scheduled).first()
    if not history:
        history = MedicineHistory(medicine_id=med.medicine_id, user_id=med.user_id, scheduled_time=scheduled)
        db.session.add(history)
    history.status = status
    history.taken_at = datetime.utcnow() if status == "taken" else None
    if status == "taken" and med.quantity and med.quantity > 0:
        med.quantity -= 1
        if med.quantity <= med.refill_threshold:
            add_notification(med.user_id, "Low medicine stock", f"{med.medicine_name} is running low ({med.quantity} left).", "stock")
    db.session.commit()
    flash(f"{med.medicine_name} marked as {status}.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/medicines", methods=["GET", "POST"])
@login_required
def medicines():
    user = current_user()
    if request.method == "POST":
        try:
            required = ["medicine_name", "medicine_type", "dosage", "frequency", "time"]
            if any(not request.form.get(key, "").strip() for key in required):
                raise ValueError("Complete all required medicine fields.")
            med = Medicine(user_id=user.user_id, medicine_name=request.form["medicine_name"].strip(), medicine_type=request.form["medicine_type"], dosage=request.form["dosage"].strip(), frequency=request.form["frequency"].strip(), time=parse_time(request.form["time"]), start_date=parse_date(request.form.get("start_date")), end_date=parse_date(request.form.get("end_date")), meal_instruction=request.form.get("meal_instruction"), quantity=int(request.form.get("quantity") or 0), refill_threshold=int(request.form.get("refill_threshold") or 3), notes=request.form.get("notes", "").strip())
            db.session.add(med)
            add_notification(user.user_id, "Medicine added", f"{med.medicine_name} has been added to your medicine plan.", "medicine")
            db.session.commit()
            flash("Medicine added successfully.", "success")
        except (ValueError, TypeError):
            db.session.rollback()
            flash("Please check the medicine form and try again.", "danger")
        return redirect(url_for("medicines"))
    search = request.args.get("q", "").strip()
    kind = request.args.get("type", "")
    query = Medicine.query.filter_by(user_id=user.user_id)
    if search:
        query = query.filter(Medicine.medicine_name.ilike(f"%{search}%"))
    if kind:
        query = query.filter_by(medicine_type=kind)
    return render_template("medicines.html", medicines=query.order_by(Medicine.time).all(), search=search, selected_type=kind)


@app.route("/medicines/<int:medicine_id>/edit", methods=["POST"])
@login_required
def edit_medicine(medicine_id):
    med = owned_or_404(Medicine, medicine_id, "medicine_id")
    try:
        for field in ["medicine_name", "medicine_type", "dosage", "frequency", "meal_instruction", "notes"]:
            if field in request.form:
                setattr(med, field, request.form[field].strip())
        med.time = parse_time(request.form["time"])
        med.start_date, med.end_date = parse_date(request.form.get("start_date")), parse_date(request.form.get("end_date"))
        med.quantity, med.refill_threshold = int(request.form.get("quantity", 0)), int(request.form.get("refill_threshold", 3))
        db.session.commit()
        flash("Medicine updated successfully.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Could not update medicine. Check the values and try again.", "danger")
    return redirect(url_for("medicines"))


@app.route("/medicines/<int:medicine_id>/delete", methods=["POST"])
@login_required
def delete_medicine(medicine_id):
    med = owned_or_404(Medicine, medicine_id, "medicine_id")
    MedicineHistory.query.filter_by(medicine_id=med.medicine_id, user_id=med.user_id).delete()
    db.session.delete(med)
    db.session.commit()
    flash("Medicine deleted.", "info")
    return redirect(url_for("medicines"))


@app.route("/reminders")
@login_required
def reminders():
    return render_template("reminders.html", schedule=today_schedule(current_user().user_id))


@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments():
    user = current_user()
    if request.method == "POST":
        try:
            required = ["doctor_name", "appointment_date", "appointment_time"]
            if any(not request.form.get(k, "").strip() for k in required):
                raise ValueError
            appt = Appointment(user_id=user.user_id, doctor_name=request.form["doctor_name"].strip(), specialization=request.form.get("specialization", "").strip(), appointment_date=parse_date(request.form["appointment_date"]), appointment_time=parse_time(request.form["appointment_time"]), clinic_name=request.form.get("clinic_name", "").strip(), purpose=request.form.get("purpose", "").strip(), notes=request.form.get("notes", "").strip())
            db.session.add(appt)
            add_notification(user.user_id, "Appointment scheduled", f"Your appointment with {appt.doctor_name} is scheduled for {appt.appointment_date:%d %b %Y}.", "appointment")
            db.session.commit()
            flash("Appointment scheduled successfully.", "success")
        except (ValueError, TypeError):
            db.session.rollback()
            flash("Please complete doctor, date, and time.", "danger")
        return redirect(url_for("appointments"))
    items = Appointment.query.filter_by(user_id=user.user_id).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    return render_template("appointments.html", appointments=items)


@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@login_required
def appointment_status(appointment_id):
    appt = owned_or_404(Appointment, appointment_id, "appointment_id")
    status = request.form.get("status")
    if status not in {"upcoming", "completed", "cancelled"}:
        abort(400)
    appt.status = status
    db.session.commit()
    flash(f"Appointment marked {status}.", "success")
    return redirect(url_for("appointments"))


@app.route("/appointments/<int:appointment_id>/edit", methods=["POST"])
@login_required
def edit_appointment(appointment_id):
    appt = owned_or_404(Appointment, appointment_id, "appointment_id")
    try:
        required = ["doctor_name", "appointment_date", "appointment_time"]
        if any(not request.form.get(k, "").strip() for k in required):
            raise ValueError
        appt.doctor_name = request.form["doctor_name"].strip()
        appt.specialization = request.form.get("specialization", "").strip()
        appt.appointment_date = parse_date(request.form["appointment_date"])
        appt.appointment_time = parse_time(request.form["appointment_time"])
        appt.clinic_name = request.form.get("clinic_name", "").strip()
        appt.purpose = request.form.get("purpose", "").strip()
        appt.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Appointment updated successfully.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Please check the appointment values and try again.", "danger")
    return redirect(url_for("appointments"))


@app.route("/appointments/<int:appointment_id>/delete", methods=["POST"])
@login_required
def delete_appointment(appointment_id):
    db.session.delete(owned_or_404(Appointment, appointment_id, "appointment_id"))
    db.session.commit()
    flash("Appointment deleted.", "info")
    return redirect(url_for("appointments"))


def save_upload(file, category):
    if not file or not file.filename:
        raise ValueError("Choose a file to upload.")
    if not allowed_file(file.filename):
        raise ValueError("Only PDF, JPG, JPEG, and PNG files are allowed.")
    folder = Path(app.config["UPLOAD_FOLDER"]) / category
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(8)}_{secure_filename(file.filename)}"
    file.save(folder / filename)
    return filename


@app.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    user = current_user()
    if request.method == "POST":
        try:
            if not request.form.get("report_name", "").strip():
                raise ValueError("Report name is required.")
            filename = save_upload(request.files.get("file"), "reports")
            report = Report(user_id=user.user_id, report_name=request.form.get("report_name", "").strip(), category=request.form.get("category", "Other"), file_path=filename, report_date=parse_date(request.form.get("report_date")), doctor_hospital=request.form.get("doctor_hospital", "").strip(), description=request.form.get("description", "").strip())
            db.session.add(report)
            add_notification(user.user_id, "Report uploaded", f"{report.report_name} has been added to your medical records.", "report")
            db.session.commit()
            flash("Report uploaded successfully.", "success")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        return redirect(url_for("reports"))
    return render_template("reports.html", reports=Report.query.filter_by(user_id=user.user_id).order_by(Report.upload_date.desc()).all())


@app.route("/reports/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_report(report_id):
    report = owned_or_404(Report, report_id, "report_id")
    path = Path(app.config["UPLOAD_FOLDER"]) / "reports" / report.file_path
    if path.exists(): path.unlink()
    db.session.delete(report)
    db.session.commit()
    flash("Report deleted.", "info")
    return redirect(url_for("reports"))


@app.route("/prescriptions", methods=["GET", "POST"])
@login_required
def prescriptions():
    user = current_user()
    if request.method == "POST":
        try:
            if not request.form.get("doctor_name", "").strip():
                raise ValueError("Doctor name is required.")
            filename = save_upload(request.files.get("file"), "prescriptions")
            item = Prescription(user_id=user.user_id, doctor_name=request.form["doctor_name"].strip(), prescription_date=parse_date(request.form.get("prescription_date")), clinic_name=request.form.get("clinic_name", "").strip(), file_path=filename, notes=request.form.get("notes", "").strip())
            db.session.add(item)
            db.session.commit()
            flash("Prescription uploaded successfully.", "success")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        return redirect(url_for("prescriptions"))
    search = request.args.get("q", "").strip()
    query = Prescription.query.filter_by(user_id=user.user_id)
    if search: query = query.filter(or_(Prescription.doctor_name.ilike(f"%{search}%"), Prescription.clinic_name.ilike(f"%{search}%")))
    return render_template("prescriptions.html", prescriptions=query.order_by(Prescription.upload_date.desc()).all(), search=search)


@app.route("/prescriptions/<int:prescription_id>/delete", methods=["POST"])
@login_required
def delete_prescription(prescription_id):
    item = owned_or_404(Prescription, prescription_id, "prescription_id")
    path = Path(app.config["UPLOAD_FOLDER"]) / "prescriptions" / item.file_path
    if path.exists(): path.unlink()
    db.session.delete(item)
    db.session.commit()
    flash("Prescription deleted.", "info")
    return redirect(url_for("prescriptions"))


@app.route("/uploads/<category>/<filename>")
@login_required
def uploaded_file(category, filename):
    if category not in {"reports", "prescriptions"}:
        abort(404)
    model = Report if category == "reports" else Prescription
    item = model.query.filter_by(user_id=session["user_id"], file_path=filename).first()
    if not item: abort(404)
    return send_from_directory(Path(app.config["UPLOAD_FOLDER"]) / category, filename, as_attachment=request.args.get("download") == "1")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def health_profile():
    user = current_user()
    if request.method == "POST":
        try:
            for field in ["name", "gender", "blood_group", "allergies", "phone", "emergency_contact_name", "emergency_contact_number"]:
                setattr(user, field, request.form.get(field, "").strip())
            user.age = int(request.form.get("age") or 0) or None
            email = request.form.get("email", "").strip().lower()
            conflict = User.query.filter(User.email == email, User.user_id != user.user_id).first()
            if not email or conflict: raise ValueError
            user.email = email
            photo = request.files.get("photo")
            if photo and photo.filename:
                if photo.filename.rsplit(".", 1)[-1].lower() not in {"jpg", "jpeg", "png"}: raise ValueError
                user.photo_path = save_upload(photo, "profiles")
            db.session.commit()
            flash("Health profile saved successfully.", "success")
        except (ValueError, TypeError):
            db.session.rollback()
            flash("Please check your profile details and image type.", "danger")
        return redirect(url_for("health_profile"))
    return render_template("health_profile.html")


@app.route("/profile-image/<filename>")
@login_required
def profile_image(filename):
    if current_user().photo_path != filename: abort(404)
    return send_from_directory(Path(app.config["UPLOAD_FOLDER"]) / "profiles", filename)


def qr_data_uri(user):
    content = f"MediCare+ Emergency Health Card\nName: {user.name}\nBlood Group: {user.blood_group or 'Not provided'}\nAllergies: {user.allergies or 'None recorded'}\nEmergency Contact: {user.emergency_contact_name or 'Not provided'}\nPhone: {user.emergency_contact_number or 'Not provided'}"
    image = qrcode.make(content)
    buff = io.BytesIO(); image.save(buff, format="PNG")
    return base64.b64encode(buff.getvalue()).decode("ascii")


@app.route("/qr-card")
@login_required
def qr_card():
    return render_template("qr_card.html", qr_image=qr_data_uri(current_user()))


@app.route("/qr-card/download")
@login_required
def qr_download():
    from flask import send_file
    user = current_user()
    content = f"MediCare+ Emergency Health Card\nName: {user.name}\nBlood Group: {user.blood_group or 'Not provided'}\nAllergies: {user.allergies or 'None recorded'}\nEmergency Contact: {user.emergency_contact_name or 'Not provided'}\nPhone: {user.emergency_contact_number or 'Not provided'}"
    buf = io.BytesIO(); qrcode.make(content).save(buf, "PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name="medicare-health-card-qr.png")


@app.route("/interactions", methods=["GET", "POST"])
@login_required
def interactions():
    result = None
    if request.method == "POST":
        one, two = request.form.get("medicine_one", "").strip(), request.form.get("medicine_two", "").strip()
        if not one or not two:
            flash("Enter both medicine names to check an interaction.", "danger")
        else:
            match = MedicineInteraction.query.filter(
                or_((func.lower(MedicineInteraction.medicine_one) == one.lower()) & (func.lower(MedicineInteraction.medicine_two) == two.lower()),
                    (func.lower(MedicineInteraction.medicine_one) == two.lower()) & (func.lower(MedicineInteraction.medicine_two) == one.lower()))
            ).first()
            result = {"one": one, "two": two, "match": match}
    return render_template("interaction_checker.html", result=result)


@app.route("/stock", methods=["GET", "POST"])
@login_required
def stock():
    user = current_user()
    if request.method == "POST":
        med = owned_or_404(Medicine, int(request.form.get("medicine_id", 0)), "medicine_id")
        try:
            if request.form.get("action") == "set":
                med.quantity = max(0, int(request.form.get("quantity", 0)))
                med.refill_threshold = max(0, int(request.form.get("refill_threshold", 3)))
            else:
                med.quantity = max(0, med.quantity + int(request.form.get("amount", 1)) * (1 if request.form.get("action") == "increase" else -1))
            if med.quantity <= med.refill_threshold:
                add_notification(user.user_id, "Low medicine stock", f"{med.medicine_name} has {med.quantity} item(s) remaining.", "stock")
            db.session.commit()
            flash("Stock updated.", "success")
        except (ValueError, TypeError):
            db.session.rollback(); flash("Invalid stock value.", "danger")
        return redirect(url_for("stock"))
    return render_template("stock.html", medicines=Medicine.query.filter_by(user_id=user.user_id).order_by(Medicine.quantity).all())


@app.route("/emergency", methods=["GET", "POST"])
@login_required
def emergency():
    user = current_user()
    message = None
    if request.method == "POST":
        message = f"EMERGENCY ALERT from MediCare+. {user.name} may need immediate assistance. Blood Group: {user.blood_group or 'not provided'}. Allergies: {user.allergies or 'none recorded'}. Please contact them immediately."
        add_notification(user.user_id, "Emergency alert sent", "Your emergency alert was simulated successfully.", "emergency")
        db.session.commit()
        flash("Emergency alert sent (demo simulation).", "success")
    return render_template("emergency.html", message=message)


@app.route("/history")
@login_required
def history():
    user = current_user()
    record_type = request.args.get("type", "all")
    try:
        filter_date = parse_date(request.args.get("date"))
    except ValueError:
        filter_date = None
        flash("Use a valid date to filter health history.", "warning")
    history_query = MedicineHistory.query.filter_by(user_id=user.user_id)
    appointment_query = Appointment.query.filter_by(user_id=user.user_id).filter(Appointment.status != "upcoming")
    report_query = Report.query.filter_by(user_id=user.user_id)
    if filter_date:
        history_query = history_query.filter(func.date(MedicineHistory.scheduled_time) == filter_date)
        appointment_query = appointment_query.filter(Appointment.appointment_date == filter_date)
        report_query = report_query.filter(func.date(Report.upload_date) == filter_date)
    return render_template("history.html", history=history_query.order_by(MedicineHistory.scheduled_time.desc()).all(), appointments=appointment_query.order_by(Appointment.appointment_date.desc()).all(), reports=report_query.order_by(Report.upload_date.desc()).all(), record_type=record_type, filter_date=filter_date)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = current_user()
    if request.method == "POST":
        user.notifications_enabled = bool(request.form.get("notifications_enabled"))
        user.voice_enabled = bool(request.form.get("voice_enabled"))
        db.session.commit()
        flash("Reminder preferences saved.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html")


@app.route("/notifications/read", methods=["POST"])
@login_required
def read_notifications():
    Notification.query.filter_by(user_id=session["user_id"], is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/api/reminders")
@login_required
def reminder_api():
    user = current_user()
    now = datetime.now()
    items = []
    for item in today_schedule(user.user_id):
        diff = abs((now - item["scheduled"]).total_seconds())
        if item["status"] == "pending" and diff <= 60:
            med = item["medicine"]
            items.append({"id": f"medicine-{med.medicine_id}", "type": "medicine", "title": "Time to take your medicine", "name": med.medicine_name, "dosage": med.dosage, "instruction": med.meal_instruction or ""})
    for appointment in Appointment.query.filter_by(user_id=user.user_id, status="upcoming").filter(Appointment.appointment_date == date.today()).all():
        scheduled = datetime.combine(appointment.appointment_date, appointment.appointment_time)
        if abs((now - scheduled).total_seconds()) <= 300:
            items.append({"id": f"appointment-{appointment.appointment_id}", "type": "appointment", "title": "Appointment reminder", "name": f"Appointment with {appointment.doctor_name}", "dosage": scheduled.strftime("%I:%M %p"), "instruction": appointment.clinic_name or ""})
    return jsonify({"enabled": user.notifications_enabled, "voice": user.voice_enabled, "reminders": items})


@app.cli.command("init-db")
def init_db_command():
    """Create all database tables using the configured database URL."""
    db.create_all()
    click.echo("Database tables created.")


@app.cli.command("seed-demo")
def seed_demo_command():
    """Add database-backed demo data; safe to run once."""
    db.create_all()
    user = User.query.filter_by(email="demo@medicare.local").first()
    if user:
        click.echo("Demo account already exists: demo@medicare.local / Demo@123")
        return
    user = User(name="Rahul Sharma", email="demo@medicare.local", password=generate_password_hash("Demo@123"), age=28, gender="Male", blood_group="B+", allergies="Penicillin", phone="+91 98765 43210", emergency_contact_name="Priya Sharma", emergency_contact_number="+91 98765 40000")
    db.session.add(user); db.session.flush()
    meds = [
        Medicine(user_id=user.user_id, medicine_name="Vitamin D", medicine_type="Tablet", dosage="1 tablet", frequency="Daily", time=time(8, 0), start_date=date.today()-timedelta(days=15), end_date=date.today()+timedelta(days=15), meal_instruction="After breakfast", quantity=18, refill_threshold=5),
        Medicine(user_id=user.user_id, medicine_name="Amlodipine", medicine_type="Tablet", dosage="5 mg", frequency="Daily", time=time(14, 0), start_date=date.today()-timedelta(days=20), meal_instruction="After lunch", quantity=5, refill_threshold=5),
        Medicine(user_id=user.user_id, medicine_name="Paracetamol", medicine_type="Tablet", dosage="500 mg", frequency="As needed", time=time(20, 0), start_date=date.today()-timedelta(days=5), meal_instruction="After dinner", quantity=2, refill_threshold=3),
    ]
    db.session.add_all(meds); db.session.flush()
    for days_back in range(1, 7):
        db.session.add(MedicineHistory(medicine_id=meds[0].medicine_id, user_id=user.user_id, scheduled_time=datetime.combine(date.today()-timedelta(days=days_back), time(8, 0)), status="taken", taken_at=datetime.utcnow()))
    db.session.add(Appointment(user_id=user.user_id, doctor_name="Dr. Amit Patel", specialization="General Physician", appointment_date=date.today()+timedelta(days=8), appointment_time=time(10, 30), clinic_name="City Care Clinic", purpose="Regular health checkup"))
    db.session.add_all([MedicineInteraction(medicine_one="Amlodipine", medicine_two="Simvastatin", warning="This combination may increase exposure to simvastatin. A clinician may adjust treatment.", severity="moderate"), MedicineInteraction(medicine_one="Paracetamol", medicine_two="Warfarin", warning="Regular use may increase bleeding risk. Discuss with a pharmacist or doctor.", severity="high")])
    add_notification(user.user_id, "Welcome to MediCare+", "Your demo health dashboard is ready to explore.", "info")
    db.session.commit()
    click.echo("Demo account created: demo@medicare.local / Demo@123")


if __name__ == "__main__":
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    app.run(debug=True)
