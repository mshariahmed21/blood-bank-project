import os
import re
import secrets
import time
import json
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

from flask import Flask, flash, redirect, render_template, render_template_string, request, session, url_for, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key-change-before-deployment")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8
OTP_DEMO_MODE = os.environ.get("OTP_DEMO_MODE", "0") == "1"
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "").strip()
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "").replace(" ", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))

# Locally uses SQLite. For Render, set DATABASE_URL to a managed PostgreSQL database URL
# so donor registrations survive deploys/restarts.
database_url = os.environ.get("DATABASE_URL", "sqlite:///qatrah_life.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

BLOOD_TYPES = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
CITIES = [
    "الرياض", "الدرعية", "الخرج", "المجمعة", "الدوادمي",
    "جدة", "مكة المكرمة", "الطائف", "القنفذة", "رابغ", "الليث",
    "المدينة المنورة", "ينبع", "العلا", "بدر",
    "الدمام", "الخبر", "الظهران", "الجبيل", "الأحساء", "حفر الباطن", "القطيف",
    "بريدة", "عنيزة", "الرس", "المذنب",
    "أبها", "خميس مشيط", "بيشة", "النماص", "محايل عسير",
    "جازان", "صبيا", "أبو عريش", "صامطة", "الدرب", "فرسان",
    "نجران", "شرورة", "حبونا", "تبوك", "الوجه", "ضباء", "أملج",
    "حائل", "بقعاء", "عرعر", "رفحاء", "طريف", "سكاكا", "القريات",
    "دومة الجندل", "الباحة", "بلجرشي", "المخواة", "وادي الدواسر",
    "الأفلاج", "القويعية", "شقراء", "عفيف"
]


class Donor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=True, unique=True, index=True)
    phone = db.Column(db.String(20), nullable=True, unique=True, index=True)
    age = db.Column(db.Integer, nullable=False)
    blood_type = db.Column(db.String(3), nullable=False, index=True)
    city = db.Column(db.String(80), nullable=False, index=True)
    consent = db.Column(db.Boolean, nullable=False, default=False)
    public_phone = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_a_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=False, index=True)
    donor_b_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    __table_args__ = (db.UniqueConstraint("donor_a_id", "donor_b_id", name="uq_conversation_pair"),)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=False, index=True)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), index=True)


class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=False, unique=True, index=True)
    in_site_notifications = db.Column(db.Boolean, nullable=False, default=True)
    browser_notifications = db.Column(db.Boolean, nullable=False, default=False)
    email_notifications = db.Column(db.Boolean, nullable=False, default=False)
    show_in_directory = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.now())


class DonationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=False, index=True)
    blood_type = db.Column(db.String(3), nullable=False, index=True)
    city = db.Column(db.String(80), nullable=False, index=True)
    hospital = db.Column(db.String(160), nullable=False)
    urgency = db.Column(db.String(20), nullable=False, default="عادي")
    details = db.Column(db.String(1000), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="مفتوح", index=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), index=True)


with app.app_context():
    db.create_all()
    # Small forward-compatible SQLite migration for databases created by earlier versions.
    try:
        columns = {column["name"] for column in db.inspect(db.engine).get_columns("donor")}
        with db.engine.begin() as connection:
            if "public_phone" not in columns:
                connection.exec_driver_sql("ALTER TABLE donor ADD COLUMN public_phone BOOLEAN NOT NULL DEFAULT 0")
            if "email" not in columns:
                connection.exec_driver_sql("ALTER TABLE donor ADD COLUMN email VARCHAR(254)")
            # Make phone optional on PostgreSQL without touching existing donor rows.
            # Existing phone values remain unchanged; only the NOT NULL constraint is removed.
            if db.engine.dialect.name == "postgresql":
                connection.exec_driver_sql("ALTER TABLE donor ALTER COLUMN phone DROP NOT NULL")
    except Exception:
        app.logger.exception("Database schema check failed")


