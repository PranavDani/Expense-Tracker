import requests
import psycopg2
import re
import calendar
import os
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


def getIncome(userID):
    income = db.execute("SELECT income FROM users WHERE id = :usersID", {"usersID": userID}).fetchone()[0]

    return float(income)


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


def deleteExpense(expense, userID):
    result = db.execute(
        "delete from expenses where user_id = :usersID and id = :oldExpenseID",
        {"usersID": userID, "oldExpenseID": expense["id"]},
    )
    db.commit()
    return True


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
    if not year:
        year = datetime.now().year

    spending_month_chart = getMonthlySpending(userID, year)
    results = db.execute(
        "SELECT description, category, expensedate, amount FROM expenses WHERE user_id = :usersID AND date_part('year', date(expensedate)) = :year ORDER BY id ASC",
        {"usersID": userID, "year": year},
    ).fetchall()
    spending_month_table = convertSQLToDict(results)

    monthlyReport = {"chart": spending_month_chart, "table": spending_month_table}

    return monthlyReport


def getMonthlySpending(userID, year=None):
    spending_month = []
    month = {"name": None, "amount": None}
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


def getBudgets(userID):
    results = db.execute(
        "SELECT id, name, amount, user_id FROM budgets WHERE user_id = :usersID ORDER BY name ASC", {"usersID": userID}
    ).fetchall()

    budgets_query = convertSQLToDict(results)

    if budgets_query:
        # Create a dict with budget user_id as key and empty list as value which will store all budgets for that user_id
        budgets = {budget["user_id"]: [] for budget in budgets_query}

        # Update the dict by inserting budget info as values
        for budget in budgets_query:
            budgets[budget["user_id"]].append({"amount": budget["amount"], "id": budget["id"], "name": budget["name"]})

        return budgets
        print(budgets)
    else:
        return None


def getBudgetID(budgetName, userID):
    budgetID = db.execute(
        "SELECT id FROM budgets WHERE user_id = :usersID AND name = :budgetName",
        {"usersID": userID, "budgetName": budgetName},
    ).fetchone()[0]

    if not budgetID:
        return None
    else:
        return budgetID


def deleteBudget(budgetName, userID):
    budgetID = getBudgetID(budgetName, userID)

    if budgetID:
        db.execute("DELETE FROM budgetCategories WHERE budgets_id = :budgetID", {"budgetID": budgetID})
        db.commit()

        db.execute("DELETE FROM budgets WHERE id = :budgetID", {"budgetID": budgetID})
        db.commit()

        return budgetName
    else:
        return None


def getTotalBudgeted(userID, year=None):

    amount = db.execute(
        "SELECT SUM(amount) AS amount FROM budgets WHERE user_id = :usersID",
        {"usersID": userID},
    ).fetchone()[0]

    if amount is None:
        return 0
    else:
        return amount


def isUniqueBudgetName(budgetName, budgetID, userID):
    if budgetID == None:
        results = db.execute("SELECT name FROM budgets WHERE user_id = :usersID", {"usersID": userID}).fetchall()
        existingBudgets = convertSQLToDict(results)
    else:
        results = db.execute(
            "SELECT name FROM budgets WHERE user_id = :usersID AND NOT id = :oldBudgetID",
            {"usersID": userID, "oldBudgetID": budgetID},
        ).fetchall()
        existingBudgets = convertSQLToDict(results)

    isUniqueName = True
    for budget in existingBudgets:
        if budgetName.lower() == budget["name"].lower():
            isUniqueName = False
            break

    if isUniqueName:
        return True
    else:
        return False


def addCategory(budgetID, categoryIDS):
    for categoryID in categoryIDS:
        db.execute(
            "INSERT INTO budgetCategories (budgets_id, category_id, amount) VALUES (:budgetID, :categoryID, :percentAmount)",
            {"budgetID": budgetID, "categoryID": categoryID["id"], "percentAmount": categoryID["amount"]},
        )
    db.commit()


def getBudgetCategoryIDS(categories, userID):
    categoryIDS = []
    for category in categories:
        categoryID = db.execute(
            "SELECT categories.id FROM userCategories INNER JOIN categories ON userCategories.category_id = categories.id WHERE userCategories.user_id = :usersID AND categories.name = :categoryName",
            {"usersID": userID, "categoryName": category["name"]},
        ).fetchone()[0]

        id_amount = {"id": None, "amount": None}
        id_amount["id"] = categoryID
        id_amount["amount"] = category["percent"]

        categoryIDS.append(id_amount)

    return categoryIDS


