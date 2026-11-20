import os
from datetime import datetime
from functools import wraps

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
socketio = SocketIO(app, cors_allowed_origins=[], async_mode="threading")

online_users = set()
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "doc", "docx"}

def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "connectify"),
        cursorclass=DictCursor,
        charset="utf8mb4",
        autocommit=True
    )

def init_db():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(40) NOT NULL UNIQUE,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(100) NULL,
                    is_group TINYINT(1) NOT NULL DEFAULT 0,
                    created_by INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_members (
                    conversation_id INT NOT NULL,
                    user_id INT NOT NULL,
                    PRIMARY KEY (conversation_id, user_id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    sender_id INT NOT NULL,
                    body TEXT NULL,
                    attachment VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_messages_conversation (conversation_id, id)
                ) ENGINE=InnoDB
            """)
    finally:
        conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def is_member(cur, conversation_id, user_id):
    cur.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=%s AND user_id=%s",
        (conversation_id, user_id)
    )
    return cur.fetchone() is not None

def conversation_payload(cur, conversation_id, user_id):
    cur.execute("SELECT id, title, is_group FROM conversations WHERE id=%s", (conversation_id,))
    conv = cur.fetchone()
    if not conv:
        return None
    cur.execute("""
        SELECT u.id, u.username FROM users u
        JOIN conversation_members cm ON cm.user_id=u.id
        WHERE cm.conversation_id=%s AND u.id<>%s ORDER BY u.username
    """, (conversation_id, user_id))
    members = cur.fetchall()
    if conv["is_group"]:
        display = conv["title"] or "Group chat"
    else:
        display = members[0]["username"] if members else "Conversation"
    return {"id": conv["id"], "title": display, "is_group": bool(conv["is_group"]), "members": members}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("chat"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 40:
            flash("Username must be between 3 and 40 characters.", "error")
        elif "@" not in email:
            flash("Enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        else:
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username,email,password_hash) VALUES (%s,%s,%s)",
                        (username, email, generate_password_hash(password))
                    )
                flash("Account created. Please sign in.", "success")
                return redirect(url_for("login"))
            except pymysql.err.IntegrityError:
                flash("Username or email already exists.", "error")
            finally:
                conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username=%s OR email=%s", (identity, identity.lower()))
                user = cur.fetchone()
        finally:
            conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("chat"))
        flash("Incorrect username/email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=session["username"], user_id=session["user_id"])

@app.get("/api/users")
@login_required
def users():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users WHERE id<>%s ORDER BY username", (session["user_id"],))
            result = cur.fetchall()
        return jsonify(result)
    finally:
        conn.close()

@app.get("/api/conversations")
@login_required
def conversations():
    uid = session["user_id"]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.title, c.is_group,
                       (SELECT m.body FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS last_message,
                       (SELECT m.created_at FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS last_time
                FROM conversations c
                JOIN conversation_members cm ON cm.conversation_id=c.id
                WHERE cm.user_id=%s
                ORDER BY COALESCE(
                    (SELECT m2.created_at FROM messages m2 WHERE m2.conversation_id=c.id ORDER BY m2.id DESC LIMIT 1),
                    c.created_at
                ) DESC
            """, (uid,))
            rows = cur.fetchall()
            output = []
            for row in rows:
                payload = conversation_payload(cur, row["id"], uid)
                if payload:
                    output.append({**payload, "last_message": row["last_message"] or "Start a conversation"})
        return jsonify(output)
    finally:
        conn.close()

@app.post("/api/conversations/direct")
@login_required
def direct_conversation():
    other_id = request.json.get("user_id")
    uid = session["user_id"]
    if not other_id or int(other_id) == uid:
        return jsonify({"error": "Invalid user."}), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id=%s", (other_id,))
            if not cur.fetchone():
                return jsonify({"error": "User not found."}), 404
            cur.execute("""
                SELECT c.id FROM conversations c
                JOIN conversation_members a ON a.conversation_id=c.id AND a.user_id=%s
                JOIN conversation_members b ON b.conversation_id=c.id AND b.user_id=%s
                WHERE c.is_group=0
                LIMIT 1
            """, (uid, other_id))
            found = cur.fetchone()
            if found:
                cid = found["id"]
            else:
                cur.execute("INSERT INTO conversations (is_group, created_by) VALUES (0,%s)", (uid,))
                cid = cur.lastrowid
                cur.executemany(
                    "INSERT INTO conversation_members (conversation_id,user_id) VALUES (%s,%s)",
                    [(cid, uid), (cid, int(other_id))]
                )
            payload = conversation_payload(cur, cid, uid)
        return jsonify(payload)
    finally:
        conn.close()