def send_email_otp(recipient, code):
    """Send an email verification code through Gmail SMTP."""
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        return False, "smtp_not_configured"
    message = EmailMessage()
    message["Subject"] = "رمز التحقق | قطرة حياة"
    message["From"] = SMTP_EMAIL
    message["To"] = recipient
    message.set_content(
        f"مرحبًا بك في قطرة حياة\n\nرمز التحقق الخاص بك هو: {code}\n"
        "الرمز صالح لمدة 5 دقائق، ولا تشاركه مع أي شخص.\n\nفريق قطرة حياة"
    )
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=20) as server:
                server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
                server.send_message(message)
        return True, "sent"
    except Exception:
        app.logger.exception("Email OTP delivery failed")
        return False, "smtp_send_failed"


def normalize_saudi_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("966") and len(digits) == 12:
        digits = digits[3:]
    if len(digits) == 10 and digits.startswith("05"):
        digits = digits[1:]
    if len(digits) == 9 and digits.startswith("5"):
        return "966" + digits
    return None


def valid_saudi_phone(phone):
    return normalize_saudi_phone(phone) is not None


@app.route("/donors", methods=["GET"])
def donor_directory():
    """Show all donors who consented to be listed, across every blood type and city."""
    results = Donor.query.filter_by(consent=True).order_by(Donor.created_at.desc()).all()
    results = [d for d in results if not (UserPreference.query.filter_by(donor_id=d.id).first() and not UserPreference.query.filter_by(donor_id=d.id).first().show_in_directory)]
    return render_template(
        "index.html",
        results=results,
        selected_type="",
        selected_city="",
        searched=True,
        donor_directory=True,
        blood_types=BLOOD_TYPES,
        cities=CITIES,
        total_donors=Donor.query.count(),
        current_donor=current_donor(),
        form={},
    )


@app.route("/explore", methods=["GET", "POST"])
def explore():
    selected_type = ""
    selected_city = ""
    searched = False
    results = []

    if request.method == "POST":
        searched = True
        selected_type = request.form.get("blood_type", "").strip()
        selected_city = request.form.get("city", "").strip()

        query = Donor.query
        if selected_type in BLOOD_TYPES:
            query = query.filter_by(blood_type=selected_type)
        elif selected_type:
            selected_type = ""

        if selected_city in CITIES:
            query = query.filter_by(city=selected_city)
        elif selected_city:
            selected_city = ""

        results = query.order_by(Donor.created_at.desc()).all()

    total_donors = Donor.query.count()
    return render_template(
        "index.html",
        results=results,
        selected_type=selected_type,
        selected_city=selected_city,
        searched=searched,
        donor_directory=False,
        blood_types=BLOOD_TYPES,
        cities=CITIES,
        total_donors=total_donors,
        current_donor=current_donor(),
        form=request.form if request.method == "POST" and request.form.get("full_name") else {},
    )


def current_donor():
    # A donor is active only in the browser session that completed registration.
    donor_id = session.get("active_donor_id")
    if donor_id:
        return db.session.get(Donor, int(donor_id))
    account_id = session.get("account_id")
    if account_id:
        account = db.session.get(Account, int(account_id))
        if account and account.donor_id:
            return db.session.get(Donor, account.donor_id)
    email = session.get("verified_email")
    return Donor.query.filter_by(email=email).first() if email else None


def conversation_pair(first_id, second_id):
    return (min(first_id, second_id), max(first_id, second_id))


@app.route("/messages")
def inbox():
    donor = current_donor()
    if not donor:
        flash("أضف بياناتك كمتبرع أولًا حتى تتمكن من استخدام الرسائل الخاصة.", "error")
        return redirect(url_for("register"))
    conversations = Conversation.query.filter(
        db.or_(Conversation.donor_a_id == donor.id, Conversation.donor_b_id == donor.id)
    ).order_by(Conversation.created_at.desc()).all()
    items = []
    for conversation in conversations:
        other_id = conversation.donor_b_id if conversation.donor_a_id == donor.id else conversation.donor_a_id
        other = db.session.get(Donor, other_id)
        latest = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.created_at.desc(), Message.id.desc()).first()
        if other:
            items.append({"conversation": conversation, "other": other, "latest": latest})
    return render_template("messages.html", donor=donor, items=items)


