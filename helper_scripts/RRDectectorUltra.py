# ======= ResRevDetector Ultra =======
import pandas as pd
from collections import Counter
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import itertools
import matplotlib.colors as mcolors


@dataclass
class DetectorConfig:
    """Configuration class for ResReviewDetector parameters"""
    # File paths
    biz_path: str = './data/yelp_academic_dataset_business.json'
    rev_path: str = './data/yelp_academic_dataset_review.json'
    tag_map_path: str = './data/categorized_tags.xlsx'
    neg_path: str = './data/neg.json'
    pos_path: str = './data/pos.json'
    output_dir: str = './data/output/review_batches/'
    
    # Processing parameters
    batch_size: int = 100000
    threshold: float = 0.3
    no_bar: bool = False  
    check_name: bool = False
    
    # Target attributes for restaurant detection
    target_attr: List[str] = field(default_factory=lambda: [
        'RestaurantsDelivery',
        'RestaurantsReservations',
        'RestaurantsTakeOut',
        'RestaurantsGoodForGroups',
        'RestaurantsAttire',
        'Ambience',
        'OutdoorSeating'
    ])
    
    # Name filtering - keywords to exclude from business names
    excluded_name_keywords: List[str] = field(default_factory=lambda: [
        'pub', 'bar', 'smoothies', 'gelato', 'candy', 'ice cream', 'delis',
        'deli', 'smoothie', 'juice bar', 'coffee shop', 'cafe', 'bakery',
        'donut', 'bagel', 'tavern', 'lounge', 'brewery', 'winery', 'distillery'
    ])
    
    # Special cuisines list
    special_cuisines: List[str] = field(default_factory=lambda: [
        "Afghan", "African", "American (New)", "American (Traditional)", "Arabic", "Argentine", "Armenian", 
        "Asian Fusion", "Australian", "Austrian", "Bangladeshi", "Basque", "Belgian", "Brazilian", "British", 
        "Burmese", "Cajun/Creole", "Calabrian", "Cambodian", "Canadian (New)", "Cantonese", "Caribbean", 
        "Chilean", "Chinese", "Colombian", "Cucina campana", "Czech", "Dominican", "Eastern European", 
        "Egyptian", "Ethiopian", "Filipino", "French", "Fuzhou", "German", "Greek", "Hawaiian", "Hainan", 
        "Haitian", "Hakka", "Halal", "Himalayan/Nepalese", "Honduran", "Hong Kong Style Cafe", "Hungarian", 
        "Iberian", "Indian", "Indonesian", "Irish", "Israeli", "Italian", "Japanese", "Japanese Curry", 
        "Korean", "Kosher", "Laotian", "Latin American", "Lebanese", "Mediterranean", "Mexican", 'Trinidadian',
        "Middle Eastern", "Modern European", "Mongolian", "Moroccan", "New Mexican Cuisine", "Nicaraguan", 
        "Pan Asian", "Persian/Iranian", "Peruvian", "Polish", "Portuguese", "Puerto Rican", "Russian", 
        "Salvadoran", "Sardinian", "Scandinavian", "Scottish", "Senegalese", "Serbo Croatian", 'Syrian',
        "Shanghainese", "Sicilian", "Singaporean", "Somali", "South African", "Southern", 'Guamanian', 
        "Spanish", "Sri Lankan", "Szechuan", "Taiwanese", "Tex-Mex", 'Pakistani', 'Oriental', 'Malaysian',
        "Thai", "Turkish", "Tuscan", "Ukrainian", "Uzbek", "Venezuelan", "Vietnamese", "Cuban", 'Georgian'
    ])
    
    # Output parameters
    output_batch_size: int = 100000
    output_prefix: str = "res_revs"
    
    # Visualization parameters
    plot_figsize: Tuple[int, int] = (8, 6)
    plot_cmap: str = 'Blues'


