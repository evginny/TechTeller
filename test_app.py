import unittest
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import json
from unittest.mock import patch
from app import app, db, User, News, check_if_admin
from urllib.parse import urlencode, quote_plus
from flask import url_for


class BasicTests(unittest.TestCase):
    # executed prior to each test
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        # Create an application context
        with self.app.app_context():
            db.create_all()

    # executed after each test
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class FlaskRoutesTests(BasicTests):
    def test_home_page(self):
        with app.test_client() as client:
            response = client.get("/", follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Welcome", response.data)

    def setUp(self):
        super().setUp()
        # Add test data for news items
        self.add_news_items()

    def add_news_items(self):
        with self.app.app_context():
            # Create and add news items to the database
            news_data = [
                {
                    "id": 1,
                    "by": "author1",
                    "time": 100,
                    "title": "News 1",
                    "url": "http://example.com/1",
                    "like_count": 5,
                    "dislike_count": 2,
                },
                {
                    "id": 2,
                    "by": "author2",
                    "time": 200,
                    "title": "News 2",
                    "url": "http://example.com/2",
                    "like_count": 3,
                    "dislike_count": 1,
                },
                {
                    "id": 3,
                    "by": "author3",
                    "time": 300,
                    "title": "News 3",
                    "url": "http://example.com/3",
                    "like_count": 10,
                    "dislike_count": 5,
                },
            ]

            for news in news_data:
                new_news_item = News(**news)
                db.session.add(new_news_item)
            db.session.commit()

    def test_mynews_default_sorting(self):
        # Test for default sorting (Newest first)
        with self.app.test_client() as client:
            response = client.get("/mynews")
            self.assertEqual(response.status_code, 200)

    def test_mynews_popularity_sorting(self):
        # Test for sorting by popularity
        with self.app.test_client() as client:
            response = client.get("/mynews?sort=popularity")
            self.assertEqual(response.status_code, 200)

    @patch("app.oauth.auth0.authorize_access_token")
    @patch("app.oauth.auth0.get")
    def test_callback_route(self, mock_get, mock_authorize_access_token):
        # Mock the token returned by authorize_access_token
        mock_token = {"access_token": "fake_token", "id_token": "fake_id_token"}
        mock_authorize_access_token.return_value = mock_token

        # Mock the userinfo response
        mock_userinfo = {
            "email": "test@example.com",
            "name": "Test User",
            "picture": "http://example.com/picture.jpg",
            "nickname": "testuser",
        }
        mock_get.return_value.json.return_value = mock_userinfo

        # Call the callback route
        response = self.client.get("/callback", follow_redirects=True)

        # Debug output
        print("Response status code:", response.status_code)
        print("Response data:", response.data)

        # Check if the response is correct
        self.assertEqual(response.status_code, 200)
        # Optionally, check for specific content in the response
        self.assertIn(b"Profile", response.data)
        self.assertIn(b"Sign out", response.data)

    @patch("app.oauth.auth0.authorize_redirect")
    def test_login_route(self, mock_authorize_redirect):
        # Mock the authorize_redirect method to return a redirect response
        mock_authorize_redirect.return_value = "Mocked OAuth Redirect"

        # Call the login route
        response = self.client.get("/login", follow_redirects=False)

        # Check if the response is a redirect to the OAuth service
        mock_authorize_redirect.assert_called_once()
        self.assertEqual(response.data.decode(), "Mocked OAuth Redirect")

    def test_logout_route(self):
        auth0_domain = os.environ.get("AUTH0_DOMAIN")
        client_id = os.environ.get("AUTH0_CLIENT_ID")
        # Set up a mock session
        with self.client as c:
            with c.session_transaction() as sess:
                sess["user"] = {"email": "test@example.com"}

            # Call the logout route
            response = self.client.get("/logout", follow_redirects=False)

            # Check if the session is cleared
            with c.session_transaction() as sess:
                self.assertNotIn("user", sess)

            # Check if the response is a redirect to the correct URL
            self.assertEqual(response.status_code, 302)
            expected_url = (
                "https://"
                + auth0_domain
                + "/v2/logout?"
                + urlencode(
                    {
                        "returnTo": url_for("home", _external=True),
                        "client_id": client_id,
                    },
                    quote_via=quote_plus,
                )
            )
            self.assertTrue(response.location.startswith(expected_url))

    def test_profile_logged_in(self):
        # Mock a user session
        with self.client as c:
            with c.session_transaction() as sess:
                sess["profile"] = {
                    "name": "Test User",
                    "email": "test@example.com",
                    "picture": "http://example.com/picture.jpg",
                }

            # Call the profile route
            response = c.get("/profile", follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Test User", response.data)
            self.assertIn(b"Profile", response.data)

    def test_profile_not_logged_in(self):
        with self.app.test_client() as client:
            # Make a GET request to the profile route
            response = client.get("/profile", follow_redirects=False)

            # Check that the response is a redirect to the home page
            self.assertEqual(response.status_code, 302)
            self.assertTrue("/" in response.headers["Location"])


class UserModelTestCase(unittest.TestCase):
    def test_user_repr(self):
        # Create a user instance
        user = User(
            given_name="John",
            family_name="Doe",
            nickname="johndoe",
            name="John Doe",
            email="john@example.com",
            picture="default.jpg",
            email_verified=True,
            isAdmin=False,
        )

        # Check the __repr__ method
        self.assertEqual(
            user.__repr__(), "User('John Doe', 'john@example.com', 'default.jpg')"
        )


class NewsModelTestCase(unittest.TestCase):
    def test_news_repr(self):
        # Create a news instance
        news = News(
            id=1,
            by="author",
            time=123456789,
            title="Sample News Title",
            url="http://example.com/news",
            like_count=10,
            dislike_count=2,
        )

        # Check the __repr__ method
        self.assertEqual(news.__repr__(), "<News Sample News Title>")


class CheckAdminFunctionTestCase(unittest.TestCase):
    def test_check_if_admin_with_admin_keywords(self):
        # Test with admin keywords in name and email
        admin_users = [
            User(name="Piyush Kumar", email="piyush@example.com"),
            User(name="Regular User", email="chashi@example.com"),
            User(name="Hansong Zhou", email="hansong@example.com"),
            User(name="Admin User", email="admin@zhou.com"),
            User(name="Jane Kalshnikova", email="jane.kalashn@gmail.com"),
        ]

        for user in admin_users:
            self.assertTrue(check_if_admin(user), f"Failed for user: {user}")

    def test_check_if_admin_without_admin_keywords(self):
        # Test with non-admin users
        non_admin_users = [
            User(name="Regular User", email="user@example.com"),
            User(name="John Doe", email="john.doe@example.com"),
        ]

        for user in non_admin_users:
            self.assertFalse(check_if_admin(user), f"Failed for user: {user}")

    def test_check_if_admin_for_specific_email(self):
        # Create a user with the specific email and a dummy name
        user_with_specific_email = User(
            name="Test User", email="jane.kalashn@gmail.com"
        )

        # Check if the user is recognized as an admin
        self.assertTrue(
            check_if_admin(user_with_specific_email),
            "User with specific email should be admin",
        )

        # Create a user with a different email and a dummy name
        user_with_different_email = User(name="Other User", email="other@example.com")

        # Check that this user is not recognized as an admin
        self.assertFalse(
            check_if_admin(user_with_different_email),
            "User with different email should not be admin",
        )


class NewsFeedRouteTestCase(BasicTests):
    def test_newsfeed_route(self):
        # Set up test data
        with self.app.app_context():
            for i in range(1, 11):
                news = News(
                    id=i,
                    by=f"author{i}",
                    time=123456789 + i,
                    title=f"Sample News Title {i}",
                    url=f"http://example.com/news{i}",
                    like_count=i * 10,
                    dislike_count=i * 2,
                )
                db.session.add(news)
            db.session.commit()

        # Call the newsfeed route
        response = self.client.get("/newsfeed", follow_redirects=True)

        # Check if the response status code is 200
        self.assertEqual(response.status_code, 200)

        # Check if the response is in JSON format
        self.assertEqual(response.content_type, "application/json")

        # Parse the JSON data from the response
        data = json.loads(response.data.decode())

        # Check if the correct number of news items are returned
        self.assertEqual(len(data["news_items"]), 10)


class LikeNewsRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Create a test user and news item
            test_user = User(email="test@example.com", name="Test User")
            test_news = News(
                id=1, title="Test News", by="author", like_count=0, dislike_count=0
            )
            db.session.add(test_user)
            db.session.add(test_news)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_like_news(self):
        with self.client as c:
            # Mock a user session
            with c.session_transaction() as sess:
                sess["profile"] = {"email": "test@example.com", "name": "Test User"}

            # Send a POST request to like the news
            response = c.post("/like_news/1", follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Fetch the updated news item
            news_item = News.query.get(1)
            self.assertEqual(news_item.like_count, 1)

            # Check the response for the correct action
            data = json.loads(response.data)
            self.assertEqual(data["result"], "liked")

            # Test unliking the news
            response = c.post("/like_news/1", follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Fetch the updated news item again
            news_item = News.query.get(1)
            self.assertEqual(news_item.like_count, 0)

            # Check the response for the correct action
            data = json.loads(response.data)
            self.assertEqual(data["result"], "unliked")


class LikeNewsWithoutSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Create a test news item
            test_news = News(
                id=1, title="Test News", by="author", like_count=0, dislike_count=0
            )
            db.session.add(test_news)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_like_news_without_session(self):
        # Send a POST request without a user session
        response = self.client.post("/like_news/1", follow_redirects=True)
        self.assertEqual(response.status_code, 401)

        # Check the response for the correct error message
        data = json.loads(response.data)
        self.assertEqual(data["error"], "User not logged in")


class SwitchLikeDislikeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Create a test user and news item
            test_user = User(email="test@example.com", liked_news=[], disliked_news=[])
            test_news = News(
                id=1, title="Test News", by="author", like_count=0, dislike_count=1
            )
            test_user.disliked_news.append(test_news)
            db.session.add(test_user)
            db.session.add(test_news)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_switch_like_dislike(self):
        # Mock a user session
        with self.client as c:
            with c.session_transaction() as sess:
                sess["profile"] = {"email": "test@example.com"}

            # Send a POST request to like the news item
            response = c.post("/like_news/1", follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Fetch the updated news item from the database
            news_item = News.query.get(1)

            # Check if the like count increased and dislike count decreased
            self.assertEqual(news_item.like_count, 1)
            self.assertEqual(news_item.dislike_count, 0)

            # Check the response for the correct action
            data = json.loads(response.data)
            self.assertEqual(data["result"], "switched_to_like")


class DislikeNewsTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the Flask test client
        self.app = app.test_client()

        # Create and push an application context
        self.ctx = app.app_context()
        self.ctx.push()

        # Set up the database within the application context
        db.create_all()

        # Create and add a test user to the database
        self.test_user = User(
            given_name="Test",
            family_name="User",
            nickname="testuser",
            name="Test User",
            email="test@example.com",
            picture="default.jpg",
            email_verified=True,
            isAdmin=False,
        )
        db.session.add(self.test_user)

        # Create and add a test news item to the database
        self.test_news = News(
            id=1,
            by="author",
            time=123456789,
            title="Sample News Title",
            url="http://example.com/news",
            like_count=0,
            dislike_count=0,
        )
        db.session.add(self.test_news)

        # Commit the changes to the database
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_dislike_news_first_time(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess["profile"] = {"email": "test@example.com"}

            response = c.post("/dislike_news/1", follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            news_item = News.query.get(1)
            self.assertEqual(news_item.dislike_count, 1)

            data = json.loads(response.data)
            self.assertEqual(data["result"], "disliked")

    def test_switch_like_to_dislike(self):
        # Query the user and news item from the database to ensure they're in an active session
        with self.app as c:
            with c.session_transaction() as sess:
                sess["profile"] = {"email": "test@example.com"}

            user = User.query.filter_by(email="test@example.com").first()
            news_item = News.query.get(1)

            # Add the news item to liked news first
            user.liked_news.append(news_item)
            db.session.commit()

            # Now perform the dislike action
            response = c.post("/dislike_news/1", follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Refresh the news item from the database
            news_item = News.query.get(1)
            self.assertIn(news_item, user.disliked_news)
            self.assertNotIn(news_item, user.liked_news)
            self.assertEqual(news_item.dislike_count, 1)

            data = json.loads(response.data)
            self.assertEqual(data["result"], "switched_to_dislike")

    def test_undislike_news(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess["profile"] = {"email": "test@example.com"}
            # Query the user and news item from the database to ensure they're in an active session
            user = User.query.filter_by(email="test@example.com").first()
            news_item = News.query.get(1)

            # Add the news item to disliked news first
            user.disliked_news.append(news_item)
            db.session.commit()

            # Now perform the undislike action
            response = c.post("/dislike_news/1", follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Refresh the news item from the database
            news_item = News.query.get(1)
            self.assertNotIn(news_item, user.disliked_news)
            self.assertEqual(news_item.dislike_count, -1)

            data = json.loads(response.data)
            self.assertEqual(data["result"], "undisliked")


if __name__ == "__main__":
    unittest.main()
