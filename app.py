import requests
import psycopg2
import os
import e_expenses
import e_categories
import e_account

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
        expenses_year = None
        expenses_month = None
        expenses_week = None
        # Get the users spend categories (for quick expense modal)
        categories = e_categories.getSpendCategories(session["user_id"])

        income = e_expenses.getIncome(session["user_id"])

        expenses_year = e_expenses.getTotalSpend_Year(session["user_id"])

        # Get current months total expenses for the user
        expenses_month = e_expenses.getTotalSpend_Month(session["user_id"])

        # Get current week total expenses for the user
        expenses_week = e_expenses.getTotalSpend_Week(session["user_id"])

        expenses_last5 = e_expenses.getLastFiveExpenses(session["user_id"])

        # Get todays date (for quick expense modal)
        date = datetime.today().strftime("%Y-%m-%d")

        return render_template(
            "index.html",
            categories=categories,
            date=date,
            income=income,
            expenses_year=expenses_year,
            expenses_month=expenses_month,
            expenses_week=expenses_week,
            expenses_last5=expenses_last5,
        )

    # Post Method for the modal
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


@app.route("/expensehistory", methods=["GET", "POST"])
@login_required
def expensehistory():
    if request.method == "GET":
        history = e_expenses.getHistory(session["user_id"])
        categories = e_categories.getSpendCategories(session["user_id"])
        return render_template("expensehistory.html", history=history, categories=categories, isDeleteAlert=False)

    else:
        userHasSelected_deleteExpense = False
        if "btnDeleteConfirm" in request.form:
            userHasSelected_deleteExpense = True
        elif "btnSave" in request.form:
            userHasSelected_deleteExpense = False
        else:
            return apology("Bro, idk what's happening")

        oldExpense = e_expenses.getExpense(request.form, session["user_id"])

        if oldExpense["id"] == None:
            return apology("The expense record you're trying to update doesn't exist")

        if userHasSelected_deleteExpense == True:
            deleted = e_expenses.deleteExpense(oldExpense, session["user_id"])
            if not deleted:
                return apology("This expense was not able to be deleted")

            history = e_expenses.getHistory(session["user_id"])
            categories = e_categories.getSpendCategories(session["user_id"])
            return render_template("expensehistory.html", history=history, categories=categories, isDeleteAlert=True)

        else:
            expensed = e_expenses.updateExpense(oldExpense, request.form, session["user_id"])
            if not expensed:
                return apology("The expense was unable to be updated")

            # Redirect to results page and render a summary of the updated expense
            return render_template("expensed.html", results=expensed)


@app.route("/account", methods=["GET", "POST"])
@login_required
def updateaccount():
    if request.method == "POST":
        # Initialize user's actions
        userHasSelected_updateIncome = False
        userHasSelected_updatePassword = False

        # Initialize user alerts
        alert_updateIncome = None
        alert_updatePassword = None

        # Determine what action was selected by the user (button/form trick from: https://stackoverflow.com/questions/26217779/how-to-get-the-name-of-a-submitted-form-in-flask)
        if "btnUpdateIncome" in request.form:
            userHasSelected_updateIncome = True
        elif "btnUpdatePassword" in request.form:
            userHasSelected_updatePassword = True
        else:
            return apology("Doh! Your Account is drunk. Try again!")

        if userHasSelected_updateIncome:
            newIncome = float(request.form.get("income").strip())
            updatedIncome = e_account.updateIncome(newIncome, session["user_id"])
            if updatedIncome != 1:
                return apology(updatedIncome["apology"])
            alert_updateIncome = newIncome

        if userHasSelected_updatePassword:
            # Try updating the users password
            updatedPassword = e_account.updatePassword(
                request.form.get("currentPassword"), request.form.get("newPassword"), session["user_id"]
            )
            # Render error message if the password could not be updated
            if updatedPassword != 1:
                return apology(updatedPassword["apology"])
            # Set the alert message for user
            alert_updatePassword = True

        user = e_account.getAllUserInfo(session["user_id"])
        return render_template(
            "account.html",
            username=user["name"],
            income=user["income"],
            newIncome=alert_updateIncome,
            updatedPassword=alert_updatePassword,
        )

    # GET method
    else:
        user = e_account.getAllUserInfo(session["user_id"])

        return render_template(
            "account.html",
            username=user["name"],
            income=user["income"],
            newIncome=None,
            updatedPassword=None,
        )


@app.route("/reports", methods=["GET"])
@login_required
def reports():
    """View reports"""

    return render_template("reports.html")