class ResReviewDetector:
    """
    A comprehensive restaurant review detector and processor for Yelp dataset.
    
    This class provides functionality to:
    1. Filter restaurant-related businesses from Yelp data
    2. Validate model performance using confusion matrix
    3. Process and merge reviews with restaurant data
    4. Add cuisine type information
    5. Save processed data in batches
    """
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        """
        Initialize the detector with configuration parameters.
        
        Args:
            config: DetectorConfig instance with all parameters
        """
        self.config = config or DetectorConfig()
        self.tag_dict = None
        self.all_bizs = None
        self.res_bizs = None
        self.all_revs = None
        
    def update_config(self, **kwargs):
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                print(f"Warning: Unknown configuration parameter '{key}'")
    
    def batch_read(self, file_path: str, batch_size: Optional[int] = None):
        """Read data in batches from a JSON file"""
        batch_size = batch_size or self.config.batch_size
        with open(file_path, 'r', encoding='utf-8') as file:
            batch = []
            for i, line in enumerate(file):
                try:
                    data = json.loads(line.strip())
                    batch.append(data)
                    if len(batch) == batch_size:
                        yield batch
                        batch = []
                except json.JSONDecodeError:
                    print(f"Invalid JSON line skipped: {line.strip()}")
            if batch:  
                yield batch
    
    def read_json_in_batch(self, file_path: str, batch_size: Optional[int] = None) -> List[Dict]:
        """Read entire JSON file in batches"""
        batch_size = batch_size or self.config.batch_size
        data = []
        for batch in self.batch_read(file_path=file_path, batch_size=batch_size):
            data.extend(batch)
        return data
    
    def get_tag_dict(self, file_path: Optional[str] = None) -> Dict[str, str]:
        """Load tag mapping from Excel file"""
        file_path = file_path or self.config.tag_map_path
        df = pd.read_excel(file_path)
        return dict(zip(df['Tag'], df['Category']))
    
    def is_res(self, biz: Dict[str, Any]) -> bool:
        """
        Determine if a business is restaurant-related.
        
        ***Logic***
        1) Num of restaurant-related tags > threshold;
        2) Must contain 'Restaurants' tag;
        3) Attribute includes at least one of the target attributes;
        4) If no_bar is True, must not have 'Bars', 'Pubs', 'Delis' and etc. in tags.
        5) Business name must not contain excluded keywords
        """
        # Step 1: Check if any relevant attributes exist
        attributes = biz.get('attributes', {})
        if not isinstance(attributes, dict):
            return False
        attr_list = list(attributes.keys())
        matching_attr = [attr for attr in attr_list if attr in self.config.target_attr]
        if not matching_attr:
            return False
        
        # Step 2: Check categories/tags
        categories = biz.get('categories', '')
        if not isinstance(categories, str):
            return False
        tag_list = [tag.strip() for tag in categories.split(',')]
        category_counter = Counter()
        for tag in tag_list:
            if tag in self.tag_dict:
                category_counter[self.tag_dict[tag]] += 1
        total = sum(category_counter.values())
        if total == 0:
            return False
        restaurant_count = category_counter.get('Restaurant', 0)
        restaurant_ratio = restaurant_count / total
        
        # Step 3: Check for Bar exclusion if no_bar is True
        if self.config.no_bar:
            for tag in tag_list:
                if 'Bars' in tag or 'Pubs' in tag or 'Delis' in tag:
                    return False
        
        # Step 4: Check if any original tag was a "Restaurants" type
        has_restaurants_tag = 'Restaurants' in tag_list
        
        # Step 5: Check business name for excluded keywords
        name = biz.get('name', '').lower()
        if self.config.check_name:
            for keyword in self.config.excluded_name_keywords:
                if keyword.lower() in name:
                    return False
        
        return (restaurant_ratio > self.config.threshold and 
                has_restaurants_tag and 
                len(matching_attr) > 0)
    
    def get_res_biz(self, bizs: List[Dict]) -> List[Dict]:
        """Filter restaurant businesses from business list"""
        return [biz for biz in bizs if self.is_res(biz)]
    
    def create_confusion_matrix(self, tp: int, fp: int, fn: int, tn: int):
        """Create and display confusion matrix with metrics"""
        cm = np.array([[tp, fn], [fp, tn]])
        
        # Calculate metrics
        accuracy = (tp + tn) / (tp + fp + fn + tn)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
        # Create visualization
        plt.figure(figsize=self.config.plot_figsize)
        sns.heatmap(cm, annot=True, fmt='d', cmap=self.config.plot_cmap, 
                    xticklabels=['Predicted Positive', 'Predicted Negative'],
                    yticklabels=['Actual Positive', 'Actual Negative'])
        plt.title('Confusion Matrix')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        
        # Print metrics
        print(f"Accuracy: {accuracy:.3f}")
        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")
        print(f"Specificity: {specificity:.3f}")
        print(f"F1-Score: {f1_score:.3f}")
        plt.show()
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'specificity': specificity,
            'f1_score': f1_score
        }
    
    def validate_model(self, all_bizs: Optional[List[Dict]] = None) -> Dict[str, float]:
        """Validate model performance using positive and negative samples"""
        if all_bizs is None:
            all_bizs = self.all_bizs

        # Load validation data
        with open(self.config.neg_path, 'r', encoding='utf-8') as n:
            N = json.load(n)
        with open(self.config.pos_path, 'r', encoding='utf-8') as p:
            P = json.load(p)
        
        # Get business IDs
        N_biz_ids = set(biz['business_id'] for biz in N)
        P_biz_ids = set(biz['business_id'] for biz in P)
        
        # Filter validation businesses
        N_val = [biz for biz in all_bizs if biz['business_id'] in N_biz_ids]
        P_val = [biz for biz in all_bizs if biz['business_id'] in P_biz_ids]
        
        # Calculate confusion matrix values
        TP = len(self.get_res_biz(P_val))
        FP = len(self.get_res_biz(N_val))
        FN = len(P) - TP
        TN = len(N) - FP
        
        return self.create_confusion_matrix(TP, FP, FN, TN)
    
    def get_cuisine(self, bizs: List[Dict]) -> List[Dict]:
        """Add cuisine type information to businesses"""
        cuisine_bizs = []
        for biz in bizs:
            categories_str = biz.get('categories')  
            if not categories_str:  
                continue
            categories = [cat.strip() for cat in categories_str.split(",")]
            matching_tags = [tag for tag in categories if tag in self.config.special_cuisines]
            if len(matching_tags) == 1: 
                biz['cuisine_type'] = matching_tags[0]
            elif len(matching_tags) == 0:
                biz['cuisine_type'] = 'General'
            else:
                biz['cuisine_type'] = 'Multiple'
            cuisine_bizs.append(biz)
        return cuisine_bizs
    
    def merge_rev_res_batch(self, revs: List[Dict], res_bizs: List[Dict], 
                           batch_size: Optional[int] = None) -> List[Dict]:
        """Merge reviews with restaurant business data"""
        batch_size = batch_size or self.config.batch_size
        biz_dict = {biz['business_id']: biz for biz in res_bizs}
        total = len(revs)
        merged_list = []
        for i in range(0, total, batch_size):
            print(f"Processing batch {i // batch_size + 1}... ({i} to {min(i + batch_size, total)})")
            batch = revs[i:i + batch_size]
            for rev in batch:
                biz_id = rev['business_id']
                if biz_id in biz_dict:
                    biz = biz_dict[biz_id]
                    merged_item = {
                        'business_id': biz_id,
                        'user_id': rev['user_id'],
                        'review_id': rev['review_id'],
                        'review_text': rev['text'],
                        'review_stars': rev['stars'],
                        'cuisine_type': biz['cuisine_type'],
                        'restaurant_name': biz['name'],
                        'tags': biz['categories'],
                        'attributes': biz['attributes'],
                        'state': biz['state'],
                        'city': biz['city'],
                        'date': rev['date']
                    }
                    merged_list.append(merged_item)
        return merged_list
    
    def save_json_in_batches(self, data: List[Dict], output_dir: Optional[str] = None, 
                            batch_size: Optional[int] = None, prefix: Optional[str] = None):
        """Save data into multiple JSON files in batches"""
        output_dir = output_dir or self.config.output_dir
        batch_size = batch_size or self.config.output_batch_size
        prefix = prefix or self.config.output_prefix
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        total = len(data)
        print(f"Total records: {total}")
        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            file_index = i // batch_size + 1
            filename = f"{prefix}_{file_index}.json"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(batch, f, indent=2, ensure_ascii=False)
            
            print(f"Saved {len(batch)} records to {file_path}")
    
    def load_data(self):
        """Load all necessary data files"""
        print("Loading business data...")
        self.all_bizs = self.read_json_in_batch(self.config.biz_path)
        
        print("Loading tag dictionary...")
        self.tag_dict = self.get_tag_dict()
        
        print("Loading review data...")
        self.all_revs = self.read_json_in_batch(self.config.rev_path)
        
        print("Data loading completed!")
    
    def process_restaurants(self):
        """Process restaurant data with cuisine information"""
        if self.all_bizs is None or self.tag_dict is None:
            raise ValueError("Data not loaded. Please call load_data() first.")
        
        print("Filtering restaurant businesses...")
        self.res_bizs = self.get_res_biz(self.all_bizs)
        
        print("Adding cuisine type information...")
        self.res_bizs = self.get_cuisine(self.res_bizs)
        
        print(f"Found {len(self.res_bizs)} restaurant businesses")
        return self.res_bizs
    
    def get_performance_table(self, param_grid: Dict[str, List[Any]], 
                          json_path: str = "./data/performance_table.json",
                          table_image_path: str = "./data/performance_table.png") -> List[Dict[str, Any]]:
        """
        Test all parameter combinations in the param_grid and return performance results for each.
        Also saves results to a JSON file and generates a performance table image with metrics as rows and method_ids as columns.

        Args:
            param_grid: Dictionary with parameter names as keys and lists of values to try.
            json_path: Path to save JSON file.
            table_image_path: Path to save performance table image.

        Returns:
            List of dictionaries containing Method_ID, Parameters, and evaluation metrics.
            """
        if self.all_bizs is None or self.tag_dict is None:
            raise ValueError("Data not loaded. Please call load_data() first.")

        print(f"Parameter grid: {param_grid}")
        results = []

        # Prepare for grid search
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        total_combinations = len(list(itertools.product(*param_values)))
        print(f"Testing {total_combinations} parameter combinations...\n")
        for i, param_combo in enumerate(itertools.product(*param_values)):
            current_params = dict(zip(param_names, param_combo))
            method_id = i + 1
            print(f"[{i+1}/{total_combinations}] Testing: {current_params}")

        # Backup original parameters
            original_params = {}
            for param_name in param_names:
                original_params[param_name] = getattr(self.config, param_name)
                setattr(self.config, param_name, current_params[param_name])
            try:
                plt.ioff()
                metrics = self.validate_model()
                plt.close('all')
                result = {
                    "Method_ID": method_id,
                    "Parameters": current_params.copy(),
                    "Accuracy": round(metrics.get("accuracy", -1), 3),
                    "Precision": round(metrics.get("precision", -1), 3),
                    "Recall": round(metrics.get("recall", -1), 3),
                    "Specificity": round(metrics.get("specificity", -1), 3),
                    "F1-Score": round(metrics.get("f1_score", -1), 3),
                }
                results.append(result)
                print(f"Result: {result}\n")
            except Exception as e:
                print(f"Error with parameters {current_params}: {e}")
                result = {
                    "Method_ID": method_id,
                    "Parameters": current_params.copy(),
                    "Accuracy": -1,
                    "Precision": -1,
                    "Recall": -1,
                    "Specificity": -1,
                    "F1-Score": -1,
                    "error": str(e)
                }
                results.append(result)
            finally:
                # Restore original config values
                for param_name in param_names:
                    setattr(self.config, param_name, original_params[param_name])
        plt.ion()  # Turn interactive plotting back on
        print("=" * 60)
        print("PERFORMANCE TABLE GENERATED!")
        print(f"Total methods evaluated: {total_combinations}")
        print("=" * 60)

        # Save results to JSON
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Performance table saved to {json_path}")

        # Generate performance table (metrics as rows, method_ids as columns)
        df = pd.DataFrame(results)
        metrics_columns = ["Accuracy", "Precision", "Recall", "Specificity", "F1-Score"]
        performance_df = df.set_index("Method_ID")[metrics_columns].T  

        # Plot as image (black and white)
        plt.figure(figsize=(18, 6))
        sns.set_theme(style="whitegrid")
        custom_cmap = mcolors.LinearSegmentedColormap.from_list(
            "salmon_white", 
            ["white", "lightsalmon"], 
            N=256
            )
        ax = sns.heatmap(performance_df, annot=True, cmap=custom_cmap, fmt=".3f", linewidths=.5, linecolor='black', cbar=False) 
        ax.xaxis.set_ticks_position('top')
        ax.xaxis.label.set_visible(False)
        ax.yaxis.label.set_visible(False)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(table_image_path, dpi=200, bbox_inches='tight')
        plt.close()
        print(f"Performance table image saved to {table_image_path}")
        
        return results
        
    def optimize_parameters(self, param_grid: Dict[str, List[Any]], 
                           metric: str = 'f1_score', verbose: bool = True) -> Dict[str, Any]:
        """
        Find the best parameters using grid search on validation data.
        
        Args:
            param_grid: Dictionary with parameter names as keys and lists of values to try
            metric: Metric to optimize ('f1_score', 'accuracy', 'precision', 'recall')
            verbose: Whether to print progress
            
        Returns:
            Dictionary with best parameters and their performance
        """
        if self.all_bizs is None or self.tag_dict is None:
            raise ValueError("Data not loaded. Please call load_data() first.")
        
        print(f"Starting parameter optimization using {metric}...")
        print(f"Parameter grid: {param_grid}")
        best_score = -1
        best_params = {}
        best_metrics = {}
        results = []
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        total_combinations = len(list(itertools.product(*param_values)))
        print(f"Testing {total_combinations} parameter combinations...\n")
        for i, param_combo in enumerate(itertools.product(*param_values)):
            # Create parameter dict
            current_params = dict(zip(param_names, param_combo))
            if verbose:
                print(f"[{i+1}/{total_combinations}] Testing: {current_params}")
            # Update configuration
            original_params = {}
            for param_name, param_value in current_params.items():
                original_params[param_name] = getattr(self.config, param_name)
                setattr(self.config, param_name, param_value)
            try:
                # Validate with current parameters (suppress plot)
                plt.ioff()  # Turn off interactive plotting
                metrics = self.validate_model()
                plt.close('all')  # Close any plots
                current_score = metrics[metric]
                result = {
                    'params': current_params.copy(),
                    'metrics': metrics,
                    'score': current_score
                }
                results.append(result)
                if verbose:
                    print(f"{metric}: {current_score:.4f}")
                # Update best parameters
                if current_score > best_score:
                    best_score = current_score
                    best_params = current_params.copy()
                    best_metrics = metrics.copy()
                    if verbose:
                        print("*** New best score! ***")
            except Exception as e:
                print(f"Error with parameters {current_params}: {e}")
                result = {
                    'params': current_params.copy(),
                    'metrics': None,
                    'score': -1,
                    'error': str(e)
                }
                results.append(result)
            # Restore original parameters
            for param_name, original_value in original_params.items():
                setattr(self.config, param_name, original_value)
            if verbose:
                print()
        
        # Set best parameters
        for param_name, param_value in best_params.items():
            setattr(self.config, param_name, param_value)
        plt.ion()  # Turn interactive plotting back on
        optimization_results = {
            'best_params': best_params,
            'best_metrics': best_metrics,
            'best_score': best_score,
            'all_results': results
        }
        print("=" * 60)
        print("OPTIMIZATION COMPLETE!")
        print(f"Best {metric}: {best_score:.4f}")
        print(f"Best parameters: {best_params}")
        print("=" * 60)

        return optimization_results
    
    def quick_parameter_tune(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Quick parameter tuning with common parameter ranges.
        
        Args:
            verbose: Whether to print progress
            
        Returns:
            Dictionary with best parameters and their performance
        """
        # Define common parameter ranges
        param_grid = {
            'threshold': [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            'target_attr': [
                ['RestaurantsDelivery', 'RestaurantsReservations', 'RestaurantsTakeOut'],
                
                ['RestaurantsDelivery', 'RestaurantsReservations', 'RestaurantsTakeOut', 
                 'RestaurantsGoodForGroups', 'RestaurantsAttire'],
                
                ['RestaurantsDelivery', 'RestaurantsReservations', 'RestaurantsTakeOut',
                 'RestaurantsGoodForGroups', 'RestaurantsAttire', 'Ambience', 'OutdoorSeating']
            ]
        }
        return self.optimize_parameters(param_grid, verbose=verbose)
    
    def show_optimization_summary(self, optimization_results: Dict[str, Any], top_n: int = 5):
        """
        Display a summary of optimization results.
        
        Args:
            optimization_results: Results from optimize_parameters()
            top_n: Number of top results to show
        """
        results = optimization_results['all_results']

        # Filter out failed results
        valid_results = [r for r in results if r['score'] > -1]
        if not valid_results:
            print("No valid results found!")
            return
        
        # Sort by score
        valid_results.sort(key=lambda x: x['score'], reverse=True)
        print(f"\nTop {min(top_n, len(valid_results))} Parameter Combinations:")
        print("-" * 80)
        for i, result in enumerate(valid_results[:top_n]):
            print(f"\n{i+1}. Score: {result['score']:.4f}")
            print(f"Parameters: {result['params']}")
            print(f"Metrics: Accuracy={result['metrics']['accuracy']:.3f}, "
                  f"Precision={result['metrics']['precision']:.3f}, "
                  f"Recall={result['metrics']['recall']:.3f}, "
                  f"F1={result['metrics']['f1_score']:.3f}")
            
    def get_fp_fn_with_reviews(self, all_bizs: Optional[List[Dict]] = None, 
                                    all_revs: Optional[List[Dict]] = None) -> Dict[str, List[Dict]]:
        """
        Optimized version to get false positives and false negatives with their business info and reviews.
        """
        print("Starting FP/FN analysis...")
    
        if all_bizs is None:
            all_bizs = self.all_bizs
        if all_revs is None:
            all_revs = self.all_revs

        # Load validation data
        print("Loading validation data...")
        with open(self.config.neg_path, 'r', encoding='utf-8') as n:
            N = json.load(n)  # Should NOT be restaurants
        with open(self.config.pos_path, 'r', encoding='utf-8') as p:
            P = json.load(p)  # Should BE restaurants

        # Get business IDs
        N_biz_ids = set(biz['business_id'] for biz in N)
        P_biz_ids = set(biz['business_id'] for biz in P)
    
        print(f"Negative validation set: {len(N_biz_ids)} businesses")
        print(f"Positive validation set: {len(P_biz_ids)} businesses")

        # Filter validation businesses
        print("Filtering validation businesses...")
        N_val = [biz for biz in all_bizs if biz['business_id'] in N_biz_ids]
        P_val = [biz for biz in all_bizs if biz['business_id'] in P_biz_ids]
    
        print(f"Found {len(N_val)} negative validation businesses")
        print(f"Found {len(P_val)} positive validation businesses")

        # Get false positives and false negatives
        print("Identifying false positives...")
        fp_businesses = []
        for i, biz in enumerate(N_val):
            if i % 100 == 0:
                print(f"Processing negative business {i+1}/{len(N_val)}")
            if self.is_res(biz):
                fp_businesses.append(biz)
    
        print("Identifying false negatives...")
        fn_businesses = []
        for i, biz in enumerate(P_val):
            if i % 100 == 0:
                print(f"Processing positive business {i+1}/{len(P_val)}")
            if not self.is_res(biz):
                fn_businesses.append(biz)
    
        print(f"Found {len(fp_businesses)} false positives")
        print(f"Found {len(fn_businesses)} false negatives")

        # Get the business IDs we need reviews for
        target_biz_ids = set()
        for biz in fp_businesses + fn_businesses:
            target_biz_ids.add(biz['business_id'])
    
        print(f"Looking for reviews for {len(target_biz_ids)} businesses...")

        # Create review lookup ONLY for the businesses we need
        review_lookup = {}
        total_reviews = len(all_revs)
        batch_size = 100000
    
        for i in range(0, total_reviews, batch_size):
            batch_end = min(i + batch_size, total_reviews)
            print(f"Processing review batch {i//batch_size + 1}: reviews {i+1} to {batch_end}")
        
            batch_reviews = all_revs[i:batch_end]
            for review in batch_reviews:
                biz_id = review['business_id']
                if biz_id in target_biz_ids:  # Only process reviews for businesses we care about
                    if biz_id not in review_lookup:
                        review_lookup[biz_id] = []
                    if len(review_lookup[biz_id]) < 10:
                        review_lookup[biz_id].append({
                            'review_id': review['review_id'],
                            'text': review['text']
                            })

        print(f"Found reviews for {len(review_lookup)} businesses")

        # Build FP data
        print("Building false positive data...")
        false_positives = []
        for biz in fp_businesses:
            biz_id = biz['business_id']
            fp_data = {
                'business_id': biz_id,
                'name': biz.get('name', ''),
                'categories': biz.get('categories', ''),
                'attributes': biz.get('attributes', {}),
                'reviews': review_lookup.get(biz_id, [])
                }
            false_positives.append(fp_data)

        # Build FN data
        print("Building false negative data...")
        false_negatives = []
        for biz in fn_businesses:
            biz_id = biz['business_id']
            fn_data = {
                'business_id': biz_id,
                'name': biz.get('name', ''),
                'categories': biz.get('categories', ''),
                'attributes': biz.get('attributes', {}),
                'reviews': review_lookup.get(biz_id, [])
                }
            false_negatives.append(fn_data)

        print("FP/FN analysis complete!")
        return {
            'false_positives': false_positives,
            'false_negatives': false_negatives
        }
    
    def save_fp_fn(self, output_path: str = './data/fp_fn_validation.json'):
        """Save FP/FN data from validation sets only"""
        fp_fn_data = self.get_fp_fn_with_reviews()
    
        result = {
            'summary': {
                'false_positives_count': len(fp_fn_data['false_positives']),
                'false_negatives_count': len(fp_fn_data['false_negatives']),
                'total_fp_reviews': sum(len(biz['reviews']) for biz in fp_fn_data['false_positives']),
                'total_fn_reviews': sum(len(biz['reviews']) for biz in fp_fn_data['false_negatives'])
                },
            'data': fp_fn_data
            }
        
        print("Saving to file...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
        print(f"FP/FN validation data saved to {output_path}")
        print(f"False Positives: {result['summary']['false_positives_count']} businesses")
        print(f"False Negatives: {result['summary']['false_negatives_count']} businesses")
    
        return result
    
    def run_optimized_pipeline(self, param_grid: Optional[Dict[str, List[Any]]] = None, metric: str = 'f1_score', verbose: bool = True):
        """
        Execute the complete pipeline with parameter optimization.
        
        Args:
            param_grid: Custom parameter grid (None for quick tune)
            metric: Metric to optimize
            verbose: Whether to print progress
            
        Returns:
            Tuple of (processed_reviews, optimization_results)
        """
        # Load data
        self.load_data()
        
        # Optimize parameters
        if param_grid is None:
            print("Running quick parameter tuning...")
            optimization_results = self.quick_parameter_tune(verbose=verbose)
        else:
            print("Running custom parameter optimization...")
            optimization_results = self.optimize_parameters(param_grid, metric, verbose)
        
        # Show final validation with best parameters
        print("\nFinal validation with best parameters:")
        final_metrics = self.validate_model()
        
        # Process restaurants
        self.process_restaurants()
        
        # Merge reviews with restaurant data
        print("Merging reviews with restaurant data...")
        res_revs = self.merge_rev_res_batch(self.all_revs, self.res_bizs)
        
        # Save results
        print("Saving processed data...")
        self.save_json_in_batches(res_revs)
        
        print("Optimized pipeline completed successfully!")
        return res_revs, optimization_results
    
    def run_full_pipeline(self):
        """Execute the complete processing pipeline without optimization"""
        # Load data
        self.load_data()
        
        # Validate model
        print("Validating model performance...")
        metrics = self.validate_model()
        
        # Process restaurants
        self.process_restaurants()
        
        # Merge reviews with restaurant data
        print("Merging reviews with restaurant data...")
        res_revs = self.merge_rev_res_batch(self.all_revs, self.res_bizs)
        
        # Save results
        print("Saving processed data...")
        self.save_json_in_batches(res_revs)
        
        print("Pipeline completed successfully!")
        return res_revs, metrics


if __name__ == "__main__":
    '''
    # ===== This part is for parameter tunning =====
    # Create configuration
    config = DetectorConfig(
        batch_size=100000,
        output_dir='./data/output/review_batches/'
    )
    
    # Initialize detector
    detector = ResReviewDetector(config)
    detector.load_data()
    
    # Parameter tuning
    custom_param_grid = {
    'threshold': [0.3, 0.4, 0.5, 0.6, 0.7],
    'no_bar': [True, False],
    'target_attr': [
        ['ByAppointmentOnly', 'BusinessAcceptsCreditCards', 'BikeParking', 'RestaurantsPriceRange2', 'CoatCheck', 
          'RestaurantsTakeOut', 'RestaurantsDelivery', 'Caters', 'WiFi', 'BusinessParking', 'WheelchairAccessible', 
          'HappyHour', 'OutdoorSeating', 'HasTV', 'RestaurantsReservations', 'DogsAllowed', 'Alcohol', 'GoodForKids', 
          'RestaurantsAttire', 'Ambience', 'RestaurantsTableService', 'RestaurantsGoodForGroups', 'DriveThru', 'NoiseLevel', 
          'GoodForMeal', 'BusinessAcceptsBitcoin', 'Smoking', 'Music', 'GoodForDancing', 'AcceptsInsurance', 'BestNights', 
          'BYOB', 'Corkage', 'BYOBCorkage', 'HairSpecializesIn', 'Open24Hours', 'RestaurantsCounterService', 
          'AgesAllowed', 'DietaryRestrictions'],
        
        ['RestaurantsDelivery', 'RestaurantsReservations', 'RestaurantsTakeOut', 
         'RestaurantsGoodForGroups','RestaurantsAttire']
        ],
    'check_name': [True, False]
    }
    all_results = detector.get_performance_table(param_grid=custom_param_grid)
    
    """
    optimization_results = detector.optimize_parameters(
        param_grid=custom_param_grid,
        metric='precision',
        verbose=True
    )
    detector.show_optimization_summary(optimization_results)
    """
    '''

    # ===== Use The Most Fit One =====
    config_1 = DetectorConfig(
        threshold=0.7,  
        no_bar=False,     
        target_attr=['RestaurantsDelivery', 'RestaurantsReservations', 'RestaurantsTakeOut', 'RestaurantsGoodForGroups','RestaurantsAttire'],
        batch_size=100000,
        check_name=True,
        output_dir='./data/output/review_batches/recheck'
    )
    detector = ResReviewDetector(config_1)
    detector.load_data()
    detector.process_restaurants()
    res_revs = detector.merge_rev_res_batch(detector.all_revs, detector.res_bizs)
    detector.save_json_in_batches(res_revs)


    