def generateBudgetFromForm(formData):
    budget = {"name": None, "amount": None, "categories": []}
    counter = 0

    # Loop through all of the form data to extract budgets details and store in the budget dict
    for key, value in formData:
        counter += 1
        # First 3 keys represent the name/year/amount from the form, all other keys represent dynamically loaded categories from the form
        if counter <= 2:
            # Check name for invalid chars and uniqueness
            if key == "name":
                # Invalid chars are all special chars except underscores, spaces, and hyphens (uses same regex as what's on the HTML page)
                validBudgetName = re.search("^([a-zA-Z0-9_\s\-]*)$", value)
                if validBudgetName:
                    budget[key] = value.strip()
                else:
                    return {
                        "apology": "Please enter a budget name without special characters except underscores, spaces, and hyphens"
                    }
            # Convert the amount from string to float
            else:
                amount = float(value.strip())
                budget[key] = amount
        # All other keys will provide the *category* name / percent budgeted
        else:
            # Skip iteration if value is empty (empty means the user doesnt want the category in their budget)
            if value == "":
                continue

            # Need to split the key since the HTML elements are loaded dynamically and named like 'categories.1', 'categories.2', etc.
            cleanKey = key.split(".")

            # Store the category name and associated % the user wants budgetd for the category
            category = {"name": None, "percent": None}
            if cleanKey[0] == "categories":
                category["name"] = value.strip()

                # Get the percent value and convert to decimal
                percent = int(formData[counter][1].strip()) / 100
                category["percent"] = percent

                # Add the category to the list of categories within the dict
                budget[cleanKey[0]].append(category)
            # Pass on this field because we grab the percent above (Why? It's easier to keep these 2 lines than rewrite many lines. This is the lowest of low pri TODOs)
            elif cleanKey[0] == "categoryPercent":
                pass
            else:
                return {
                    "apology": "Only categories and their percentage of the overall budget are allowed to be stored"
                }

    return budget


def createBudget(budget, userID):
    # Verify the budget name is not a duplicate of an existing budget
    uniqueBudgetName = isUniqueBudgetName(budget["name"], None, userID)
    if not uniqueBudgetName:
        return {"apology": "Please enter a unique budget name, not a duplicate."}

    # Insert new budget into DB
    newBudgetID = db.execute(
        "INSERT INTO budgets (name, amount, user_id) VALUES (:budgetName, :budgetAmount, :usersID) RETURNING id",
        {
            "budgetName": budget["name"],
            "budgetAmount": budget["amount"],
            "usersID": userID,
        },
    ).fetchone()[0]
    db.commit()

    # Get category IDs from DB for the new budget
    categoryIDS = getBudgetCategoryIDS(budget["categories"], userID)

    # Insert a record for each category in the new budget
    addCategory(newBudgetID, categoryIDS)

    return budget


def deleteBudget(budgetName, userID):
    budgetID = getBudgetID(budgetName, userID)

    if budgetID:
        db.execute("DELETE FROM budgetCategories WHERE budgets_id = :budgetID", {"budgetID": budgetID})
        db.commit()

        db.execute("DELETE FROM budgets WHERE id = :budgetID", {"budgetID": budgetID})
        db.commit()

        return budgetName
    else:
        return None


def getBudgetByID(budgetID, userID):
    results = db.execute(
        "SELECT name, amount, id FROM budgets WHERE user_id = :usersID AND id = :budgetID",
        {"usersID": userID, "budgetID": budgetID},
    ).fetchall()

    budget = convertSQLToDict(results)

    return budget[0]


def getTotalBudgetedAmount(userID):

    amount = db.execute(
        "SELECT SUM(amount) AS amount FROM budgets WHERE user_id = :usersID", {"usersID": userID}
    ).fetchone()[0]

    if amount is None:
        return 0
    else:
        return amount


def getUpdatableBudget(budget, userID):

    categories = e_categories.getSpendCategories(userID)

    # Get the budget's spend categories and % amount for each category
    results = db.execute(
        "SELECT DISTINCT categories.name, budgetCategories.amount FROM budgetCategories INNER JOIN categories ON budgetCategories.category_id = categories.id INNER JOIN budgets ON budgetCategories.budgets_id = budgets.id WHERE budgets.id = :budgetsID",
        {"budgetsID": budget["id"]},
    ).fetchall()
    budgetCategories = convertSQLToDict(results)

    # Add 'categories' as a new key/value pair to the existing budget dict
    budget["categories"] = []

    for category in categories:
        for budgetCategory in budgetCategories:
            # Mark the category as checked/True if it exists in the budget that the user wants to update
            if category["name"] == budgetCategory["name"]:
                amount = round(budgetCategory["amount"] * 100)
                budget["categories"].append({"name": category["name"], "amount": amount, "checked": True})
                break
        else:
            budget["categories"].append({"name": category["name"], "amount": None, "checked": False})

    return budget


def updateBudget(oldBudgetName, budget, userID):
    oldBudgetID = getBudgetID(oldBudgetName, userID)

    uniqueBudgetName = isUniqueBudgetName(budget["name"], oldBudgetID, userID)
    if not uniqueBudgetName:
        return {"apology": "Please enter a unique budget name, not a duplicate."}

    db.execute(
        "UPDATE budgets SET name = :budgetName, amount = :budgetAmount WHERE id = :oldBudgetID AND user_id = :usersID",
        {
            "budgetName": budget["name"],
            "budgetAmount": budget["amount"],
            "oldBudgetID": oldBudgetID,
            "usersID": userID,
        },
    )
    db.commit()

    db.execute("DELETE FROM budgetCategories WHERE budgets_id = :oldBudgetID", {"oldBudgetID": oldBudgetID})
    db.commit()

    categoryIDS = getBudgetCategoryIDS(budget["categories"], userID)
    addCategory(oldBudgetID, categoryIDS)

    return budget


def getHistory(userID):
    results = db.execute(
        "SELECT description, category, expenseDate AS date, amount, submitTime FROM expenses WHERE user_id = :usersID ORDER BY id ASC",
        {"usersID": userID},
    ).fetchall()

    history = convertSQLToDict(results)

    return history