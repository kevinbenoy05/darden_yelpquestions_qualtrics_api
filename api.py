from flask import Flask, jsonify
from json import load
import random
app = Flask(__name__)

def load_questions():
    reviews = []
    with open("random_reviews.json", encoding='utf-8') as json_file:
        reviews_list = load(json_file)
    random_indexes = random.sample(range(len(reviews_list)), 5)
    for i in random_indexes:
        reviews.append(reviews_list[i])
    return reviews

@app.route('/questions', methods = ['GET'])
def get_questions_api():
    reviews = load_questions()
    return jsonify(reviews)

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=False, port=10000)