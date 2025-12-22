import json, random
def get_random_reviews_from_file(file: str, reviews: int) -> list:
    reviews_list = None
    random_reviews = []
    with open(f"data\\output\\review_batches\\recheck\\{file}", encoding='utf-8') as json_file:
        reviews_list = json.load(json_file)
        if not reviews_list:
            return []
    print(f"getting reviews from {file}")
    random_indexes = random.sample(range(len(reviews_list)), reviews)
    for i in random_indexes:
        review_id = reviews_list[i]["review_id"]
        review_text = reviews_list[i]["review_text"]
        data = {"review_id": review_id,
                "review_text": review_text}
        random_reviews.append(data)
    print("Done!")
    return random_reviews

def create_json_file(num_reviews: int):
    final_json = []
    for i in range(23):
        json_one_file = get_random_reviews_from_file(f"res_revs_{i+1}.json", num_reviews//23)
        for review in json_one_file:
            final_json.append(review)
    print("creating final json file...")
    with open("random_reviews.json", "w", encoding='utf-8') as file:
        json.dump(final_json, file, indent=4)
    print("Done!!")


if __name__ == "__main__":
    create_json_file(1500)