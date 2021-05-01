# Expense-Tracker

## Run it locally (written for Windows and VSCode)

1. Create a directory and clone the repo in it:

```
git clone https://github.com/Pranav1642/Expense-Tracker.git
```

2. Create your virtual environment:

```
python -m venv env
```

3. Activate your virtual environment:

```
env\Scripts\activate
```

4. Install the dependencies:

```
pip install -r requirements.txt
```

5. Create the DB in Postgres (Download it first) (schema in repo [here](./Postgress-database.txt))

6. Set your environment variables in .env file (otherwise hard code (not a good practice) the string `engine` in app.py in all of the `.py` files):

```
# DB variable
DATABASE_LINK=postgres://{user}:{password}@{hostname}:{port}/{database-name}
```

7. Build and run the Flask app in VSCode
