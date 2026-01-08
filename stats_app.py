import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

@app.route('/stats')
def get_stats():
    count = Message.query.count()
    return jsonify({"total_messages": count})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)