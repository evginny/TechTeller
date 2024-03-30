# TechTeller
## Description
This web application is a Flask-based project that interacts with the Hacker News API to fetch and display news items. It allows users to view, like, and dislike news articles, providing an engaging platform for news consumption. The application integrates user authentication and session management, ensuring a personalized experience.
[Visit TechTeller](https://ek.evginny.com/)
## Features
* News Fetching: Automatically fetches the latest news from Hacker News API.
* User Authentication: Supports user login using OAuth.
* News Interaction: Users can like or dislike news items.
* Responsive UI: A user-friendly interface accessible on various devices.
* Session Management: Maintains user sessions for a personalized experience.

### URLs:
* Home Page (/): Displays the home page of the application.
* User Callback (/callback): Handles the callback from the OAuth provider.
* User Login (/login): Redirects users to the OAuth provider for login.
* User Logout (/logout): Logs out the user and clears the session.
* News Feed (/newsfeed): Fetches and displays news items from the database.
* User Profile (/profile): Displays the profile of the logged-in user.
* User's News (/mynews): Shows news items with options for users to like or dislike.
* Like News (/like_news/int:news_id): Allows users to like a news item.
* Dislike News (/dislike_news/int:news_id): Allows users to dislike a news item.
* User List (/users): Accessible to admin users to view a list of users.
* Delete User (/delete_user/int:user_id): Allows admin users to delete a user.

## Installation
1. Clone the Repository: 
    * git clone https://gitlab.com/cop45219873343/ek19n.git cd ek19n
2. Set Up a Virtual Environment (optional but recommended):
    * python -m venv venv source venv/bin/activate
3.  Install Dependencies:
    * pip install -r requirements.txt
4.  Database Setup: 
    * flask db init
    * flask db migrate
    * flask db upgrade
5. Running the application:
    * flask run
6. Setting Up Nginx and Gunicorn:
    * Configure Nginx to proxy requests to Gunicorn.
    * Set up Gunicorn as the WSGI server.

## Configs
### Nginx Configuration
  
The Nginx configuration is set up to serve the application on a domain with SSL enabled and to serve static files from a specified directory.  
server {  
server_name ek.evginny.com;  
location /static {  
alias <path/static>;  
}  
location / {  
proxy_pass http://localhost:8000;  
include /etc/nginx/proxy_params;  
proxy_redirect off;  
}  
listen 443 ssl; # managed by Certbot  
ssl_certificate /etc/letsencrypt/live/ek.evginny.com/fullchain.pem; # managed by Certbot  
ssl_certificate_key /etc/letsencrypt/live/ek.evginny.com/privkey.pem; # managed by Certbot  
include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot  
ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot  
}  


server {  
if ($host = ek.evginny.com) {  
return 301 https://hosthosthostrequest_uri;  
} # managed by Certbot  

listen 80;  
server_name ek.evginny.com;  
return 404; # managed by Certbot  

### Supervisor Configuration
Supervisor is used to manage the Gunicorn process for the Flask application.  
[program:myproject]  
directory=path/myproject  
command=path/.local/bin/gunicorn -w 3 app:app  
user=username  
autostart=true  
autorestart=true  
stopasgroup=true  
killasgroup=true  
stderr_logfile=/var/log/myproject/myproject.err.log  
stdout_logfile=/var/log/myproject/myproject.out.log  
### Gunicorn Configuration
Gunicorn is configured to run the Flask application with 3 worker processes.  
gunicorn -w 3 app:app  
### Cron Job
A cron job is set up to run a script periodically (every hour in this case) to fetch news from Hacker News API.  
0 * * * * cd /home/ek19n/myproject && /usr/bin/python3 fetch_hackernews.py

## Testing
To run the unit tests and generate a coverage report, follow these steps:
* Run Tests with Coverage:
    * coverage run -m pytest
* Generate Coverage Report:
    * coverage report
* View Detailed HTML Report (optional):
    * coverage html
