from flask import Flask, jsonify
from json import load
import pandas as pd
import random


app = Flask(__name__)

control = "The restaurant is right next to the central train station, so it was very easy to find. There was plenty of parking in the lot across the street. We hadn't made a reservation, but we were seated within two minutes of arriving. Our server greeted us immediately and checked in regularly throughout the meal. The dining area was spotless — clean tables, clean floors, clean restrooms. The food was fresh and well-prepared. The menu had a solid variety of options to choose from. Prices were fair for what we received."
with open("random_reviews.json", encoding='utf-8') as json_file:
        reviews_list = load(json_file)

reviews_df = pd.DataFrame(reviews_list)
review_counts_df = reviews_df[['review_id']].drop_duplicates().copy()
review_counts_df['review_count'] = 0
        

def load_questions():
    selected_ids = []
    eligible_ids = review_counts_df.loc[review_counts_df['review_count'] < 5, 'review_id']
    if len(eligible_ids) < 5:
        selected_ids = reviews_df['review_id'].sample(n=5, replace=False).tolist()
    else:
        selected_ids = eligible_ids.sample(n=5, replace=False).tolist()
    review_counts_df.loc[review_counts_df['review_id'].isin(selected_ids), 'review_count'] += 1
    reviews = (
        reviews_df.set_index('review_id')
        .loc[selected_ids]
        .reset_index()
        .to_dict(orient='records')
    )
    control_review = {
        'review_id': 'control',
        'review_text': control
    }
    reviews.insert(random.randint(0, len(reviews)), control_review)
    return reviews

@app.route('/questions', methods = ['GET'])
def get_questions_api():
    reviews = load_questions()
    return jsonify(reviews)

@app.route('/health')
def health_check():
    return "OK", 200


if __name__ == "__main__":
    app.run()