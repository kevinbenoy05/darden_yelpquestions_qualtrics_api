from flask import Flask, jsonify
from json import load
import pandas as pd
import random
import matplotlib.pyplot as plt


app = Flask(__name__)

control = "The restaurant is right next to the central train station, so it was very easy to find. There was plenty of parking in the lot across the street. Our server greeted us immediately and checked in regularly throughout the meal. The dining area was spotless — clean tables, clean floors, clean restrooms. The food was fresh and well-prepared. The menu had a solid variety of options to choose from. Prices were fair for what we received."
with open("random_reviews.json", encoding='utf-8') as json_file:
    reviews_list = load(json_file)

review_ids = ['777jGHeZgwWgtJNBVGuxDw', 'nV4IjpWQX8W0s1tnKkbMJA', 'JJ1yjqdrLbsOMoE9xkrvzA', '1JfzyhvkzM-5Z5HAPh1Vhw', '7BaQ3vFNiIEmw0Ge9cswVQ', 'pS7Rq-Cxfr4BwIwrRnwl5A', 'JRclmKL3sRLessQFxz7R_g', 'JGnrRAo9Jes26kDWUJH7DQ', 'AIUc_ztbMhngLxQR8tsV-A', 'uLLu-cULBUXnLcT3R7748w', 'JBFXCDLofJ6f2R1LXRZL8g', 'woJei0BMyMjWYoEQPtKeLQ', '9xRiPdzuEJQnjoY3968iBw', 'IzNHZTMCgSlY03ohM3ZBhw', '0pbvCdlAWj_93qilWOHvnw', 'UTey0Sx96JjH32TgHIYM6w', '8IigYBgu8yynd8PGeUFHyg', 'kVqDrQLdQ1PjVVEIsTLUkg', 'sTnt45-kymn5Y1sUv556xg', 'lJ20Z-Xqps_idKDkrhJhuA', 'X4shFqRTjdsAFWRD4EkuyA', 'qjj3bqMbPXqUWy1jOi39pQ', 'UcLSNTElLt1cR-5I7_CQ0w', 'K487me6z_8P_6UPS7bCrIQ', 'NWr_69z4q0I7HzHUJ4fvVA', 'RyDue_eiTCbrsnb2S0BmNA', '-Ye2fcS1Jr1kieggVPZVkQ', 'z3s67k5ORelHfboZXK9wUw', 'TiTaLIW9YfLVIwznT9yEjw', 'J532l6SKfuGRaNguAg4xmw', 'AdHnRvQpXKNqACJXuoGu0A', 'yhiU5IhayhcCVJfNEFvC_g', 'GgVynHNvYizQ0_aj4HsgvA', 'lYY2opv1vhg0Bgh6qP15KQ', 'YOI9YVgBEdYcTmNpB4AbpQ', 'GUbAYQDzd8LRbCsQJNmLbA', 'TjF9p2xPZzbULGrQ-YEZ9A', '5I7ME5ApnfEmPt87Aw_nPQ', 'J2kEn0v1L_NtE9cqHkw_dA', 'hjmr174zvhLaGTAYt7HFlQ', 'FmA4PRS8yaxGxGetQUa4_w', 'qv_z53hWYkEkC5QP_GLAyA', 'cShxIjrNlpuEAEgWyorlpw', 'QIYjbMU3XsD5tkGhPZAJlw', 'egvfu_89QeJ-cf2NakR1pw', 'p9JURLnoKzKYBOFd87Y8bg', 'y1lM8aGTq49NFwDe3rqoLQ']
reviews_df = pd.DataFrame(reviews_list) 
reviews_df = reviews_df[reviews_df['review_id'].isin(review_ids)]
review_counts_df = reviews_df[['review_id']].drop_duplicates().copy()
review_counts_df['review_count'] = 2
review_counts_df.loc[
    review_counts_df['review_id'] == '777jGHeZgwWgtJNBVGuxDw',
    'review_count'
] = 3  # Only one with 3 reviews

        

def load_questions():
    selected_ids = []
    eligible_ids = review_counts_df.loc[review_counts_df['review_count'] < 5, 'review_id']
    if len(eligible_ids) < 5:
        remaining_needed = 5 - len(eligible_ids)
        ineligible_ids = review_counts_df.loc[review_counts_df['review_count'] >= 5, 'review_id']
        selected_ids = eligible_ids.tolist() + ineligible_ids.sample(n=remaining_needed, replace=False).tolist()
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