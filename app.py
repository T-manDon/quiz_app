from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")  # Use environment variable for secret key

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect unauthorized users to login page

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Define the User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primary key
    username = db.Column(db.String(150), nullable=False, unique=True)  # Username
    password = db.Column(db.String(150), nullable=False)  # Password (hashed)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Load user function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registration route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists. Try a different one.")
            return redirect(url_for("register"))

        # Create new user and add to database
        new_user = User(username=username)
        new_user.set_password(password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! You can now log in.")
            return redirect(url_for("login"))
        except Exception as e:
            logging.error(f"Error during registration: {e}")
            flash("An error occurred during registration. Please try again.")
            return redirect(url_for("register"))
    
    return render_template("register.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the user exists in the database
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("home"))

        flash("Login failed. Check your username and password.")
        return redirect(url_for("login"))

    return render_template("login.html")

# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# Home route
@app.route("/")
def home():
    return render_template("home.html")

# Define the Quiz model
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primary key
    question = db.Column(db.String(255), nullable=False)  # The question text
    option_a = db.Column(db.String(150), nullable=False)  # Option A
    option_b = db.Column(db.String(150), nullable=False)  # Option B
    option_c = db.Column(db.String(150), nullable=False)  # Option C
    option_d = db.Column(db.String(150), nullable=False)  # Option D
    correct_answer = db.Column(db.String(1), nullable=False)  # The correct answer (A/B/C/D)

    def __repr__(self):
        return f"<Quiz {self.id}>"

# Route to insert sample quiz questions
@app.route("/add_sample_questions")
def add_sample_questions():
    try:
        if Quiz.query.count() == 0:  # Add questions only if the table is empty
            sample_questions = [
                Quiz(
                    question="What is the capital of France?",
                    option_a="Berlin", option_b="Madrid", option_c="Paris", option_d="Rome", correct_answer="C"
                ),
                Quiz(
                    question="What is 2 + 2?",
                    option_a="3", option_b="4", option_c="5", option_d="6", correct_answer="B"
                ),
                Quiz(
                    question="Which planet is known as the Red Planet?",
                    option_a="Earth", option_b="Mars", option_c="Jupiter", option_d="Venus", correct_answer="B"
                )
            ]

            db.session.add_all(sample_questions)
            db.session.commit()
            return "Sample questions added!"
        else:
            return "Sample questions already exist in the database."
    except Exception as e:
        logging.error(f"Error adding sample questions: {e}")
        return "An error occurred while adding sample questions."

# Route to display quiz questions
@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    # Get all quiz questions
    questions = Quiz.query.all()

    # Handle form submission for quiz answers
    if request.method == "POST":
        score = 0
        for question in questions:
            user_answer = request.form.get(f"question_{question.id}")
            if user_answer == question.correct_answer:
                score += 1

        flash(f"Your score is {score} out of {len(questions)}")
        return render_template("quiz.html", questions=questions, score=score)

    return render_template("quiz.html", questions=questions)

# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_DEBUG', '0').lower() in ['true', '1', 't']
    app.run(debug=debug_mode)