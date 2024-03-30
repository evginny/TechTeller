"""
This module fetches news from Hacker News API and processes the data for further use.
"""
import requests
from requests.exceptions import RequestException
from app import app, db, News


def fetch_hackernews():
    """
    Fetches the top news stories from Hacker News API and updates the database.

    This function retrieves the latest top 50 news stories from the Hacker News API.
    Each news story is checked against the existing records in the database. If a story
    does not exist in the database, it is added. If it already exists, it is updated
    with the latest data.

    After updating the database with new and existing stories, the function checks the
    total number of news records. If there are more than 150 records, it deletes the
    oldest ones to maintain a maximum of 150 records in the database.

    The function does not return any value but updates the database with the latest
    news stories and maintains the database size.
    """
    try:
        response = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty"
        )
        news_ids = response.json()
    except RequestException as e:
        print(f'Error fetching top stories: {e}')
        return 

    for news_id in news_ids[:50]:
        try:
            news_response = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{news_id}.json?print=pretty"
            )
            news_data = news_response.json()
        except RequestException as e:
            print(f"Error fetching news item {news_id}: {e}")
            continue

        # Check if news already exists in the database
        news_item = News.query.get(news_data["id"])

        if not news_item:
            # Create a new news item if it doesn't exist
            news_item = News(id=news_data["id"])

        # Update the news item with the latest data
        news_item.by = news_data.get("by")
        news_item.time = news_data.get("time")
        news_item.title = news_data.get("title")
        news_item.url = news_data.get("url")

        # Add to session and commit to save the news item to the database
        db.session.add(news_item)
    # Commit all news items to the database at once
    db.session.commit()

    # Check the total number of news records
    news_count = News.query.count()
    # If more than 50, delete the oldest
    if news_count > 150:
        # Find the IDs of the oldest news
        oldest_news = News.query.order_by(News.time.asc()).limit(news_count - 150).all()
        for old_news in oldest_news:
            db.session.delete(old_news)

        # Commit the deletions
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        fetch_hackernews()
