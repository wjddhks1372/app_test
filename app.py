import os
import time
from flask import Flask, request, jsonify
from redis import Redis
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from celery import Celery # 추가

app = Flask(__name__)

# --- 기존 설정 유지 ---
redis_host = os.environ.get('REDIS_HOST', 'redis')
db_url = os.environ.get('DATABASE_URL', 'postgresql://user:password@db:5432/myapp')
redis = Redis(host=redis_host, port=6379, decode_responses=True)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Celery 설정 추가 ---
# Redis를 메시지 브로커(우체국)로 사용합니다.
celery = Celery(app.name, broker=f'redis://{redis_host}:6379/0', backend=f'redis://{redis_host}:6379/0')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

# --- 비동기로 처리할 '무거운 작업' 정의 ---
@celery.task
def heavy_processing_task(content):
    print(f"[Worker] 데이터 '{content}' 분석 시작 (10초 소요)...")
    time.sleep(10)
    print(f"[Worker] 분석 완료!")
    return True

def init_db():
    retries = 10
    while retries > 0:
        try:
            with app.app_context():
                db.create_all()
            print("Successfully connected to the database!")
            return
        except OperationalError:
            retries -= 1
            print(f"Waiting for database... ({10-retries}/10)")
            time.sleep(3)
    print("Could not connect to the database. Exiting.")

init_db()

@app.route('/')
def index():
    count = redis.incr('hits')
    messages = Message.query.all()
    msg_list = "".join([f"<li>{m.content}</li>" for m in messages])
    
    return f"""
    <h1>🚀 비동기 작업 큐 통합 시스템</h1>
    <p><b>방문자 수:</b> {count}</p>
    <hr>
    <h3>방명록 (DB 저장)</h3>
    <ul>{msg_list if msg_list else "아직 메시지가 없습니다."}</ul>
    <form action="/add" method="post">
        <input type="text" name="content" placeholder="방명록 남기기" required>
        <button type="submit">저장 및 비동기 작업 요청</button>
    </form>
    <p><i>* 글을 남기면 DB에 즉시 저장되고, 10초짜리 분석 작업이 백그라운드에서 시작됩니다.</i></p>
    """

@app.route('/add', methods=['POST'])
def add_message():
    content = request.form.get('content')
    if content:
        # 1. 즉시 처리: DB 저장
        new_msg = Message(content=content)
        db.session.add(new_msg)
        db.session.commit()
        
        # 2. 비동기 처리: 일꾼(Worker)에게 무거운 작업 던지기
        heavy_processing_task.delay(content) # .delay()가 핵심!
        
    return f"<script>alert('DB 저장 완료! 무거운 작업은 일꾼이 시작했습니다.'); window.location.href='/';</script>"

@app.route('/health')
def health_check():
    try:
        db.session.execute('SELECT 1')
        redis.ping()
        return jsonify(status="healthy"), 200
    except Exception as e:
        return jsonify(status="unhealthy", reason=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)