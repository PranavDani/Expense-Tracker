import requests
import psycopg2
import calendar
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


def getTotalSpend_Year(userID):
    results = db.execute(
        "SELECT SUM(amount) AS expenses_year FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = date_part('year', CURRENT_DATE)",
        {"usersID": userID},
        # Source = https://www.postgresqltutorial.com/postgresql-date_part/
    ).fetchall()

    totalSpendYear = convertSQLToDict(results)

    return totalSpendYear[0]["expenses_year"]


# Get and return the users total spend for the current month
def getTotalSpend_Month(userID):
    results = db.execute(
        "SELECT SUM(amount) AS expenses_month FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = date_part('year', CURRENT_DATE) AND date_part('month', date(expensedate)) = date_part('month', CURRENT_DATE)",
        {"usersID": userID},
    ).fetchall()

    totalSpendMonth = convertSQLToDict(results)

    return totalSpendMonth[0]["expenses_month"]


def getTotalSpend_Week(userID):
    # Query note: Day 0 of a week == Sunday. This query grabs expenses between the *current* weeks Monday and Sunday.
    results = db.execute(
        "SELECT SUM(amount) AS expenses_week FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = date_part('year', CURRENT_DATE) AND date_part('week', date(expensedate)) = date_part('week', CURRENT_DATE)",
        {"usersID": userID},
    ).fetchall()

    totalSpendWeek = convertSQLToDict(results)

    return totalSpendWeek[0]["expenses_week"]


# Get the users total income
def getIncome(userID):
    income = db.execute("SELECT income FROM users WHERE id = :usersID", {"usersID": userID}).fetchone()[0]

    return float(income)


# Get and return the users last 5 expenses
def getLastFiveExpenses(userID):
    results = db.execute(
        "SELECT description, category, expenseDate, amount FROM expenses WHERE user_id = :usersID ORDER BY id DESC LIMIT 5",
        {"usersID": userID},
    ).fetchall()

    lastFiveExpenses = convertSQLToDict(results)

    if lastFiveExpenses:
        return lastFiveExpenses
    else:
        return None


# Delete existing expense
def deleteExpense(expense, userID):
    result = db.execute(
        "delete from expense where user_id = :usersID and id = :oldExpenseID",
        {"usersID": userID, "oldExpenseID": expense["id"]},
    )
    db.commit()


def getExpense(formData, userID):
    expense = {
        "description": None,
        "category": None,
        "date": None,
        "amount": None,
        "submitTime": None,
        "id": None,
    }

    expense["description"] = formData.get("oldDescription").strip()
    expense["category"] = formData.get("oldCategory").strip()
    expense["date"] = formData.get("oldDate").strip()
    expense["amount"] = formData.get("oldAmount").strip()
    expense["submitTime"] = formData.get("submitTime").strip()

    expense["amount"] = float(expense["amount"].replace("$" or "₹", "").replace(",", ""))

    expenseID = db.execute(
        "SELECT id FROM expenses WHERE user_id = :usersID AND description = :oldDescription AND category = :oldCategory AND expenseDate = :oldDate AND amount = :oldAmount AND submitTime = :oldSubmitTime",
        {
            "usersID": userID,
            "oldDescription": expense["description"],
            "oldCategory": expense["category"],
            "oldDate": expense["date"],
            "oldAmount": expense["amount"],
            "oldSubmitTime": expense["submitTime"],
        },
    ).fetchone()

    if expenseID:
        expense["id"] = expenseID[0]
    else:
        expense["id"] = None

    return expense


def updateExpense(oldExpense, formData, userID):
    expense = {"description": None, "category": None, "date": None, "amount": None, "payer": None}
    expense["description"] = formData.get("description").strip()
    expense["category"] = formData.get("category").strip()
    expense["date"] = formData.get("date").strip()
    expense["amount"] = formData.get("amount").strip()

    # Convert the amount from string to float for the DB
    expense["amount"] = float(expense["amount"])

    # Make sure the user actually is submitting changes and not saving the existing expense again
    hasChanges = False
    for key, value in oldExpense.items():
        # Exit the loop when reaching submitTime since that is not something the user provides in the form for a new expense
        if key == "submitTime":
            break
        else:
            if oldExpense[key] != expense[key]:
                hasChanges = True
                break
    if hasChanges is False:
        return None

    # Update the existing record
    now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    result = db.execute(
        "UPDATE expenses SET description = :newDescription, category = :newCategory, expenseDate = :newDate, amount = :newAmount, submitTime = :newSubmitTime WHERE id = :existingExpenseID AND user_id = :usersID",
        {
            "newDescription": expense["description"],
            "newCategory": expense["category"],
            "newDate": expense["date"],
            "newAmount": expense["amount"],
            "newSubmitTime": now,
            "existingExpenseID": oldExpense["id"],
            "usersID": userID,
        },
    ).rowcount
    db.commit()

    # Make sure result is not empty (indicating it could not update the expense)
    if result:
        # Add dictionary to list (to comply with design/standard of expensed.html)
        expenses = []
        expenses.append(expense)
        return expenses
    else:
        return None


def generateMonthlyReport(userID, year=None):

    # Default to getting current years reports
    if not year:
        year = datetime.now().year

    # Create data structure to hold users monthly spending data for the chart (monthly summed data)
    spending_month_chart = getMonthlySpending(userID, year)

    # Get the spending data from DB for the table (individual expenses per month)
    results = db.execute(
        "SELECT description, category, expensedate, amount FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = :year ORDER BY id ASC",
        {"usersID": userID, "year": year},
    ).fetchall()
    spending_month_table = convertSQLToDict(results)

    # Combine both data points (chart and table) into a single data structure
    monthlyReport = {"chart": spending_month_chart, "table": spending_month_table}

    return monthlyReport


def getMonthlySpending(userID, year=None):
    spending_month = []
    month = {"name": None, "amount": None}

    # Default to getting current years spending
    if not year:
        year = datetime.now().year

    results = db.execute(
        "SELECT date_part('month', date(expensedate)) AS month, SUM(amount) AS amount FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = :year GROUP BY date_part('month', date(expensedate)) ORDER BY month",
        {"usersID": userID, "year": year},
    ).fetchall()
    spending_month_query = convertSQLToDict(results)

    for record in spending_month_query:
        month["name"] = calendar.month_abbr[int(record["month"])]
        month["amount"] = record["amount"]

        spending_month.append(month.copy())

    return spending_month


# Get and return the users lifetime expense history
def getHistory(userID):
    results = db.execute(
        "SELECT description, category, expenseDate AS date, amount, submitTime FROM expenses WHERE user_id = :usersID ORDER BY id ASC",
        {"usersID": userID},
    ).fetchall()

    history = convertSQLToDict(results)

    return history