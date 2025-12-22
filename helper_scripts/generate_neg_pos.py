import json
import os
import random

# CONFIGURATION
# Matches the path in your DetectorConfig
SOURCE_FILE = 'yelp_academic_dataset_business.json'
POS_OUTPUT = './data/pos.json'
NEG_OUTPUT = './data/neg.json'
SAMPLE_SIZE = 5000  # "As long as possible" - 5000 is plenty for statistical significance

def generate_truth_sets():
    print(f"Reading from {SOURCE_FILE}...")
    
    positives = []
    negatives = []
    
    # 1. Define Strict Rules for "Ground Truth"
    # We use very strict rules here to ensure our validation set is 100% accurate
    # so we can test the fuzzier logic of the main detector.
    
    # Non-Restaurant Categories (High Confidence)
    negative_keywords = [
        'Automotive', 'Health & Medical', 'Beauty & Spas', 'Home Services', 
        'Financial Services', 'Real Estate', 'Public Services & Government',
        'Pets', 'Active Life', 'Mass Media', 'Education', 'Religious Organizations'
    ]
    
    try:
        with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    biz = json.loads(line)
                    cats_str = biz.get('categories', '')
                    
                    if not cats_str:
                        continue
                        
                    cats = [c.strip() for c in cats_str.split(',')]
                    
                    # --- LOGIC FOR POSITIVES (Definite Restaurants) ---
                    # Must have 'Restaurants' tag explicitly
                    # Must NOT have ambiguous tags like 'Gas Stations' or 'Grocery'
                    if ('Restaurants' in cats and 
                        'Gas Stations' not in cats and 
                        'Convenience Stores' not in cats and 
                        'Grocery' not in cats):
                        positives.append({
                            'business_id': biz['business_id'],
                            'name': biz['name'],
                            'categories': cats_str
                        })
                        
                    # --- LOGIC FOR NEGATIVES (Definite Non-Restaurants) ---
                    # Must NOT have 'Restaurants' or 'Food' tags
                    # Must have one of the clear non-food keywords
                    elif ('Restaurants' not in cats and 
                          'Food' not in cats and 
                          any(k in cats for k in negative_keywords)):
                        negatives.append({
                            'business_id': biz['business_id'],
                            'name': biz['name'],
                            'categories': cats_str
                        })
                        
                except json.JSONDecodeError:
                    continue
                    
    except FileNotFoundError:
        print(f"Error: Could not find source file at {SOURCE_FILE}")
        print("Please check your file path.")
        return

    # 2. Shuffle and Slice to create random samples
    random.shuffle(positives)
    random.shuffle(negatives)
    
    final_pos = positives[:SAMPLE_SIZE]
    final_neg = negatives[:SAMPLE_SIZE]
    
    print(f"Found {len(positives)} total potential positives.")
    print(f"Found {len(negatives)} total potential negatives.")
    print(f"-" * 30)
    
    # 3. Save Files
    os.makedirs(os.path.dirname(POS_OUTPUT), exist_ok=True)
    
    with open(POS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_pos, f, indent=2)
    print(f"Successfully created {POS_OUTPUT} with {len(final_pos)} entries.")
    
    with open(NEG_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_neg, f, indent=2)
    print(f"Successfully created {NEG_OUTPUT} with {len(final_neg)} entries.")

if __name__ == "__main__":
    generate_truth_sets()