import time
import redis
from flask import Flask

app = Flask(__name__)
# 'redis'라는 이름의 컨테이너에 접속 (도커 네트워크의 마법)
cache = redis.Redis(host='redis', port=6379)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits') # 방문자 수 1 증가
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

@app.route('/')
def hello():
    count = get_hit_count()
    return f'성공! 현재 방문자 수는 {count}명입니다.\n'

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)