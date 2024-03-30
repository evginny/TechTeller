from flask import (
    Flask,
    jsonify,
    Response,
    render_template,
    redirect,
    session,
    url_for,
    request,
)
from os import environ as env
from urllib.parse import quote_plus, urlencode
import sqlite3
import json
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from math import ceil

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"


@app.after_request
def apply_csp(response):
    """
    Applies Content Security Policy (CSP) headers to all responses.

    Args:
        response: The response object to which the CSP headers will be added.

    Returns:
        The modified response object with CSP headers.
    """
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com; "
        "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' https://lh3.googleusercontent.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "report-uri /report-csp-violation;"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-XSS-Protection"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers[
        "Strict-Transport-Security"
    ] = "max-age=63072000; includeSubDomains"
    return response


db = SQLAlchemy(app)
migrate = Migrate(app, db)

likes_table = db.Table(
    "likes",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("news_id", db.Integer, db.ForeignKey("news.id"), primary_key=True),
)

dislikes_table = db.Table(
    "dislikes",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("news_id", db.Integer, db.ForeignKey("news.id"), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    given_name = db.Column(db.String(100))
    family_name = db.Column(db.String(100))
    nickname = db.Column(db.String(100))
    name = db.Column(db.String(100))
    picture = db.Column(db.String(20), nullable=False, default="default.jpg")
    email = db.Column(db.String(100), unique=True, nullable=False)
    email_verified = db.Column(db.Boolean)
    isAdmin = db.Column(db.Boolean, default=False)
    liked_news = db.relationship(
        "News",
        secondary=likes_table,
        backref=db.backref("liked_by", lazy="dynamic"),
        cascade="all, delete",
    )
    disliked_news = db.relationship(
        "News",
        secondary=dislikes_table,
        backref=db.backref("disliked_by", lazy="dynamic"),
        cascade="all, delete",
    )

    def __repr__(self):
        return f"User('{self.name}', '{self.email}', '{self.picture}')"


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    by = db.Column(db.String(200))
    time = db.Column(db.Integer)
    title = db.Column(db.String(200))
    url = db.Column(db.String(200))
    like_count = db.Column(db.Integer, default=0)
    dislike_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<News {self.title}>"


with app.app_context():
    db.create_all()

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


def check_if_admin(user):
    """
    Checks if the given user is an admin based on predefined criteria.

    Args:
        user: A User object representing the user to be checked.

    Returns:
        A boolean value indicating whether the user is an admin.
    """
    admin_keywords = ["kumar", "piyush", "chashi", "hansong", "zhou"]
    user_name = user.name.lower()
    user_email = user.email.lower()

    # Check if any keyword is in the user's name or email
    for keyword in admin_keywords:
        if keyword in user_name or keyword in user_email:
            return True

    # Specific check for 'Jane Kalshnikova'
    if "jane.kalashn@gmail.com" == user_email:
        return True

    return False


# Controllers API
@app.route("/")
def home():
    """
    Renders the home page of the application.

    Returns:
        A rendered template for the home page.
    """
    return render_template(
        "home.html",
        session=session.get("user"),
        pretty=json.dumps(session.get("user"), indent=4),
    )


@app.route("/callback", methods=["GET", "POST"])
def callback():
    """
    Handles the OAuth callback after a user logs in via Auth0.

    Returns:
        A redirect to the 'mynews' page after successful login and user session setup.
    """
    token = oauth.auth0.authorize_access_token()
    session["user"] = token

    # Make sure to include the full URL to the userinfo endpoint
    userinfo_response = oauth.auth0.get(
        "https://{}/userinfo".format(env.get("AUTH0_DOMAIN"))
    )
    userinfo = userinfo_response.json()

    existing_user = User.query.filter_by(email=userinfo["email"]).first()

    # If the user doesn't exist in your database, create a new user instance
    if existing_user is None:
        new_user = User(
            given_name=userinfo.get("given_name", ""),
            family_name=userinfo.get("family_name", ""),
            nickname=userinfo.get("nickname", ""),
            name=userinfo.get("name", ""),
            picture=userinfo.get("picture", ""),
            email=userinfo.get("email", ""),
            email_verified=userinfo.get("email_verified", False),
        )

        # Check if the new user is an admin
        new_user.isAdmin = check_if_admin(new_user)

        # Add the new user to the database session and commit it
        db.session.add(new_user)
        try:
            db.session.commit()
            # User added to database
        except Exception as e:
            db.session.rollback()
            print(e)
    else:
        # Update admin status for existing users
        existing_user.isAdmin = check_if_admin(existing_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)

    # Store the user information in flask session.
    session["jwt_payload"] = userinfo
    session["profile"] = {
        "name": userinfo["name"],
        "picture": userinfo["picture"],
        "email": userinfo["email"],
        "nickname": userinfo["nickname"],
    }

    return redirect("/mynews")


@app.route("/login")
def login():
    """
    Initiates the login process using Auth0.

    Returns:
        A redirect to the Auth0 login page.
    """
    full_redirect_uri = url_for("callback", _external=True)
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/logout")
def logout():
    """
    Logs out the current user and clears the session.

    Returns:
        A redirect to the home page after logging out.
    """
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


@app.route("/newsfeed", methods=["GET"])
def get_news():
    """
    Fetches and displays the latest news items from the database.

    Returns:
        A JSON response containing the latest news items.
    """
    conn = sqlite3.connect("hackernews.db")
    c = conn.cursor()
    c.execute("SELECT * FROM news ORDER BY time DESC LIMIT 10")
    news = c.fetchall()
    conn.close()

    news_items = []
    for item in news:
        news_dict = {
            "id": item[0],
            "by": item[1],
            "descendants": item[2],
            "kids": eval(item[3]) if item[3] else [],
            "score": item[4],
            "text": item[5],
            "time": item[6],
            "title": item[7],
            "type": item[8],
            "url": item[9],
        }
        news_items.append(news_dict)

    # Convert the Python dictionary to a JSON string with indentation
    json_str = json.dumps({"news_items": news_items}, indent=4)

    # Return the formatted JSON string as a response
    return Response(json_str, content_type="application/json")


@app.route("/profile")
def profile():
    """
    Renders the profile page for the logged-in user.

    Returns:
        A rendered template for the user's profile page or a redirect to the home page if not logged in.
    """
    # Check if user information is stored in the session
    if "profile" in session:
        # Retrieve user information from session
        user_info = session["profile"]
        # Use default picture if none is provided
        picture = user_info.get(
            "picture", url_for("static", filename="profile_pics/default.jpg")
        )
        # Render the profile page with user information
        return render_template(
            "profile.html", title="Profile", user_info=user_info, picture=picture
        )
    else:
        # If no user is logged in, redirect to home page
        return redirect(url_for("home"))


@app.route("/mynews")
def mynews():
    """
    Displays a personalized news feed for the logged-in user.

    Returns:
        A rendered template for the user's news feed or a redirect to the login page if not logged in.
    """
    # Define the number of items per page
    per_page = 10

    # Get the page number from the query parameters, default to 1 if not set
    page = request.args.get("page", 1, type=int)

    # Get the sort parameter from the query, default to 'newest'
    sort_by = request.args.get("sort", "newest")

    if sort_by == "popularity":
        news_items = (
            News.query.order_by(
                (News.like_count - News.dislike_count).desc(), News.time.desc()
            )
            .paginate(page=page, per_page=per_page, error_out=False)
            .items
        )
    else:  # Default to newest
        news_items = (
            News.query.order_by(News.time.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
            .items
        )

    # Calculate total number of pages needed
    total_count = News.query.count()
    total_pages = ceil(total_count / per_page)

    if "profile" in session:
        user_email = session["profile"]["email"]
        user = User.query.filter_by(email=user_email).first()
        liked_news_ids = [news.id for news in user.liked_news]
        disliked_news_ids = [news.id for news in user.disliked_news]
        is_admin = user.isAdmin if user else False
    else:
        liked_news_ids = []
        disliked_news_ids = []
        is_admin = False

    # Render the mynews template, passing in the news items and page info
    return render_template(
        "mynews.html",
        news_items=news_items,
        page=page,
        total_pages=total_pages,
        liked_news_ids=liked_news_ids,
        disliked_news_ids=disliked_news_ids,
        sort_by=sort_by,
        is_admin=is_admin,
    )


@app.route("/like_news/<int:news_id>", methods=["POST"])
def like_news(news_id):
    """
    Handles the liking of a news item by the logged-in user.

    Args:
        news_id: An integer representing the ID of the news item to be liked.

    Returns:
        A JSON response indicating the result of the like operation.
    """
    if "profile" not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_email = session["profile"]["email"]
    user = User.query.filter_by(email=user_email).first()
    news_item = News.query.get_or_404(news_id)

    if news_item in user.liked_news:
        user.liked_news.remove(news_item)
        news_item.like_count -= 1
        action = "unliked"
    elif news_item in user.disliked_news:
        user.disliked_news.remove(news_item)
        user.liked_news.append(news_item)
        news_item.like_count += 1
        news_item.dislike_count -= 1
        action = "switched_to_like"
    else:
        user.liked_news.append(news_item)
        news_item.like_count += 1
        action = "liked"
    db.session.commit()

    return jsonify(result=action)

    # return redirect(url_for('mynews'))
    # return jsonify({'result': 'success', 'action': 'liked', 'news_id': news_id})


@app.route("/dislike_news/<int:news_id>", methods=["POST"])
def dislike_news(news_id):
    """
    Handles the disliking of a news item by the logged-in user.

    Args:
        news_id: An integer representing the ID of the news item to be disliked.

    Returns:
        A JSON response indicating the result of the dislike operation.
    """
    if "profile" not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_email = session["profile"]["email"]
    user = User.query.filter_by(email=user_email).first()
    news_item = News.query.get_or_404(news_id)

    if news_item in user.disliked_news:
        user.disliked_news.remove(news_item)
        action = "undisliked"
        news_item.dislike_count -= 1
    elif news_item in user.liked_news:
        user.liked_news.remove(news_item)
        news_item.dislike_count += 1
        news_item.like_count -= 1
        user.disliked_news.append(news_item)
        action = "switched_to_dislike"
    else:
        user.disliked_news.append(news_item)
        action = "disliked"
        news_item.dislike_count += 1
    db.session.commit()

    return jsonify(result=action)
    # return redirect(url_for('mynews'))
    # return jsonify({'result': 'success', 'action': 'disliked', 'news_id': news_id})


@app.route("/users")
def user_list():
    """
    Displays a list of users, accessible only to admin users.

    Returns:
        A rendered template showing the list of users or a redirect to the login page for non-admin users.
    """
    if "profile" in session:
        user_email = session["profile"]["email"]
        user = User.query.filter_by(email=user_email).first()

        if user is None or not user.isAdmin:
            # Redirect to a different page if the user is not an admin
            return redirect(url_for("home"))

        users = User.query.all()
        return render_template("users.html", users=users)
    else:
        # Redirect to the login page if the user is not logged in
        return redirect(url_for("login"))


@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    """
    Deletes a user from the database, accessible only to admin users.

    Args:
        user_id: An integer representing the ID of the user to be deleted.

    Returns:
        A redirect to the user list page or the home page based on the user's admin status.
    """
    # Check if user is logged in and if they are an admin
    if "profile" in session:
        user_email = session["profile"]["email"]
        user = User.query.filter_by(email=user_email).first()

        if user is None or not user.isAdmin:
            # Redirect to a different page if the user is not an admin
            return redirect(url_for("home"))

        user = User.query.get_or_404(user_id)

        # Decrement like_count and dislike_count for each news item the user has liked or disliked
        for news in user.liked_news:
            news.like_count -= 1

        for news in user.disliked_news:
            news.dislike_count -= 1

        db.session.delete(user)
        db.session.commit()

        return redirect(url_for("user_list"))  # Redirect to the user list page
    else:
        # Redirect to the login page if the user is not logged in
        return redirect(url_for("login"))


if __name__ == "__main__":
    # app.run()
    app.run(debug=True)
