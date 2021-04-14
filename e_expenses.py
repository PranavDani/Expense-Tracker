import requests
import psycopg2
import os

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


# Expense functions
# Add Expenses
def addExpenses(formData, userID):
    expenses = []
    expense = {"description": None, "category": None, "date": None, "amount": None}
    # expenses.append(expense)
    print(expenses)

    # Check for the location from where addexepense is being executed
    if "." not in formData[0][0]:
        for key, value in formData:
            expense[key] = value.strip()

        expense["amount"] = float(expense["amount"])
        expenses.append(expense)

    else:
        counter = 0
        for key, value in formData:
            cleanKey = key.split(".")
            expense[cleanKey[0]] = value.strip()
            counter += 1
            # Every 4 loops add the expense to the list of expenses (because there are 4 fields for an expense record)
            if counter % 4 == 0:
                # Store the amount as a float
                expense["amount"] = float(expense["amount"])
                # Add dictionary to list
                expenses.append(expense.copy())

    print(expense)
    print(expenses)

    for expense in expenses:
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        db.execute(
            "insert into expenses (description, category, expenseDate, amount, submitTime, user_id) values (:description, :category, :expenseDate, :amount, :submitTime, :usersID)",
            {
                "description": expense["description"],
                "category": expense["category"],
                "expenseDate": expense["date"],
                "amount": expense["amount"],
                "submitTime": now,
                "usersID": userID,
            },
        )
    db.commit()
    return expenses


# Delete existing expense
def deleteExpense(expense, userID):
    result = db.execute(
        "delete from expense where user_id = :usersID and id = :oldExpenseID",
        {"usersID": userID, "oldExpenseID": expense["id"]},
    )
    db.commit()