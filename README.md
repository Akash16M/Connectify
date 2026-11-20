# Connectify – Real-Time Chat Website

A WhatsApp-inspired messaging website built with Python, Flask, Flask-SocketIO, MySQL, HTML, CSS and JavaScript.

## Features in this starter version
- User registration and login with hashed passwords
- One-to-one conversations
- Group conversations
- Real-time messages using Socket.IO
- Message history stored in MySQL
- Online/offline presence indicator
- Typing indicator
- Image and document attachments
- Responsive chat interface

## Requirements
- Python 3.10 or newer
- MySQL Server running locally
- MySQL port: **3307** (change in `.env` if yours is different)

## Setup on Windows
1. Extract the ZIP file.
2. Open the extracted `connectify` folder.
3. Make sure your MySQL server is running on port 3307.
4. Create the database once in MySQL:

   ```sql
   CREATE DATABASE connectify CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

5. Copy `.env.example` and rename the copy to `.env`.
6. Open `.env` and enter your MySQL password:

   ```env
   SECRET_KEY=make-this-a-long-random-value
   DB_HOST=127.0.0.1
   DB_PORT=3307
   DB_USER=root
   DB_PASSWORD=YOUR_MYSQL_PASSWORD
   DB_NAME=connectify
   ```

7. Double-click `run_windows.bat`, or run these commands in Command Prompt:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

8. Open **http://127.0.0.1:5000** in your browser.
9. Register two accounts in separate browsers (or use an incognito window) to test live chat.

## Important
- The app creates its tables automatically when `python app.py` starts. Create the database first.
- Keep `.env` private. Do not upload it to GitHub.
- This is a learning/portfolio starter, not a production-secure messaging service. Before public deployment, add CSRF protection, rate limiting, secure HTTPS cookies, malware scanning for uploads, robust presence tracking across multiple workers, and production server configuration.
- Files in `static/uploads` are served as static files in this starter version. Do not upload sensitive documents.
