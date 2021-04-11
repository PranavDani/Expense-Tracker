import requests
import psycopg2
import os

from flask_sqlalchemy import sqlalchemy
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv
from datetime import datetime
from saviour import apology, login_required, convertSQLToDict
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


def getSpendCategories(userID):
    results = db.execute(
        "select categories.name from usercategories inner join categories on usercategories.category_id = categories.id where usercategories.user_id = :usersID",
        {"usersID": userID},
    ).fetchall()
    categories = convertSQLToDict(results)
    return categories
