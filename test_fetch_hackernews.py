"""
Module: test_fetch_hackernews.py

This module contains unit tests for the fetch_hackernews function, 
which is responsible for fetching news data from the Hacker News API 
and storing it in a database. 
The tests cover various scenarios including successful data fetching, 
handling API errors, updating existing news items, and dealing with request exceptions.

Classes:
    FetchHackerNewsTests: Contains all the test cases for the fetch_hackernews function.

Test Cases:
    test_fetch_hackernews: 
        Tests successful fetching and storing of news items from the Hacker News API.
    test_fetch_hackernews_api_error: 
        Tests the behavior of fetch_hackernews when the API returns an error.
    test_fetch_hackernews_existing_items:
        Tests updating existing news items in the database with new data from the API.
    test_fetch_hackernews_with_request_exception:
        Tests the handling of RequestExceptions during API calls.
"""


import unittest
from unittest.mock import patch, MagicMock
import requests
from requests.exceptions import RequestException
from app import app, db, News
from fetch_hackernews import fetch_hackernews


class FetchHackerNewsTests(unittest.TestCase):
    def setUp(self):
        """
        Set up the test environment before each test.

        This method initializes the Flask test client, sets up a new application context,
        and creates a fresh in-memory database for testing.
        It is automatically called before each test method.
        """
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """
        Clean up after each test.

        This method removes the database session and drops all tables, ensuring a clean state
        for the next test. It is automatically called after each test method.
        """
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch("fetch_hackernews.requests.get")
    def test_fetch_hackernews(self, mock_get):
        """
        Test successful fetching and storing of news items from the Hacker News API.

        This test mocks the requests.get method to simulate API responses and verifies
        that news items are correctly fetched and stored in the database.
        """
        # Mock the response from the Hacker News API
        mock_get.return_value.json.side_effect = [
            [1, 2, 3],  # First call returns a list of news IDs
            {
                "id": 1,
                "title": "Test News 1",
                "by": "author1",
                "time": 123456,
                "url": "http://example.com/1",
            },
            {
                "id": 2,
                "title": "Test News 2",
                "by": "author2",
                "time": 123457,
                "url": "http://example.com/2",
            },
            {
                "id": 3,
                "title": "Test News 3",
                "by": "author3",
                "time": 123458,
                "url": "http://example.com/3",
            },
        ]

        # Call the function within an application context
        with self.app.app_context():
            fetch_hackernews()

            # Assert that news items are added to the database
            self.assertEqual(News.query.count(), 3)

    @patch("fetch_hackernews.requests.get")
    def test_fetch_hackernews_api_error(self, mock_get):
        """
        Test the behavior of fetch_hackernews when the API returns an error.

        This test simulates an API error using a mocked requests.get method and checks that
        no new records are added to the database when an API error occurs.
        """
        # Simulate a RequestException
        mock_get.side_effect = RequestException("API Error")

        with app.app_context():
            # Get the initial count of news records in the database
            initial_count = News.query.count()

            # Call the function
            fetch_hackernews()

            # Get the count after attempting to fetch news
            final_count = News.query.count()

        self.assertEqual(initial_count, final_count)

    @patch("fetch_hackernews.requests.get")
    def test_fetch_hackernews_existing_items(self, mock_get):
        """
        Test updating existing news items in the database with new data from the API.

        This test sets up an initial news item in the database, mocks API responses to provide
        updated data for the same news item, and verifies that the existing record is updated
        accordingly.
        """
        # Setup initial news item in the database
        with self.app.app_context():
            existing_news = News(
                id=1,
                title="Old News 1",
                by="author1",
                time=123450,
                url="http://example.com/old1",
            )
            db.session.add(existing_news)
            db.session.commit()

        # Mock the API response
        mock_get.return_value.json.side_effect = [
            [1],  # Existing news ID
            {
                "id": 1,
                "title": "Updated News 1",
                "by": "author1",
                "time": 123456,
                "url": "http://example.com/1",
            },
        ]

        # Call the function
        with self.app.app_context():
            fetch_hackernews()

            # Assert that the existing news item is updated
            updated_news = News.query.get(1)
            self.assertIsNotNone(updated_news)
            self.assertEqual(updated_news.title, "Updated News 1")

    @patch("fetch_hackernews.requests.get")
    def test_fetch_hackernews_with_request_exception(self, mock_get):
        """
        Test the handling of RequestExceptions during API calls.

        This test mocks the requests.get method to simulate a RequestException on API calls after
        the initial fetch of news IDs. It verifies that no records are added to the database
        in case of such exceptions.
        """
        # Mock the response for the initial API call (list of news IDs)
        mock_get.return_value.json.return_value = [1, 2, 3]

        # Create a side effect for subsequent calls to simulate RequestException
        def side_effect(*args, **kwargs):
            if "topstories.json" in args[0]:
                return MagicMock(json=lambda: [1, 2, 3])
            else:
                raise RequestException("API Error")

        mock_get.side_effect = side_effect

        # Call the function within an application context
        with self.app.app_context():
            fetch_hackernews()

            self.assertEqual(News.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
