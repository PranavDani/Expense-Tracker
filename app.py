from flask import Flask, render_template
from sqlalchemy import create_engine

# from models import db
from sqlalchemy.orm import scoped_session, sessionmaker

from flask import Flask, jsonify

# from flask_cors import CORS
from dotenv import load_dotenv
import psycopg2
import os

load_dotenv()

# PostgreSQL Database credentials loaded from the .env file
DATABASE = os.getenv("DATABASE")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")


app = Flask(__name__)

# engine = create_engine("postgresql://postgres:160402@localhost:5432/track")

# db = scoped_session(sessionmaker(bind=engine))

try:
    con = psycopg2.connect(database=DATABASE, user=DATABASE_USERNAME, password=DATABASE_PASSWORD)

    db = con.cursor()

    # # GET: Fetch all movies from the database
    # @app.route("/")
    # def fetch_all_movies():
    #     db.execute("SELECT * FROM usercategories")
    #     rows = db.fetchall()
    #     print(rows)

    #     return jsonify(rows)


except:
    print("Error")


@app.route("/")
def hello_world():
    return "Hello, World!"


if __name__ == "__main__":
    app.run(debug=True)
