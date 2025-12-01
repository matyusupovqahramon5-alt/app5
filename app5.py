from flask import Flask, redirect, url_for, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from authlib.integrations.flask_client import OAuth
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key_render_2025'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Google OAuth sozlamalari (Renderda Environment Variables qilib qo‘shasiz)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='YOUR_GOOGLE_CLIENT_ID',       # Render → Environment Variables ga qo‘shiladi
    client_secret='YOUR_GOOGLE_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

users = {}  # {sid: {"name": "Ali", "email": "ali@gmail.com", "picture": "url"}}

HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Chat 24/7</title>
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <style>
        body{margin:0;background:#000;color:#fff;font-family:system-ui;height:100vh;display:flex;flex-direction:column}
        header{background:#1a1a1a;padding:15px;text-align:center;position:relative}
        #user{display:flex;align-items:center;gap:10px;font-size:14px;position:absolute;left:15px;top:10px}
        #user img{border-radius:50%;width:32px;height:32px}
        #messages{flex:1;overflow-y:auto;padding:10px;background:#0d0d0d}
        .msg{max-width:80%;margin:8px 0;padding:12px 16px;border-radius:18px;word-wrap:break-word}
        .mine{background:#0d6efd;color:white;margin-left:auto;border-bottom-right-radius:4px}
        .other{background:#333;color:#ddd;border-bottom-left-radius:4px}
        .name{font-weight:600;font-size:13px;margin-bottom:4px}
        form{display:flex;padding:10px;background:#1a1a1a;border-top:1px solid #333;gap:8px}
        input{flex:1;background:#333;color:#fff;border:none;border-radius:25px;padding:14px;font-size:16px}
        button{background:#0d6efd;color:#fff;border:none;border-radius:50%;width:50px;height:50px;font-size:20px}
        .login{background:#1a1a1a;height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center}
        .google-btn{background:#4285f4;color:#fff;padding:14px 24px;border-radius:8px;font-size:18px;text-decoration:none;display:inline-flex;align-items:center;gap:10px}
    </style>
</head>
<body>
{% if not session.get('user') %}
<div class="login">
    <h1>Google Chat 24/7</h1>
    <br><br>
    <a href="/login" class="google-btn">Sign in with Google</a>
</div>
{% else %}
<header>
    <div id="user">
        <img src="{{ session.user.picture }}" alt="">
        <span>{{ session.user.name }}</span>
    </div>
    <b>Google Chat 24/7</b>
</header>
<div id="messages"></div>
<form onsubmit="send();return false;">
    <input id="msg" placeholder="Xabar yozing..." autocomplete="off" required autofocus>
    <button>Send</button>
</form>
{% endif %}

<script>
    {% if session.get('user') %}
    const socket = io();
    socket.on("connect", () => console.log("Connected"));

    socket.on("msg", d => {
        let div = document.createElement("div");
        div.className = "msg " + (d.email === "{{ session.user.email }}" ? "mine" : "other");
        div.innerHTML = `<div class="name">${d.name}</div>${d.text}`;
        document.getElementById("messages").appendChild(div);
        div.scrollIntoView({behavior:"smooth"});
    });

    function send() {
        let text = document.getElementById("msg").value.trim();
        if (!text) return;
        socket.emit("msg", {text});
        document.getElementById("msg").value = "";
    }
    document.getElementById("msg").addEventListener("keypress", e => {if(e.key==="Enter") send()});
    {% endif %}
</script>
</body>
</html>"""

@app.route("/")
def index():
    if not session.get("user"):
        return render_template_string(HTML)
    return render_template_string(HTML)

@app.route("/login")
def login():
    redirect_uri = url_for('auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth")
def auth():
    token = google.authorize_access_token()
    userinfo = token['userinfo']
    session['user'] = {
        "name": userinfo.name,
        "email": userinfo.email,
        "picture": userinfo.picture
    }
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@socketio.on("connect")
def handle_connect():
    if not session.get("user"):
        return False  # Google orqali kirmaganlarni ulamaymiz!
    users[request.sid] = session["user"]

@socketio.on("msg")
def handle_msg(data):
    user = users.get(request.sid)
    if not user: return
    msg = {
        "name": user["name"],
        "email": user["email"],
        "text": data["text"][:500]
    }
    emit("msg", msg, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    users.pop(request.sid, None)

if __name__ == "__main__":
    socketio.run(app)