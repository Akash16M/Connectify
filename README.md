# 💬 Connectify – Real-Time Chat Website

**Connectify** is a WhatsApp-inspired real-time messaging web application built using Python, Flask, Flask-SocketIO, and MySQL. It allows users to communicate through private and group conversations with an interactive and responsive interface.

## 🚀 Features

- 🔐 **User Authentication** – Secure user registration and login with password hashing.
- 💬 **Private Chat** – One-to-one real-time messaging.
- 👥 **Group Chat** – Communicate with multiple users in group conversations.
- ⚡ **Real-Time Messaging** – Send and receive messages instantly using Socket.IO.
- 🟢 **Online/Offline Status** – View user availability.
- ✍️ **Typing Indicator** – Know when another user is typing.
- 🕘 **Message History** – Store and retrieve conversations using MySQL.
- 📎 **File Sharing** – Share images and documents.
- 📱 **Responsive Design** – User-friendly interface for different screen sizes.

## 🛠️ Technologies Used

| Category | Technology |
|---|---|
| Backend | Python, Flask |
| Real-Time Communication | Flask-SocketIO |
| Frontend | HTML, CSS, JavaScript |
| Database | MySQL |
| Authentication | Flask Sessions, Password Hashing |

## 📂 Project Structure

```text
Connectify/
│
├── app.py
├── requirements.txt
├── run_windows.bat
├── .env.example
├── .gitignore
├── README.md
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── chat.html
│
└── static/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── chat.js
    └── uploads/
```

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Akash16M/Connectify.git
```

### 2. Navigate to the Project Folder

```bash
cd Connectify
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv
```

### 4. Activate Virtual Environment

```bash
.venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure MySQL Database

Create a database in MySQL:

```sql
CREATE DATABASE connectify
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

### 7. Configure Environment Variables

Copy `.env.example` and rename the copy to `.env`.

Update your database credentials:

```env
SECRET_KEY=your_secret_key
DB_HOST=127.0.0.1
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=connectify
```

**Note:** Update the database port and credentials according to your MySQL configuration. Never upload your `.env` file to GitHub.

### 8. Run the Application

```bash
python app.py
```

Alternatively, Windows users can run `run_windows.bat`.

### 9. Open in Browser

```text
http://127.0.0.1:5000
```

Register two different accounts using separate browsers or an incognito window to test real-time messaging.

## 🗄️ Database

Connectify uses MySQL to store:

- User account information
- Private and group conversations
- Chat messages
- Related messaging data

The application automatically creates the required tables when it starts. Create the database before running the application.

## 🔮 Future Improvements

- [ ] Cloud deployment
- [ ] User profile pictures
- [ ] Message read receipts
- [ ] Voice and video calling
- [ ] Message deletion and editing
- [ ] Improved file storage
- [ ] Enhanced security and scalability

## 👨‍💻 Developer

**Akash**

- GitHub: [@Akash16M](https://github.com/Akash16M)
- Project: [Connectify Repository](https://github.com/Akash16M/Connectify)

## 📄 License

This project is developed for educational and portfolio purposes.

---

⭐ If you find this project interesting, consider giving it a star!