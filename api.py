from flask import Flask, jsonify
from json import load
import json
app = Flask(__name__)

def load_questions():
    """Place holder method to lead questions into json string. 
       TODO: Must take care of dynamically loading random questions from yelp file on to reviews json object
    """
    reviews = "[]"
    with open("placeholder_questions.json") as json_file: #Place holder
        reviews = load(json_file)
    return reviews

@app.route('/questions', methods = ['GET'])
def get_questions_api():
    reviews = load_questions()
    return jsonify(reviews)

if __name__ == '__main__':
    app.run(debug=True, port=10000)