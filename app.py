import requests
import psycopg2
import os
import e_expenses
import e_categories

from flask_sqlalchemy import sqlalchemy
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv
from datetime import datetime
from saviour import apology, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import create_engine

load_dotenv()

# PostgreSQL Database credentials loaded from the .env file
DATABASE = os.getenv("DATABASE")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies) Cookies are sometimes helpfull but mostly bad 😂
# app.config["SESSION_FILE_DIR"] = mkdtemp() # only remove comment when testing locally for benefit of temp directories
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Create engine object to manage connections to DB, and scoped session to separate user interactions with DB
engine = create_engine(os.getenv("DATABASE_LINK"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST
    if request.method == "POST":
        # Query DB for all existing user names and make sure new username isn't already taken
        username = request.form.get("username").strip()
        existingUsers = db.execute(
            "SELECT username FROM users WHERE LOWER(username) = :username", {"username": username.lower()}
        ).fetchone()
        if existingUsers:
            return render_template("register.html", username=username)

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        password = request.form.get("password")
        if not password:
            return apology("must provide password", 403)

        # Insert user into the database
        hashedPass = generate_password_hash(password)
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        newUserID = db.execute(
            "INSERT INTO users (username, hash, registerDate, lastLogin) VALUES (:username, :hashedPass, :registerDate, :lastLogin) RETURNING id",
            {"username": username, "hashedPass": hashedPass, "registerDate": now, "lastLogin": now},
        ).fetchone()[0]
        db.commit()

        # Create default spending categories for user
        db.execute(
            "INSERT INTO userCategories (category_id, user_id) VALUES (1, :usersID), (2, :usersID), (3, :usersID), (4, :usersID), (5, :usersID), (6, :usersID), (7, :usersID), (8, :usersID)",
            {"usersID": newUserID},
        )
        db.commit()

        # Auto-login the user after creating their username
        session["user_id"] = newUserID

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST
    if request.method == "POST":
        # check for username and password
        if not request.form.get("username"):
            return apology("Enter username", 403)

        elif not request.form.get("password"):
            return apology("Enter password", 403)

        # Query database for username
        rows = db.execute(
            "select * from users where username = :username", {"username": request.form.get("username")}
        ).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

        # start session
        session["user_id"] = rows[0]["id"]

        # record login time
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        db.execute(
            "update users set lastLogin = :lastLogin where id = :usersID",
            {"lastLogin": now, "usersID": session["user_id"]},
        )
        db.commit()

        # redirect user to the home page
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # if session.user_id pending
    # return render_template("layout.html")
    """Addition of more stuff is remaining"""
    if request.method == "GET":
        # Get the users spend categories (for quick expense modal)
        categories = e_categories.getSpendCategories(session["user_id"])
        # Get todays date (for quick expense modal)
        date = datetime.today().strftime("%Y-%m-%d")
        return render_template("index.html", categories=categories, date=date)

    else:
        # Get all of the expenses provided from the HTML form
        formData = list(request.form.items())
        # Add expenses to the DB for user
        expenses = e_expenses.addExpenses(formData, session["user_id"])
        # Redirect to results page and render a summary of the submitted expenses
        return render_template("expensed.html", results=expenses)


@app.route("/expenses")
@login_required
def expenses():
    """Manage Expenses"""
    return render_template("expenses.html")


@app.route("/addexpenses", methods=["GET", "POST"])
@login_required
def addexpenses():
    """Add expenses"""
    """Issue of multiple inputs is fixed"""

    if request.method == "POST":
        formData = list(request.form.items())
        expenses = e_expenses.addExpenses(formData, session["user_id"])
        return render_template("expensed.html", results=expenses)

    else:
        categories = e_categories.getSpendCategories(session["user_id"])
        date = datetime.today().strftime("%Y-%m-%d")
        return render_template("addexpenses.html", categories=categories, date=date)


if __name__ == "__main__":
    app.run(debug=True)