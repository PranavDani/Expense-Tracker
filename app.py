from flask_sqlalchemy import sqlalchemy
from flask import Flask, jsonify, redirect, render_template, request, session

# from models import db
from sqlalchemy.orm import scoped_session, sessionmaker

# from flask_cors import CORS
from dotenv import load_dotenv

import requests
import psycopg2
import os

load_dotenv()

# PostgreSQL Database credentials loaded from the .env file
DATABASE = os.getenv("DATABASE")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")


app = Flask(__name__)


try:
    con = psycopg2.connect(database=DATABASE, user=DATABASE_USERNAME, password=DATABASE_PASSWORD)

    db = con.cursor()
    print("Database Connection Successful")
    # # GET: Fetch all movies from the database
    # @app.route("/")
    # def fetch_all_movies():
    #     db.execute("SELECT * FROM usercategories")
    #     rows = db.fetchall()
    #     print(rows)
    #     return jsonify(rows)

except:
    print("Error")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST
    if request.method == "POST":
        print("TODO")

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print("TODO")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    # session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/")
def hello_world():
    return render_template("layout.html")


if __name__ == "__main__":
    app.run(debug=True)