@app.post("/api/conversations/group")
@login_required
def create_group():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    member_ids = data.get("member_ids") or []
    if len(title) < 2 or not member_ids:
        return jsonify({"error": "Enter a group name and select at least one member."}), 400
    uid = session["user_id"]
    ids = {uid}
    try:
        ids.update(int(x) for x in member_ids)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid members."}), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO conversations (title,is_group,created_by) VALUES (%s,1,%s)", (title, uid))
            cid = cur.lastrowid
            cur.executemany(
                "INSERT INTO conversation_members (conversation_id,user_id) VALUES (%s,%s)",
                [(cid, x) for x in ids]
            )
            payload = conversation_payload(cur, cid, uid)
        return jsonify(payload)
    finally:
        conn.close()

@app.get("/api/messages/<int:conversation_id>")
@login_required
def get_messages(conversation_id):
    uid = session["user_id"]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if not is_member(cur, conversation_id, uid):
                return jsonify({"error": "Not allowed."}), 403
            cur.execute("""
                SELECT m.id, m.body, m.attachment, m.created_at, m.sender_id, u.username
                FROM messages m JOIN users u ON u.id=m.sender_id
                WHERE m.conversation_id=%s ORDER BY m.id ASC LIMIT 200
            """, (conversation_id,))
            rows = cur.fetchall()
            for row in rows:
                row["created_at"] = row["created_at"].strftime("%H:%M")
                row["mine"] = row["sender_id"] == uid
        return jsonify(rows)
    finally:
        conn.close()

@app.post("/api/upload")
@login_required
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Choose a file."}), 400
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "File type not allowed."}), 400
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    safe_name = f"{session['user_id']}_{int(datetime.utcnow().timestamp())}_{filename}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], safe_name))
    return jsonify({"attachment": f"/static/uploads/{safe_name}", "filename": filename})

@socketio.on("connect")
def socket_connect():
    uid = session.get("user_id")
    if not uid:
        return False
    online_users.add(uid)
    join_room(f"user_{uid}")
    emit("presence_snapshot", {"user_ids": list(online_users)})
    emit("presence", {"user_id": uid, "online": True}, broadcast=True)

@socketio.on("disconnect")
def socket_disconnect():
    uid = session.get("user_id")
    if uid:
        online_users.discard(uid)
        emit("presence", {"user_id": uid, "online": False}, broadcast=True)

@socketio.on("join_conversation")
def join_conversation(data):
    uid = session.get("user_id")
    cid = int(data.get("conversation_id", 0))
    if not uid:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if is_member(cur, cid, uid):
                join_room(f"conversation_{cid}")
    finally:
        conn.close()

@socketio.on("send_message")
def send_message(data):
    uid = session.get("user_id")
    if not uid:
        return
    cid = int(data.get("conversation_id", 0))
    body = (data.get("body") or "").strip()
    attachment = data.get("attachment")
    if not body and not attachment:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if not is_member(cur, cid, uid):
                return
            cur.execute(
                "INSERT INTO messages (conversation_id,sender_id,body,attachment) VALUES (%s,%s,%s,%s)",
                (cid, uid, body or None, attachment)
            )
            message_id = cur.lastrowid
            cur.execute("SELECT username FROM users WHERE id=%s", (uid,))
            username = cur.fetchone()["username"]
        message = {
            "id": message_id, "conversation_id": cid, "sender_id": uid,
            "username": username, "body": body, "attachment": attachment,
            "created_at": datetime.now().strftime("%H:%M")
        }
        emit("new_message", message, room=f"conversation_{cid}")
    finally:
        conn.close()

@socketio.on("typing")
def typing(data):
    uid = session.get("user_id")
    if not uid:
        return
    cid = int(data.get("conversation_id", 0))
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if not is_member(cur, cid, uid):
                return
            cur.execute("SELECT username FROM users WHERE id=%s", (uid,))
            username = cur.fetchone()["username"]
        emit("typing", {"user_id": uid, "username": username, "typing": bool(data.get("typing"))},
             room=f"conversation_{cid}", include_self=False)
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        init_db()
        print("Connectify database tables are ready.")
    except Exception as exc:
        print("\\nDatabase connection failed. Check your .env settings.")
        print(f"Details: {exc}")
        raise
    socketio.run(app, host="127.0.0.1", port=5000, debug=True, allow_unsafe_werkzeug=True)
