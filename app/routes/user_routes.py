from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

user_bp = Blueprint("user", __name__)


@user_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.get_user_by_username(username):
            return jsonify(message="Username already exists"), 400

        if User.get_user_by_email(email):
            return jsonify(message="Email already exists"), 400

        user = User.add_user(username, email, password)
        login_user(user)

        return redirect(url_for("main.index"))

    return render_template("register.html")


@user_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.get_user_by_username(username)

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.index"))
        else:
            return jsonify(message="Invalid username or password"), 401

    return render_template("login.html")


@user_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@user_bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@user_bp.route("/users")
@login_required
def get_all_users():
    users = User.get_all_users()
    return jsonify(users=[user.username for user in users])
