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


def getUsername(userID):
    name = db.execute("select username from users where id = :usersID", {"usersID": userID}).fetchone()[0]
    return name


def getIncome(userID):
    income = db.execute("SELECT income FROM users WHERE id = :usersID", {"usersID": userID}).fetchone()[0]

    return float(income)


def updateIncome(income, userID):
    rows = db.execute(
        "UPDATE users SET income = :newIncome WHERE id = :usersID", {"newIncome": income, "usersID": userID}
    ).rowcount
    db.commit()

    # Return an error message if the record could not be updated
    if rows != 1:
        return {"apology": "Sorry, Update Income is angry. Try again!"}
    else:
        return rows


def updatePassword(oldPass, newPass, userID):
    # Ensure the current password matches the hash in the DB
    userHash = db.execute("SELECT hash FROM users WHERE id = :usersID", {"usersID": userID}).fetchone()[0]
    if not check_password_hash(userHash, oldPass):
        return {"apology": "invalid password"}
    # Generate hash for new password
    hashedPass = generate_password_hash(newPass)
    # Update the users account to use the new password hash
    rows = db.execute(
        "UPDATE users SET hash = :hashedPass WHERE id = :usersID", {"hashedPass": hashedPass, "usersID": userID}
    ).rowcount
    db.commit()
    # Return an error message if the password could not be updated
    if rows != 1:
        return {"apology": "Sorry, Update Password is having issues. Try again!"}
    else:
        return rows


def getAllUserInfo(userID):

    # Create dict to hold user info
    user = {"name": None, "income": None}

    # Get the users account name
    user["name"] = getUsername(userID)

    # Get the users income
    user["income"] = getIncome(userID)

    return user