@app.route("/messages/start/<int:donor_id>", methods=["GET", "POST"])
def start_message(donor_id):
    sender = current_donor()
    if not sender:
        session["message_after_register"] = donor_id
        flash("أضف بياناتك كمتبرع أولًا، وبعدها تقدر تبدأ المحادثة الخاصة.", "error")
        return redirect(url_for("register"))
    recipient = db.session.get(Donor, donor_id)
    if not recipient:
        flash("هذا المتبرع غير موجود.", "error")
        return redirect(url_for("explore"))
    if recipient.id == sender.id:
        flash("ما تقدر تبدأ محادثة مع نفسك.", "error")
        return redirect(url_for("explore"))
    a_id, b_id = conversation_pair(sender.id, recipient.id)
    conversation = Conversation.query.filter_by(donor_a_id=a_id, donor_b_id=b_id).first()
    if not conversation:
        conversation = Conversation(donor_a_id=a_id, donor_b_id=b_id)
        db.session.add(conversation)
        db.session.commit()
    return redirect(url_for("conversation", conversation_id=conversation.id))


@app.route("/messages/<int:conversation_id>", methods=["GET", "POST"])
def conversation(conversation_id):
    donor = current_donor()
    if not donor:
        flash("أضف بياناتك كمتبرع أولًا لاستخدام الرسائل الخاصة.", "error")
        return redirect(url_for("register"))
    convo = db.session.get(Conversation, conversation_id)
    if not convo or donor.id not in (convo.donor_a_id, convo.donor_b_id):
        flash("المحادثة غير موجودة أو لا تملك صلاحية الوصول إليها.", "error")
        return redirect(url_for("inbox"))
    other_id = convo.donor_b_id if convo.donor_a_id == donor.id else convo.donor_a_id
    other = db.session.get(Donor, other_id)
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if not body or len(body) > 2000:
            flash("اكتب رسالة من 1 إلى 2000 حرف.", "error")
        else:
            db.session.add(Message(conversation_id=convo.id, sender_id=donor.id, body=body))
            db.session.commit()
            return redirect(url_for("conversation", conversation_id=convo.id))
    messages = Message.query.filter_by(conversation_id=convo.id).order_by(Message.created_at.asc(), Message.id.asc()).all()
    if messages:
        session["last_seen_message_id"] = max(int(session.get("last_seen_message_id", 0)), max(m.id for m in messages))
    whatsapp_link = None
    if other and other.public_phone and other.phone:
        whatsapp_link = "https://wa.me/" + re.sub(r"\D", "", other.phone)
    return render_template("conversation.html", donor=donor, other=other, conversation=convo, messages=messages, whatsapp_link=whatsapp_link)


