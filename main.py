from flask import Flask, render_template
from database.database import setup

app = Flask(__name__)
setup()

@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/transactions")
def transactions_page():
    return render_template("transactions.html")


@app.route("/budgets")
def budgets_page():
    return render_template("budgets.html")

@app.route("/savings")
def savings_page():
    return render_template("savings.html")

@app.route("/investments")
def investments_page():
    return render_template("investments.html")

@app.route("/categories")
def categories_page():
    return render_template("categories.html")

@app.route("/reports")
def reports_page():
    return render_template("reports.html")

if __name__ == "__main__":
    app.run(debug=True)
