from flask import Flask, render_template, request, redirect, url_for
from app.transactions import add_transaction, filter_transactions, search_transaction, update_transaction, delete_transaction

app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/transactions", methods=["GET", "POST"])
def transactions_page():
    if request.method == "POST":
        try:
            add_transaction(
                float(request.form["amount"]),
                request.form["transaction_type"],
                int(request.form["category_id"]),
                request.form["description"],
                request.form["date"]
            )
            return redirect(url_for("transactions_page"))
        except ValueError as e:
            # Pass the error message into the template
            transactions = filter_transactions("all")
            return render_template("transactions.html", transactions=transactions, error=str(e))

    transactions = filter_transactions("all")
    return render_template("transactions.html", transactions=transactions)

@app.route("/transactions/search/<int:transaction_id>")
def search_transaction_route(transaction_id):
    transaction = search_transaction(transaction_id)
    return render_template("transaction_detail.html", transaction=transaction)

@app.route("/transactions/update/<int:transaction_id>", methods=["POST"])
def update_transaction_route(transaction_id):
    field = request.form["field"]
    new_value = request.form["new_value"]
    update_transaction(transaction_id, field, new_value)
    return redirect(url_for("transactions_page"))

@app.route("/transactions/delete/<int:transaction_id>", methods=["POST"])
def delete_transaction_route(transaction_id):
    delete_transaction(transaction_id)
    return redirect(url_for("transactions_page"))

if __name__ == "__main__":
    app.run(debug=True)
