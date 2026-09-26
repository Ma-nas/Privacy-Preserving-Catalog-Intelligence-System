from typing import Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# High quality dataset for top catalog verticals
TRAINING_DATA = [
    # Electronics
    ("Apple iPhone 15 Pro Max 256GB Titanium 5G Smartphone", "Electronics > Mobile Phones"),
    ("Samsung Galaxy S24 Ultra Android AI Smartphone OLED 512GB", "Electronics > Mobile Phones"),
    ("Google Pixel 8 Pro Unlocked Android Smartphone", "Electronics > Mobile Phones"),
    ("Sony WH-1000XM5 Wireless Noise Canceling Over-Ear Headphones", "Electronics > Audio & Headphones"),
    ("Bose QuietComfort 45 Bluetooth Wireless Noise Cancelling Headphones", "Electronics > Audio & Headphones"),
    ("Apple AirPods Pro 2nd Gen Wireless Earbuds with MagSafe", "Electronics > Audio & Headphones"),
    ("Dell XPS 15 Laptop Intel Core i7 32GB RAM SSD NVIDIA RTX", "Electronics > Computers & Laptops"),
    ("Apple MacBook Pro 16 M3 Max 36GB Unified Memory", "Electronics > Computers & Laptops"),
    ("Lenovo ThinkPad X1 Carbon Gen 11 Ultrabook", "Electronics > Computers & Laptops"),
    ("Logitech MX Master 3S Wireless Performance Mouse", "Electronics > Computer Accessories"),
    ("Mechanical Gaming Keyboard RGB Backlit USB", "Electronics > Computer Accessories"),

    # Fashion
    ("Men's Classic Slim-Fit 100% Organic Cotton T-Shirt", "Fashion > Men's Clothing"),
    ("Men's Casual Button Down Oxford Cotton Shirt", "Fashion > Men's Clothing"),
    ("Women's High-Waisted Stretch Denim Jeans Skinny Fit", "Fashion > Women's Clothing"),
    ("Women's Summer Floral Print Wrap Midi Dress", "Fashion > Women's Clothing"),
    ("Nike Air Zoom Pegasus 40 Men's Road Running Shoes", "Fashion > Footwear & Shoes"),
    ("Adidas Originals Superstar Classic Leather Sneakers", "Fashion > Footwear & Shoes"),
    ("Waterproof Winter Parka Jacket with Faux Fur Hood", "Fashion > Outerwear & Jackets"),
    ("Genuine Italian Leather Bifold Wallet with RFID Blocking", "Fashion > Accessories"),

    # Home & Kitchen
    ("KitchenAid Artisan Series 5-Quart Stand Mixer", "Home & Kitchen > Kitchen Appliances"),
    ("Ninja Professional Countertop Blender 1000 Watt", "Home & Kitchen > Kitchen Appliances"),
    ("Instant Pot Duo 7-in-1 Electric Pressure Cooker", "Home & Kitchen > Kitchen Appliances"),
    ("Nonstick Hard-Anodized Cookware Set 10-Piece Pots and Pans", "Home & Kitchen > Cookware"),
    ("Cast Iron Skillet Pre-Seasoned Frying Pan 12-inch", "Home & Kitchen > Cookware"),
    ("Memory Foam Queen Bed Pillow Ergonomic Cervical Support", "Home & Kitchen > Bedding"),
    ("Stainless Steel French Press Coffee Maker 34 Ounce", "Home & Kitchen > Kitchen Utensils"),

    # Sports & Outdoors
    ("Adjustable Dumbbell Set 5 to 52.5 lbs with Storage Rack", "Sports & Outdoors > Exercise & Fitness"),
    ("Thick Non-Slip Yoga Mat with Carrying Strap Eco Friendly", "Sports & Outdoors > Exercise & Fitness"),
    ("Resistance Exercise Bands Set for Strength Training", "Sports & Outdoors > Exercise & Fitness"),
    ("Coleman Sundome 4-Person Camping Tent Waterproof", "Sports & Outdoors > Camping & Hiking"),
    ("Hydro Flask Wide Mouth Straw Lid Insulated Water Bottle", "Sports & Outdoors > Outdoor Recreation"),

    # Books & Stationery
    ("Atomic Habits: An Easy & Proven Way to Build Good Habits Hardcover", "Books & Stationery > Self-Help"),
    ("Clean Code: A Handbook of Agile Software Craftsmanship Paperback", "Books & Stationery > Technology & Computers"),
    ("Designing Data-Intensive Applications The Big Ideas", "Books & Stationery > Technology & Computers"),
    ("Moleskine Classic Notebook Hard Cover Ruled Journal Large", "Books & Stationery > Office Supplies"),
]


def train_classifier() -> Pipeline:
    """Trains a TF-IDF + Multinomial Naive Bayes multi-class product classifier."""
    texts = [item[0] for item in TRAINING_DATA]
    labels = [item[1] for item in TRAINING_DATA]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("clf", MultinomialNB(alpha=0.1)),
    ])

    pipeline.fit(texts, labels)
    return pipeline


class CatalogClassifier:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = train_classifier()
        return cls._instance

    @classmethod
    def predict(cls, text: str) -> Tuple[str, float]:
        """Returns (predicted_category_path, confidence_score)."""
        if not text or not text.strip():
            return "General Merchandise > Uncategorized", 0.500

        model = cls.get_instance()
        probs = model.predict_proba([text])[0]
        max_idx = probs.argmax()
        category = model.classes_[max_idx]
        confidence = round(float(probs[max_idx]), 3)

        return category, confidence