@app.route("/manifest.webmanifest")
def pwa_manifest():
    return send_from_directory(app.root_path, "manifest.webmanifest", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def pwa_service_worker():
    response = make_response(send_from_directory(os.path.join(app.root_path, "static"), "service-worker.js", mimetype="application/javascript"))
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/", methods=["GET"])
def index():
    """Public landing page: visitors can browse and search without signing in."""
    return redirect(url_for("explore"))


@app.route("/email-login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        account = Account.query.filter_by(email=email).first() if email else None
        if not account or not check_password_hash(account.password_hash, password):
            flash("البريد الإلكتروني أو كلمة المرور غير صحيحة.", "error")
            return render_template("auth.html", mode="login")
        session.clear()
        session["account_id"] = account.id
        if account.donor_id:
            session["active_donor_id"] = account.donor_id
        session.permanent = True
        flash("تم تسجيل الدخول بنجاح.", "success")
        return redirect(url_for("index"))
    return render_template("auth.html", mode="login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("أدخل بريدًا إلكترونيًا صحيحًا.", "error")
        elif len(password) < 8:
            flash("كلمة المرور يجب أن تكون 8 أحرف على الأقل.", "error")
        elif password != confirm:
            flash("كلمتا المرور غير متطابقتين.", "error")
        elif Account.query.filter_by(email=email).first():
            flash("هذا البريد مسجل بالفعل. سجّل الدخول بدلًا من ذلك.", "error")
        else:
            account = Account(email=email, password_hash=generate_password_hash(password))
            db.session.add(account)
            db.session.commit()
            session.clear()
            session["account_id"] = account.id
            session.permanent = True
            flash("تم إنشاء حسابك. يمكنك الآن تسجيل بياناتك كمتبرع.", "success")
            return redirect(url_for("register"))
        return render_template("auth.html", mode="signup")
    return render_template("auth.html", mode="signup")

@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    return redirect(url_for("register"))


@app.route("/logout")
def logout():
    session.pop("account_id", None)
    session.pop("active_donor_id", None)
    session.pop("verified_email", None)
    session.pop("verified_phone", None)
    flash("تم إنهاء الجلسة على هذا الجهاز.", "success")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register donor details directly, without email or SMS login."""
    if request.method == "POST":
        if request.form.get("website", "").strip():
            flash("تعذّر إتمام التسجيل. حاول مرة أخرى.", "error")
            return redirect(url_for("register"))
        full_name = request.form.get("full_name", "").strip()
        phone_input = request.form.get("phone", "").strip()
        phone = normalize_saudi_phone(phone_input) if phone_input else None
        age_raw = request.form.get("age", "").strip()
        blood_type = request.form.get("blood_type", "").strip()
        city = request.form.get("city", "").strip()
        consent = request.form.get("consent") == "yes"
        public_phone = request.form.get("public_phone") == "yes"
        errors = []
        if len(full_name) < 2 or len(full_name) > 100:
            errors.append("اكتب الاسم بشكل صحيح.")
        if phone_input and not phone:
            errors.append("إذا رغبت بإضافة رقم الجوال، أدخل رقمًا سعوديًا صحيحًا.")
        elif phone and Donor.query.filter_by(phone=phone).first():
            errors.append("رقم الجوال مسجل بالفعل. إذا كانت هذه بياناتك، تواصل مع مسؤول المنصة لتحديثها.")
        try:
            age = int(age_raw)
            if age < 18 or age > 100:
                errors.append("يجب أن يكون العمر بين 18 و100 سنة للتسجيل في هذه النسخة.")
        except (ValueError, TypeError):
            age = 0
            errors.append("أدخل العمر بالأرقام.")
        if blood_type not in BLOOD_TYPES:
            errors.append("اختر فصيلة دم صحيحة.")
        if city not in CITIES:
            errors.append("اختر مدينة من القائمة.")
        if not consent:
            errors.append("يجب الموافقة على استخدام البيانات لغرض التواصل بشأن التبرع.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("register.html", blood_types=BLOOD_TYPES, cities=CITIES, form=request.form)

        donor = Donor(full_name=full_name, email=None, phone=phone, age=age,
                      blood_type=blood_type, city=city, consent=True, public_phone=public_phone)
        db.session.add(donor)
        db.session.flush()
        account_id = session.get("account_id")
        account = db.session.get(Account, int(account_id)) if account_id else None
        if account and account.donor_id is None:
            account.donor_id = donor.id
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not save donor registration")
            flash("حدث خطأ أثناء حفظ التسجيل. حاول مرة أخرى لاحقًا.", "error")
            return render_template("register.html", blood_types=BLOOD_TYPES, cities=CITIES, form=request.form)

        # Bind private messages to this browser session, without requiring login.
        target_id = session.pop("message_after_register", None) or request.args.get("message_to", type=int)
        session["active_donor_id"] = donor.id
        if account:
            session["account_id"] = account.id
        session.permanent = True
        flash("تم حفظ بياناتك بنجاح. تقدر الآن تبحث عن متبرعين وتستخدم الرسائل الخاصة.", "success")
        if target_id:
            return redirect(url_for("start_message", donor_id=target_id))
        return redirect(url_for("explore"))
    return render_template("register.html", blood_types=BLOOD_TYPES, cities=CITIES, form={})


@app.route("/api/notifications")
def notifications_api():
    donor = current_donor()
    if not donor:
        return {"count": 0, "latest": []}
    prefs = UserPreference.query.filter_by(donor_id=donor.id).first()
    if prefs and not prefs.in_site_notifications:
        return {"count": 0, "latest": []}
    conversations = Conversation.query.filter(db.or_(Conversation.donor_a_id == donor.id, Conversation.donor_b_id == donor.id)).all()
    conversation_ids = [c.id for c in conversations]
    if not conversation_ids:
        return {"count": 0, "latest": []}
    if "last_seen_message_id" not in session:
        latest_id = db.session.query(func.max(Message.id)).filter(Message.conversation_id.in_(conversation_ids)).scalar() or 0
        session["last_seen_message_id"] = int(latest_id)
        return {"count": 0, "latest": []}
    last_seen = int(session.get("last_seen_message_id", 0))
    incoming = Message.query.filter(Message.conversation_id.in_(conversation_ids), Message.sender_id != donor.id, Message.id > last_seen).order_by(Message.id.asc()).limit(10).all()
    if incoming:
        session["last_seen_message_id"] = max(m.id for m in incoming)
    return {"count": len(incoming), "latest": [{"id": m.id, "body": m.body[:120], "url": url_for("conversation", conversation_id=m.conversation_id)} for m in incoming]}

@app.route("/notifications/seen", methods=["POST"])
def notifications_seen():
    message_id = request.form.get("message_id", type=int) or 0
    session["last_seen_message_id"] = max(message_id, int(session.get("last_seen_message_id", 0)))
    return {"ok": True}


@app.route("/settings", methods=["GET", "POST"])
def settings():
    donor = current_donor()
    if not donor:
        flash("سجّل الدخول أو أضف بياناتك كمتبرع للوصول إلى الإعدادات.", "error")
        return redirect(url_for("login"))
    prefs = UserPreference.query.filter_by(donor_id=donor.id).first()
    if not prefs:
        prefs = UserPreference(donor_id=donor.id)
        db.session.add(prefs)
        db.session.commit()
    if request.method == "POST":
        prefs.in_site_notifications = request.form.get("in_site_notifications") == "yes"
        prefs.browser_notifications = request.form.get("browser_notifications") == "yes"
        prefs.email_notifications = request.form.get("email_notifications") == "yes"
        prefs.show_in_directory = request.form.get("show_in_directory") == "yes"
        db.session.commit()
        flash("تم حفظ إعداداتك.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", donor=donor, prefs=prefs)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    donor = current_donor()
    if not donor:
        flash("سجّل الدخول أولًا للوصول إلى ملفك الشخصي.", "error")
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        age_raw = request.form.get("age", "").strip()
        blood = request.form.get("blood_type", "").strip()
        city = request.form.get("city", "").strip()
        phone_input = request.form.get("phone", "").strip()
        public_phone = request.form.get("public_phone") == "yes"
        try:
            age = int(age_raw)
        except ValueError:
            age = 0
        phone = normalize_saudi_phone(phone_input) if phone_input else None
        duplicate = Donor.query.filter(Donor.phone == phone, Donor.id != donor.id).first() if phone else None
        if not (2 <= len(name) <= 100) or not (18 <= age <= 100) or blood not in BLOOD_TYPES or city not in CITIES:
            flash("راجع الاسم والعمر والفصيلة والمدينة.", "error")
        elif phone_input and not phone:
            flash("رقم الجوال غير صحيح.", "error")
        elif duplicate:
            flash("رقم الجوال مستخدم في حساب آخر.", "error")
        else:
            donor.full_name, donor.age, donor.blood_type, donor.city = name, age, blood, city
            donor.phone = phone
            donor.public_phone = bool(phone and public_phone)
            db.session.commit()
            flash("تم تحديث ملفك الشخصي.", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html", donor=donor, blood_types=BLOOD_TYPES, cities=CITIES)


@app.route("/requests", methods=["GET", "POST"])
def donation_requests():
    donor = current_donor()
    if request.method == "POST":
        if not donor:
            flash("سجّل الدخول أو أضف بياناتك كمتبرع لنشر طلب.", "error")
            return redirect(url_for("login"))
        blood = request.form.get("blood_type", "").strip()
        city = request.form.get("city", "").strip()
        hospital = request.form.get("hospital", "").strip()[:160]
        urgency = request.form.get("urgency", "عادي")
        details = request.form.get("details", "").strip()[:1000]
        if blood not in BLOOD_TYPES or city not in CITIES or len(hospital) < 2 or urgency not in ("عادي", "عاجل"):
            flash("أكمل الفصيلة والمدينة واسم المستشفى بشكل صحيح.", "error")
        else:
            item = DonationRequest(donor_id=donor.id, blood_type=blood, city=city, hospital=hospital, urgency=urgency, details=details)
            db.session.add(item)
            db.session.commit()
            flash("تم نشر الطلب. يرجى تأكيد الاحتياج مع المستشفى مباشرة.", "success")
            return redirect(url_for("donation_requests"))
    items = DonationRequest.query.filter_by(status="مفتوح").order_by(DonationRequest.created_at.desc()).limit(100).all()
    return render_template("requests.html", donor=donor, items=items, blood_types=BLOOD_TYPES, cities=CITIES)


@app.route("/requests/<int:request_id>/close", methods=["POST"])
def close_donation_request(request_id):
    donor = current_donor()
    item = db.session.get(DonationRequest, request_id)
    if not donor or not item or item.donor_id != donor.id:
        flash("لا تملك صلاحية إغلاق هذا الطلب.", "error")
    else:
        item.status = "مغلق"
        db.session.commit()
        flash("تم إغلاق الطلب.", "success")
    return redirect(url_for("donation_requests"))

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# Private admin panel: configure ADMIN_PASSWORD in the hosting environment.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()

ADMIN_TEMPLATE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>إدارة قطرة حياة</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f5fb;color:#20243a;margin:0;padding:24px}
main{max-width:1000px;margin:auto;background:white;padding:24px;border-radius:16px;box-shadow:0 8px 28px #18204a12}
h1{color:#5541a8} input,button{padding:10px;border-radius:8px;border:1px solid #ccc}
button{cursor:pointer;background:#5946b2;color:white;border:0} .danger{background:#b42332}
table{width:100%;border-collapse:collapse;margin-top:18px}th,td{padding:10px;border-bottom:1px solid #eee;text-align:right}
.msg{padding:10px;background:#fce8e8;border-radius:8px;margin:8px 0}.muted{color:#666}
</style></head><body><main>
<h1>لوحة إدارة قطرة حياة</h1>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for category, message in messages %}<div class="msg">{{ message }}</div>{% endfor %}
{% endwith %}
{% if not admin_logged_in %}
<p>الدخول مخصص لمسؤول المنصة.</p>
<form method="post">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>كلمة المرور <input type="password" name="password" required autocomplete="current-password"></label>
<button type="submit" name="action" value="login">دخول</button>
</form>
{% else %}
<p>تم تسجيل الدخول كمسؤول. إجمالي المتبرعين: <strong>{{ donors|length }}</strong></p>
<form method="post" action="{{ url_for('admin_panel') }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button type="submit" name="action" value="logout">تسجيل الخروج</button>
</form>
<table><thead><tr><th>الاسم</th><th>الجوال</th><th>الفصيلة</th><th>المدينة</th><th>العمر</th><th>الإجراء</th></tr></thead><tbody>
{% for donor in donors %}
<tr><td>{{ donor.full_name }}</td><td>{{ donor.phone or "—" }}</td><td>{{ donor.blood_type }}</td><td>{{ donor.city }}</td><td>{{ donor.age }}</td><td>
<form method="post" action="{{ url_for('admin_panel') }}" onsubmit="return confirm('تأكيد حذف بيانات المتبرع {{ donor.full_name }}؟');">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="donor_id" value="{{ donor.id }}">
<button class="danger" type="submit" name="action" value="delete">حذف المتبرع</button>
</form></td></tr>
{% else %}<tr><td colspan="6">لا يوجد متبرعون مسجلون.</td></tr>{% endfor %}
</tbody></table>
<p class="muted">حذف المتبرع يحذف أيضًا الرسائل والمحادثات المرتبطة به.</p>
{% endif %}
</main></body></html>
"""

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if "admin_csrf" not in session:
        session["admin_csrf"] = secrets.token_urlsafe(32)

    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        if not secrets.compare_digest(submitted_token, session.get("admin_csrf", "")):
            flash("انتهت صلاحية الطلب. حدّث الصفحة وحاول مرة أخرى.", "error")
            return redirect(url_for("admin_panel"))

        action = request.form.get("action", "")
        if action == "login":
            if not ADMIN_PASSWORD:
                flash("لوحة الإدارة غير مفعلة. أضف ADMIN_PASSWORD في إعدادات البيئة.", "error")
            elif secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
                session.clear()
                session["is_admin"] = True
                session["admin_csrf"] = secrets.token_urlsafe(32)
                session.permanent = True
                flash("تم تسجيل الدخول بنجاح.", "success")
            else:
                time.sleep(1)
                flash("كلمة المرور غير صحيحة.", "error")
            return redirect(url_for("admin_panel"))

        if not session.get("is_admin"):
            flash("سجّل الدخول أولًا.", "error")
            return redirect(url_for("admin_panel"))

        if action == "logout":
            session.clear()
            return redirect(url_for("admin_panel"))

        if action == "delete":
            donor_id = request.form.get("donor_id", type=int)
            donor = db.session.get(Donor, donor_id) if donor_id else None
            if not donor:
                flash("المتبرع غير موجود.", "error")
                return redirect(url_for("admin_panel"))

            conversation_ids = [
                row[0] for row in db.session.query(Conversation.id).filter(
                    db.or_(Conversation.donor_a_id == donor.id,
                           Conversation.donor_b_id == donor.id)
                ).all()
            ]
            try:
                if conversation_ids:
                    Message.query.filter(Message.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
                    Conversation.query.filter(Conversation.id.in_(conversation_ids)).delete(synchronize_session=False)
                # Also remove any messages sent by this donor in case of inconsistent legacy data.
                Message.query.filter_by(sender_id=donor.id).delete(synchronize_session=False)
                db.session.delete(donor)
                db.session.commit()
                flash("تم حذف بيانات المتبرع والمحادثات المرتبطة به.", "success")
            except Exception:
                db.session.rollback()
                app.logger.exception("Admin donor deletion failed")
                flash("تعذر حذف المتبرع. راجع سجل التطبيق.", "error")
            return redirect(url_for("admin_panel"))

    logged_in = bool(session.get("is_admin"))
    donors = Donor.query.order_by(Donor.created_at.desc()).all() if logged_in else []
    return render_template_string(
        ADMIN_TEMPLATE,
        admin_logged_in=logged_in,
        donors=donors,
        csrf_token=session["admin_csrf"],
    )


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
