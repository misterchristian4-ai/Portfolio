"""
Portfolio website — Flask application.

A small Flask app that serves a public portfolio homepage and provides
an authenticated dashboard for managing (adding, editing, deleting)
portfolio projects.
"""

import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_mail import Mail, Message as MailMessage
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

# Email notifications for contact-form submissions.
# Leave MAIL_USERNAME / MAIL_PASSWORD unset to disable email and rely on the
# dashboard's Messages page instead — submissions are always saved to the
# database either way.
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", os.environ.get("MAIL_USERNAME"))

db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# =============================================================================
# MODELS
# =============================================================================

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(100))
    github = db.Column(db.String(200))
    demo = db.Column(db.String(200))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =============================================================================
# HELPERS
# =============================================================================

def allowed_file(filename):
    """Return True if the filename has an allowed image extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_image(file_storage):
    """
    Safely save an uploaded image and return its stored filename,
    or None if no valid file was provided.
    """
    if not file_storage or file_storage.filename == "":
        return None

    if not allowed_file(file_storage.filename):
        flash("Unsupported image type. Please upload a PNG, JPG, GIF, or WEBP file.")
        return None

    filename = secure_filename(file_storage.filename)
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


# =============================================================================
# PUBLIC ROUTES
# =============================================================================

@app.route("/")
def home():
    projects = Project.query.all()
    return render_template("index.html", projects=projects)


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    body = request.form.get("message", "").strip()

    if not name or not email or not body:
        flash("Please fill out all fields before sending.")
        return redirect(url_for("home") + "#contact")

    new_message = Message(name=name, email=email, body=body)
    db.session.add(new_message)
    db.session.commit()

    if app.config["MAIL_USERNAME"] and app.config["MAIL_PASSWORD"]:
        try:
            notification = MailMessage(
                subject=f"New portfolio message from {name}",
                recipients=[ADMIN_EMAIL],
                reply_to=email,
                body=f"From: {name} <{email}>\n\n{body}",
            )
            mail.send(notification)
        except Exception:
            # Don't let a broken mail server stop the message from being
            # saved — it's still visible on the dashboard's Messages page.
            app.logger.exception("Failed to send contact notification email.")

    flash("Thanks! Your message has been sent.")
    return redirect(url_for("home") + "#contact")


# =============================================================================
# AUTHENTICATION
# =============================================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("signup"))

        if User.query.filter_by(username=username).first():
            flash("That username is already taken.")
            return redirect(url_for("signup"))

        new_user = User(
            username=username,
            password=generate_password_hash(password),
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash("Account created successfully!")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("home"))


# =============================================================================
# DASHBOARD (PROTECTED)
# =============================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    projects = Project.query.all()
    return render_template("dashboard.html", projects=projects)


@app.route("/messages")
@login_required
def messages():
    all_messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template("messages.html", messages=all_messages)


@app.route("/messages/delete/<int:message_id>")
@login_required
def delete_message(message_id):
    message = db.session.get(Message, message_id)
    if message:
        db.session.delete(message)
        db.session.commit()
        flash("Message deleted.")
    else:
        flash("Message not found.")

    return redirect(url_for("messages"))


@app.route("/add-project", methods=["GET", "POST"])
@login_required
def add_project():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        github = request.form.get("github")
        demo = request.form.get("demo")
        filename = save_uploaded_image(request.files.get("image"))

        new_project = Project(
            title=title,
            description=description,
            image=filename,
            github=github,
            demo=demo,
        )
        db.session.add(new_project)
        db.session.commit()

        flash("Project added successfully!")
        return redirect(url_for("dashboard"))

    return render_template("add_project.html")


@app.route("/edit/<int:project_id>", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        flash("Project not found.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        project.title = request.form.get("title")
        project.description = request.form.get("description")
        project.github = request.form.get("github")
        project.demo = request.form.get("demo")

        filename = save_uploaded_image(request.files.get("image"))
        if filename:
            project.image = filename

        db.session.commit()
        flash("Project updated successfully!")
        return redirect(url_for("dashboard"))

    return render_template("edit_project.html", project=project)


@app.route("/delete/<int:project_id>")
@login_required
def delete(project_id):
    project = db.session.get(Project, project_id)
    if project:
        db.session.delete(project)
        db.session.commit()
        flash("Project deleted.")
    else:
        flash("Project not found.")

    return redirect(url_for("dashboard"))


# =============================================================================
# ENTRY POINT
# =============================================================================

def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
