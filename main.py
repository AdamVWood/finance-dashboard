from flask import Flask, render_template, request, redirect, url_for, jsonify

from app import investments
from app import budgets
from app import categories
from app import savings_goals
from app import transactions
from app import financial_report

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# Investments
# ---------------------------------------------------------------------------

@app.route("/investments")
def investments_page():
    mode = request.args.get("mode", "all")

    if mode == "all":
        rows = investments.get_all_investments()
        error = None
    else:
        kwargs = {
            "keyword": request.args.get("keyword"),
            "asset_type": request.args.get("asset_type"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
            "range_option": request.args.get("range_option"),
        }
        success, result = investments.filter_investments(mode=mode, **kwargs)
        rows, error = (result, None) if success else ([], result)

    return render_template(
        "investments.html",
        investments=rows,
        error=error,
        valid_types=investments.VALID_TYPES,
        mode=mode,
    )


@app.route("/investments/add", methods=["POST"])
def add_investment_route():
    data = request.form.to_dict()
    success, result = investments.add_investment(data)

    if not success:
        rows = investments.get_all_investments()
        return render_template(
            "investments.html",
            investments=rows,
            error=result,
            valid_types=investments.VALID_TYPES,
            mode="all",
        ), 400

    return redirect(url_for("investments_page"))


@app.route("/investments/<int:investment_id>")
def get_investment_route(investment_id):
    """JSON endpoint - useful for an edit modal or AJAX lookups."""
    inv = investments.get_investment(investment_id)
    if inv is None:
        return jsonify({"error": "Investment does not exist."}), 404
    return jsonify(inv)


@app.route("/investments/<int:investment_id>/update", methods=["POST"])
def update_investment_route(investment_id):
    """Expects form fields 'field' and 'value', e.g. field=quantity&value=10"""
    field = request.form.get("field")
    value = request.form.get("value")

    success, error = investments.update_investment_field(investment_id, field, value)

    if not success:
        rows = investments.get_all_investments()
        return render_template(
            "investments.html",
            investments=rows,
            error=[error],
            valid_types=investments.VALID_TYPES,
            mode="all",
        ), 400

    return redirect(url_for("investments_page"))


@app.route("/investments/<int:investment_id>/delete", methods=["POST"])
def delete_investment_route(investment_id):
    success, error = investments.delete_investment(investment_id)

    if not success:
        rows = investments.get_all_investments()
        return render_template(
            "investments.html",
            investments=rows,
            error=[error],
            valid_types=investments.VALID_TYPES,
            mode="all",
        ), 400

    return redirect(url_for("investments_page"))


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.route("/categories")
def categories_page():
    """?keyword=food searches by name; with no params, shows all categories."""
    keyword = request.args.get("keyword")

    if keyword:
        success, result = categories.search_categories(keyword)
        rows, error = (result, None) if success else ([], result)
    else:
        rows, error = categories.get_all_categories(), None

    return render_template("categories.html", categories=rows, error=error, keyword=keyword or "")


@app.route("/categories/add", methods=["POST"])
def add_category_route():
    name = request.form.get("name")
    success, result = categories.add_category(name)

    if not success:
        rows = categories.get_all_categories()
        return render_template("categories.html", categories=rows, error=[result], keyword=""), 400

    return redirect(url_for("categories_page"))


@app.route("/categories/<int:category_id>")
def get_category_route(category_id):
    cat = categories.get_category(category_id)
    if cat is None:
        return jsonify({"error": "Category does not exist."}), 404
    linked = categories.get_linked_transaction_count(category_id)
    cat["linked_transactions"] = linked
    return jsonify(cat)


@app.route("/categories/<int:category_id>/update", methods=["POST"])
def update_category_route(category_id):
    name = request.form.get("name")
    success, error = categories.update_category(category_id, name)

    if not success:
        rows = categories.get_all_categories()
        return render_template("categories.html", categories=rows, error=[error], keyword=""), 400

    return redirect(url_for("categories_page"))


@app.route("/categories/<int:category_id>/delete", methods=["POST"])
def delete_category_route(category_id):
    success, error = categories.delete_category(category_id)

    if not success:
        rows = categories.get_all_categories()
        return render_template("categories.html", categories=rows, error=[error], keyword=""), 400

    return redirect(url_for("categories_page"))


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------

@app.route("/budgets")
def budgets_page():
    mode = request.args.get("mode", "all")

    if mode == "all":
        rows = budgets.get_all_budgets()
        error = None
    else:
        kwargs = {
            "keyword": request.args.get("keyword"),
            "category": request.args.get("category"),
            "range_option": request.args.get("range_option"),
            "month": request.args.get("month"),
            "year": request.args.get("year"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
        }
        success, result = budgets.filter_budgets(mode=mode, **kwargs)
        rows, error = (result, None) if success else ([], result)

    return render_template("budgets.html", budgets=rows, error=error, mode=mode)


@app.route("/budgets/add", methods=["POST"])
def add_budget_route():
    data = request.form.to_dict()
    success, result = budgets.add_budget(data)

    if not success:
        rows = budgets.get_all_budgets()
        return render_template("budgets.html", budgets=rows, error=result, mode="all"), 400

    return redirect(url_for("budgets_page"))


@app.route("/budgets/<int:budget_id>")
def get_budget_route(budget_id):
    b = budgets.get_budget(budget_id)
    if b is None:
        return jsonify({"error": "Budget does not exist."}), 404
    return jsonify(b)


@app.route("/budgets/<int:budget_id>/update", methods=["POST"])
def update_budget_route(budget_id):
    field = request.form.get("field")
    value = request.form.get("value")
    value2 = request.form.get("value2")

    success, error = budgets.update_budget_field(budget_id, field, value, value2)

    if not success:
        rows = budgets.get_all_budgets()
        return render_template("budgets.html", budgets=rows, error=[error], mode="all"), 400

    return redirect(url_for("budgets_page"))


@app.route("/budgets/<int:budget_id>/delete", methods=["POST"])
def delete_budget_route(budget_id):
    success, error = budgets.delete_budget(budget_id)

    if not success:
        rows = budgets.get_all_budgets()
        return render_template("budgets.html", budgets=rows, error=[error], mode="all"), 400

    return redirect(url_for("budgets_page"))


@app.route("/budgets/dashboard")
def budget_dashboard_route():
    """JSON view of the budget dashboard (spend vs budget per category)."""
    return jsonify(budgets.budget_dashboard())


@app.route("/budgets/summary")
def budget_summary_route():
    """JSON view of the quick budget summary."""
    return jsonify(budgets.budget_summary())


# ---------------------------------------------------------------------------
# Savings Goals
# ---------------------------------------------------------------------------

@app.route("/savings")
def savings_page():
    mode = request.args.get("mode", "all")

    if mode == "all":
        rows = savings_goals.get_all_savings_goals()
        error = None
    else:
        kwargs = {
            "keyword": request.args.get("keyword"),
            "range_option": request.args.get("range_option"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
        }
        success, result = savings_goals.filter_savings_goals(mode=mode, **kwargs)
        rows, error = (result, None) if success else ([], result)

    return render_template("savings.html", goals=rows, error=error, mode=mode)


@app.route("/savings/add", methods=["POST"])
def add_savings_goal_route():
    data = request.form.to_dict()
    success, result = savings_goals.add_savings_goal(data)

    if not success:
        rows = savings_goals.get_all_savings_goals()
        return render_template("savings.html", goals=rows, error=result, mode="all"), 400

    return redirect(url_for("savings_page"))


@app.route("/savings/<int:goal_id>")
def get_savings_goal_route(goal_id):
    goal = savings_goals.get_savings_goal(goal_id)
    if goal is None:
        return jsonify({"error": "Savings goal does not exist."}), 404
    return jsonify(goal)


@app.route("/savings/<int:goal_id>/update", methods=["POST"])
def update_savings_goal_route(goal_id):
    field = request.form.get("field")
    value = request.form.get("value")

    success, error = savings_goals.update_savings_goal_field(goal_id, field, value)

    if not success:
        rows = savings_goals.get_all_savings_goals()
        return render_template("savings.html", goals=rows, error=[error], mode="all"), 400

    return redirect(url_for("savings_page"))


@app.route("/savings/<int:goal_id>/add-money", methods=["POST"])
def add_money_route(goal_id):
    amount = request.form.get("amount")
    success, result = savings_goals.add_money_to_goal(goal_id, amount)

    if not success:
        rows = savings_goals.get_all_savings_goals()
        return render_template("savings.html", goals=rows, error=[result], mode="all"), 400

    return redirect(url_for("savings_page"))


@app.route("/savings/<int:goal_id>/delete", methods=["POST"])
def delete_savings_goal_route(goal_id):
    success, error = savings_goals.delete_savings_goal(goal_id)

    if not success:
        rows = savings_goals.get_all_savings_goals()
        return render_template("savings.html", goals=rows, error=[error], mode="all"), 400

    return redirect(url_for("savings_page"))


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.route("/transactions", methods=["GET", "POST"])
def transactions_page():
    if request.method == "POST":
        data = request.form.to_dict()
        success, result = transactions.add_transaction(data)
        if not success:
            rows = transactions.get_all_transactions()
            return render_template("transactions.html", transactions=rows, error=result), 400
        return redirect(url_for("transactions_page"))

    mode = request.args.get("mode", "all")

    if mode == "all":
        rows = transactions.get_all_transactions()
        error = None
    else:
        kwargs = {
            "keyword": request.args.get("keyword"),
            "category": request.args.get("category"),
            "transaction_type": request.args.get("transaction_type"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
            "range_option": request.args.get("range_option"),
        }
        success, result = transactions.filter_transactions(mode=mode, **kwargs)
        rows, error = (result, None) if success else ([], result)

    return render_template("transactions.html", transactions=rows, error=error, mode=mode)


@app.route("/transactions/<int:transaction_id>")
def get_transaction_route(transaction_id):
    t = transactions.get_transaction(transaction_id)
    if t is None:
        return jsonify({"error": "Transaction does not exist."}), 404
    return jsonify(t)


@app.route("/transactions/<int:transaction_id>/update", methods=["POST"])
def update_transaction_route(transaction_id):
    field = request.form.get("field")
    value = request.form.get("value")

    success, error = transactions.update_transaction_field(transaction_id, field, value)

    if not success:
        rows = transactions.get_all_transactions()
        return render_template("transactions.html", transactions=rows, error=[error]), 400

    return redirect(url_for("transactions_page"))


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
def delete_transaction_route(transaction_id):
    success, error = transactions.delete_transaction(transaction_id)

    if not success:
        rows = transactions.get_all_transactions()
        return render_template("transactions.html", transactions=rows, error=[error]), 400

    return redirect(url_for("transactions_page"))


# ---------------------------------------------------------------------------
# Financial Reports
# ---------------------------------------------------------------------------

@app.route("/reports")
def reports_page():
    report_type = request.args.get("type")
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    error = None
    data = None

    if report_type == "income_expenses":
        data = financial_report.report_income_expenses()
    elif report_type == "spending_by_category":
        data = financial_report.report_spending_by_category()
    elif report_type == "budget_vs_actual":
        if month and year:
            data = financial_report.report_budget_vs_actual(month, year)
        else:
            error = "Month and year are required for this report."
    elif report_type == "savings_goals":
        data = financial_report.report_savings_goals()
    elif report_type == "investments":
        data = financial_report.report_investments()
    elif report_type == "portfolio_overview":
        data = financial_report.report_portfolio_overview()
    elif report_type == "budget_dashboard":
        if month and year:
            data = financial_report.report_budget_dashboard(month, year)
        else:
            error = "Month and year are required for this report."
    elif report_type == "savings_goals_insights":
        data = financial_report.report_savings_goals_insights()
    elif report_type == "monthly_income_expenses":
        if year:
            data = financial_report.report_monthly_income_expenses(year)
        else:
            error = "Year is required for this report."

    return render_template(
        "reports.html",
        report_type=report_type,
        data=data,
        error=error,
        month=month,
        year=year,
    )


if __name__ == "__main__":
    app.run(debug=True)