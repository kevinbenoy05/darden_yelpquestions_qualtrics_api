from flask import Flask, jsonify
import json, random

app = Flask(__name__)
questions = []

@app.route('/questions', methods = ['GET'])
def get_questions():
    random_questions = random.sample(questions, k=5)
    return jsonify(random_questions)

if __name__ == '__main__':
    app.debug(True)