@app.route("/monthlyreport", methods=["GET"])
@app.route("/monthlyreport/<int:year>", methods=["GET"])
@login_required
def monthlyreport(year=None):
    """View monthly spending report"""

    # Make sure the year from route is valid
    if year:
        currentYear = datetime.now().year
        if not 2021 <= year <= currentYear:
            return apology(f"Please select a valid budget year: 2021 through {currentYear}")
    else:
        year = datetime.now().year

    # Generate a data structure that combines the users monthly spending data needed for chart and table
    monthlySpending = e_expenses.generateMonthlyReport(session["user_id"], year)

    return render_template("monthlyreport.html", monthlySpending=monthlySpending, year=year)


@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    if request.method == "GET":
        income = e_account.getIncome(session["user_id"])
        # Get the users current budgets
        budgets = e_expenses.getBudgets(session["user_id"])
        budgeted = e_expenses.getTotalBudgeted(session["user_id"])
        user = session["user_id"]

        return render_template(
            "budgets.html", income=income, budgets=budgets, user=user, budgeted=budgeted, deletedBudgetName=None
        )

    else:
        budgetName = request.form.get("delete").strip()
        deletedBudgetName = e_expenses.deleteBudget(budgetName, session["user_id"])

        # Render the budgets page with a success message, otherwise throw an error/apology
        if deletedBudgetName:
            # Get the users income, current budgets, and sum their budgeted amount unless they don't have any budgets (same steps as a GET for this route)
            income = e_expenses.getIncome(session["user_id"])
            budgets = e_expenses.getBudgets(session["user_id"])
            budgeted = e_expenses.getTotalBudgeted(session["user_id"])
            user = session["user_id"]

            return render_template(
                "budgets.html",
                income=income,
                budgets=budgets,
                user=user,
                budgeted=budgeted,
                deletedBudgetName=deletedBudgetName,
            )
        else:
            return apology("Uh oh! Your budget could not be deleted. ✂")


@app.route("/createbudget", methods=["GET", "POST"])
@login_required
def createbudget():
    if request.method == "GET":
        income = e_account.getIncome(session["user_id"])
        budgeted = e_expenses.getTotalBudgeted(session["user_id"])
        categories = e_categories.getSpendCategories(session["user_id"])

        return render_template("createbudget.html", income=income, budgeted=budgeted, categories=categories)

    else:
        budgets = e_expenses.getBudgets(session["user_id"])
        user = session["user_id"]
        if budgets:
            budgetCount = 0
            for amount in budgets:
                budgetCount += len(budgets[user])
            if budgetCount >= 20:
                return apology("You've reached the max amount of budgets'")

        formData = list(request.form.items())
        # Generate data structure to hold budget info from form
        budgetDict = e_expenses.generateBudgetFromForm(formData)

        # Render error message if budget name or categories contained invalid data
        if "apology" in budgetDict:
            return apology(budgetDict["apology"])
        else:
            # Add budget to DB for user
            budget = e_expenses.createBudget(budgetDict, session["user_id"])
            # Render error message if budget name is a duplicate of another budget the user has
            if "apology" in budget:
                return apology(budget["apology"])
            else:
                return render_template("budgetcreated.html", results=budget)


@app.route("/updatebudget/<urlvar_budgetname>", methods=["GET", "POST"])
@login_required
def updatebudget(urlvar_budgetname):
    """Update budget"""

    if request.method == "GET":
        budgetID = e_expenses.getBudgetID(urlvar_budgetname, session["user_id"])
        if budgetID is None:
            return apology("'" + urlvar_budgetname + "' budget does not exist")
        else:
            budget = e_expenses.getBudgetByID(budgetID, session["user_id"])

        income = e_account.getIncome(session["user_id"])
        budgeted = e_expenses.getTotalBudgetedAmount(session["user_id"])
        budget = e_expenses.getUpdatableBudget(budget, session["user_id"])
        print(budget)
        return render_template("updatebudget.html", income=income, budgeted=budgeted, budget=budget)

    else:
        formData = list(request.form.items())
        budgetDict = e_expenses.generateBudgetFromForm(formData)
        if "apology" in budgetDict:
            return apology(budgetDict["apology"])
        else:
            budget = e_expenses.updateBudget(urlvar_budgetname, budgetDict, session["user_id"])
            if "apology" in budget:
                return apology(budget["apology"])
            else:
                return render_template("budgetcreated.html", results=budget)


if __name__ == "__main__":
    app.run(debug=True)