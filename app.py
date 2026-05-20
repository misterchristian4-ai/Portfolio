import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin,
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user 
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-only')

# Setup Database & Authentication
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Automatically redirects unauthorized users to login

# Ensure the upload directory exists
UPLOAD_FOLDER = os.path.join('static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# MODELS
# =========================

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(100))
    github = db.Column(db.String(200))
    demo = db.Column(db.String(200))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(200))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():
    projects = Project.query.all()
    return render_template("index.html", projects=projects)


# =========================
# CONTACT FORM
# =========================

@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    print(f"Contact Form Submission:\nName: {name}\nEmail: {email}\nMessage: {message}")
    return "Message Sent Successfully"


# =========================
# SIGN UP
# =========================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    # Security Rule: If a user is already logged in, send them to the dashboard
    if current_user.is_authenticated:
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")

        # 1. Check if ANY user already exists in the database
        existing_admin = User.query.first()
        if existing_admin:
            flash("Registration locked. An administrator account already exists.")
            return redirect("/login")

        # 2. Check if the registration fields are empty
        if not username or not password:
            flash("Username and password are required.")
            return redirect("/signup")

        # 3. Securely hash the password string
        hashed_pw = generate_password_hash(password, method="scrypt")

        # 4. Save the new admin to your database
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash("Admin account created successfully! Please log in.")
        return redirect("/login")

    return render_template("signup.html")

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect("/dashboard")
        else:
            flash("Invalid username or password.")
            return redirect("/login")

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():
    projects = db.session.query(Project).all()
    return render_template("dashboard.html", projects=projects)


# =========================
# LOGOUT (FIXED: Removed <int:id>)
# =========================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect("/")


# =========================
# EDIT PROJECT
# =========================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_project(id):
    project = db.session.get(Project, id)
    if not project:
        flash("Project not found.")
        return redirect("/dashboard")

    if request.method == "POST":
        project.title = request.form.get("title")
        project.description = request.form.get("description")
        project.github = request.form.get("github")
        project.demo = request.form.get("demo")

        # Handle optional new image upload
        image = request.files.get("image")
        if image and image.filename != '':
            filename = image.filename
            image.save(os.path.join(UPLOAD_FOLDER, filename))
            project.image = filename

        db.session.commit()
        flash("Project Updated Successfully!")
        return redirect("/dashboard")

    return render_template("edit_project.html", project=project)


# =========================
# ADD PROJECT
# =========================

@app.route("/add-project", methods=["GET", "POST"])
@login_required
def add_project():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        github = request.form.get("github")
        demo = request.form.get("demo")
        image = request.files.get("image")

        filename = ""
        if image and image.filename != '':
            filename = image.filename
            image.save(os.path.join(UPLOAD_FOLDER, filename))

        new_project = Project(
            title=title,
            description=description,
            image=filename,
            github=github,
            demo=demo
        )

        db.session.add(new_project)
        db.session.commit()
        flash("Project Added Successfully")
        return redirect("/dashboard")

    return render_template("add_project.html")


# =========================
# DELETE PROJECT (FIXED: Added safety checks)
# =========================

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    project = db.session.get(Project, id)
    
    if project:
        db.session.delete(project)
        db.session.commit()
        flash("Project Deleted")
    else:
        flash("Project not found or already deleted.")

    return redirect("/dashboard")


# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    db.create_all()


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)