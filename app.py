import eventlet
eventlet.monkey_patch()

import os
import time
import requests
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from celery import Celery
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'

# 환경 변수 설정
redis_host = os.environ.get('REDIS_HOST', 'redis')
db_url = os.environ.get('DATABASE_URL', 'postgresql://user:password@db:5432/myapp')

# 서비스 초기화
# 1. DB & Redis
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# 2. Celery (비동기 일꾼용 우체국)
celery = Celery(app.name, broker=f'redis://{redis_host}:6379/0', backend=f'redis://{redis_host}:6379/0')
# 3. SocketIO (실시간 통신용)
socketio = SocketIO(app, message_queue=f'redis://{redis_host}:6379/0', cors_allowed_origins="*")

# DB 모델
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

# 비동기 작업 정의
@celery.task
def heavy_processing_task(content):
    print(f"[Worker] '{content}' 분석 중... (10초 소요)")
    time.sleep(10)
    print(f"[Worker] 분석 완료!")
    return True

# DB 초기화 (연결 재시도 로직 포함)
def init_db():
    retries = 10
    while retries > 0:
        try:
            with app.app_context():
                db.create_all()
            return True
        except OperationalError:
            retries -= 1
            time.sleep(3)
    return False

init_db()

@app.route('/')
def index():
    messages = Message.query.all()
    # 마이크로서비스(stats-service)에서 통계 가져오기
    try:
        resp = requests.get("http://stats-service:5001/stats", timeout=2)
        total_count = resp.json().get('total_messages', 0)
    except:
        total_count = "연결 불가"

    return f"""
    <h1>⚡ 실시간 풀스택 시스템</h1>
    <p><b>총 메시지 수(MSA 통계):</b> <span id="total-count">{total_count}</span></p>
    <hr>
    <ul id="msg-list">{"".join([f"<li>{m.content}</li>" for m in messages])}</ul>
    <input type="text" id="input-msg" placeholder="내용 입력">
    <button onclick="send()">실시간 전송</button>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        var socket = io();
        socket.on('new_message', function(data) {{
            var li = document.createElement("li");
            li.textContent = data.content;
            document.getElementById("msg-list").appendChild(li);
        }});
        function send() {{
            var val = document.getElementById("input-msg").value;
            socket.emit('submit_message', {{content: val}});
            document.getElementById("input-msg").value = "";
        }}
    </script>
    """

@socketio.on('submit_message')
def handle_msg(data):
    content = data.get('content')
    if content:
        # 1. DB 저장
        new_msg = Message(content=content)
        db.session.add(new_msg)
        db.session.commit()
        # 2. 비동기 작업 요청 (일꾼에게)
        heavy_processing_task.delay(content)
        # 3. 실시간 브로드캐스트 (모든 유저에게)
        emit('new_message', {'content': content}, broadcast=True)

@app.route('/health')
def health():
    return jsonify(status="healthy"), 200

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)