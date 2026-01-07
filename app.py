import os
from flask import Flask, request, jsonify
from redis import Redis
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Redis 설정
redis = Redis(host=os.environ.get('REDIS_HOST', 'redis'), port=6379)

# PostgreSQL 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db:5432/myapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 방명록 모델 정의
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

# 서버 시작 시 테이블 자동 생성
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    count = redis.incr('hits')
    
    # DB에서 모든 메시지 가져오기
    messages = Message.query.all()
    msg_list = "<br>".join([m.content for m in messages])
    
    return f"""
    <h1>CI/CD + HTTPS + DB 완벽 가동!</h1>
    <p>현재 방문자 수: {count}</p>
    <hr>
    <h3>방명록</h3>
    {msg_list if msg_list else "아직 메시지가 없습니다."}
    <form action="/add" method="post">
        <input type="text" name="content">
        <button type="submit">글쓰기</button>
    </form>
    """

@app.route('/add', methods=['POST'])
def add_message():
    content = request.form.get('content')
    if content:
        new_msg = Message(content=content)
        db.session.add(new_msg)
        db.session.commit()
    return f"<script>window.location.href='/';</script>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)