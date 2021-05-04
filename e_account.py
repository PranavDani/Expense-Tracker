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
engine = create_engine(os.getenv("DATABASE_URL"))
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


def getBudgets(userID, year=None):
    budgets = []
    budget = {"name": None, "amount": 0, "spent": 0, "remaining": 0}

    if not year:
        year = datetime.now().year

    budgets_query = e_expenses.getBudgets(userID)
    user = session["user_id"]
    if budgets_query and user in budgets_query:
        for record in budgets_query[user]:
            budgetID = record["id"]
            budget["name"] = record["name"]
            budget["amount"] = record["amount"]

            # Query the DB for the budgets total spent amount (calculated as the sum of expenses with categories that match the categories selected for the individual budget)
            results = db.execute(
                "SELECT SUM(amount) AS spent FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = :year AND category IN (SELECT categories.name FROM budgetcategories INNER JOIN categories on budgetcategories.category_id = categories.id WHERE budgetcategories.budgets_id = :budgetID)",
                {"usersID": userID, "year": year, "budgetID": budgetID},
            ).fetchall()
            budget_TotalSpent = convertSQLToDict(results)

            if budget_TotalSpent[0]["spent"] == None:
                budget["spent"] = 0
            else:
                budget["spent"] = budget_TotalSpent[0]["spent"]

            # Set the remaining amount to 0 if the user has spent more than they budgeted for so that the charts don't look crazy
            if budget["spent"] > budget["amount"]:
                budget["remaining"] = 0
            else:
                budget["remaining"] = budget["amount"] - budget["spent"]

            # Add the budget to the list
            budgets.append(budget.copy())

        return budgets

    else:
        return None


def getStatistics(userID):
    stats = {"registerDate": None, "totalExpenses": None, "totalBudgets": None, "totalCategories": None}

    registerDate = db.execute("SELECT registerDate FROM users WHERE id = :usersID", {"usersID": userID}).fetchone()[0]
    stats["registerDate"] = registerDate.split()[0]

    # Get total expenses
    totalExpenses = db.execute(
        "SELECT COUNT(*) AS count FROM expenses WHERE user_id = :usersID", {"usersID": userID}
    ).fetchone()[0]
    stats["totalExpenses"] = totalExpenses

    # Get total budgets
    totalBudgets = db.execute(
        "SELECT COUNT(*) AS count FROM budgets WHERE user_id = :usersID", {"usersID": userID}
    ).fetchone()[0]
    stats["totalBudgets"] = totalBudgets

    totalCategories = db.execute(
        "SELECT COUNT(*) AS count FROM userCategories INNER JOIN categories ON userCategories.category_id = categories.id WHERE userCategories.user_id = :usersID",
        {"usersID": userID},
    ).fetchone()[0]
    stats["totalCategories"] = totalCategories

    return stats


def getAllUserInfo(userID):

    # Create dict to hold user info
    user = {"name": None, "income": None, "stats": None}

    # Get the users account name
    user["name"] = getUsername(userID)

    # Get the users income
    user["income"] = getIncome(userID)

    user["stats"] = getStatistics(userID)

    return user
