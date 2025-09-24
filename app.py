import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

from models import db, Search
from reddit_service import (
    get_account_details,
    get_top_30_captions,
    get_top_20_hot,
    get_top_20_all_time,
)


load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/history")
    def history():
        searches = (
            Search.query.order_by(Search.created_at.desc())
            .limit(100)
            .all()
        )
        return render_template("history.html", searches=searches)

    @app.get("/user/details")
    def user_details_form():
        return render_template("user_details.html")

    @app.post("/user/details")
    def user_details_submit():
        username = (request.form.get("username") or "").strip()
        period_days_raw = (request.form.get("period_days") or "").strip()
        try:
            period_days = int(period_days_raw) if period_days_raw else 1
        except ValueError:
            period_days = 1

        if not username:
            flash("Username is required.", "error")
            return redirect(url_for("user_details_form"))

        try:
            result = get_account_details(username=username, period_days=period_days)
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("user_details_form"))

        search = Search(
            search_type="user_details",
            username=username,
            period_days=period_days,
            results_json=result,
            created_at=datetime.utcnow(),
        )
        db.session.add(search)
        db.session.commit()
        return redirect(url_for("view_results", search_id=search.id))

    @app.get("/user/top")
    def user_top_form():
        return render_template("user_top.html")

    @app.post("/user/top")
    def user_top_submit():
        username = (request.form.get("username") or "").strip()
        keywords = (request.form.get("keywords") or "").strip()
        limit_raw = (request.form.get("limit") or "").strip()
        captions_only = request.form.get("captions_only") == "on"
        try:
            limit = int(limit_raw) if limit_raw else 30
        except ValueError:
            limit = 30

        if not username:
            flash("Username is required.", "error")
            return redirect(url_for("user_top_form"))

        try:
            result = get_top_30_captions(
                username=username,
                keywords=keywords,
                limit=limit,
                captions_only=captions_only,
            )
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("user_top_form"))

        search = Search(
            search_type="user_top",
            username=username,
            keywords=keywords,
            limit_value=limit,
            captions_only=captions_only,
            results_json=result,
            created_at=datetime.utcnow(),
        )
        db.session.add(search)
        db.session.commit()
        return redirect(url_for("view_results", search_id=search.id))

    @app.get("/subreddit/hot")
    def subreddit_hot_form():
        return render_template("subreddit_hot.html")

    @app.post("/subreddit/hot")
    def subreddit_hot_submit():
        subreddit = (request.form.get("subreddit") or "").strip()
        keywords = (request.form.get("keywords") or "").strip()
        limit_raw = (request.form.get("limit") or "").strip()
        captions_only = request.form.get("captions_only") == "on"
        try:
            limit = int(limit_raw) if limit_raw else 20
        except ValueError:
            limit = 20

        if not subreddit:
            flash("Subreddit is required.", "error")
            return redirect(url_for("subreddit_hot_form"))

        try:
            result = get_top_20_hot(
                subreddit_name=subreddit,
                keywords=keywords,
                limit=limit,
                captions_only=captions_only,
            )
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("subreddit_hot_form"))

        search = Search(
            search_type="subreddit_hot",
            subreddit=subreddit,
            keywords=keywords,
            limit_value=limit,
            captions_only=captions_only,
            results_json=result,
            created_at=datetime.utcnow(),
        )
        db.session.add(search)
        db.session.commit()
        return redirect(url_for("view_results", search_id=search.id))

    @app.get("/subreddit/top")
    def subreddit_top_form():
        return render_template("subreddit_top.html")

    @app.post("/subreddit/top")
    def subreddit_top_submit():
        subreddit = (request.form.get("subreddit") or "").strip()
        keywords = (request.form.get("keywords") or "").strip()
        limit_raw = (request.form.get("limit") or "").strip()
        captions_only = request.form.get("captions_only") == "on"
        try:
            limit = int(limit_raw) if limit_raw else 20
        except ValueError:
            limit = 20

        if not subreddit:
            flash("Subreddit is required.", "error")
            return redirect(url_for("subreddit_top_form"))

        try:
            result = get_top_20_all_time(
                subreddit_name=subreddit,
                keywords=keywords,
                limit=limit,
                captions_only=captions_only,
            )
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("subreddit_top_form"))

        search = Search(
            search_type="subreddit_top",
            subreddit=subreddit,
            keywords=keywords,
            limit_value=limit,
            captions_only=captions_only,
            results_json=result,
            created_at=datetime.utcnow(),
        )
        db.session.add(search)
        db.session.commit()
        return redirect(url_for("view_results", search_id=search.id))

    @app.get("/results/<int:search_id>")
    def view_results(search_id: int):
        search = Search.query.get_or_404(search_id)
        return render_template("results.html", search=search)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)



