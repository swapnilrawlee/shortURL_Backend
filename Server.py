import qrcode
import io
import os
import base64
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from pymongo import MongoClient
import hashlib

app = Flask(__name__)
CORS(app)
mongo_uri = os.environ.get("MONGO_URI")
client = MongoClient(mongo_uri)

# MongoDB setup - replace your connection string & DB/collection names
db = client["url_shortener_db"]
collection = db["urls"]

@app.route('/', methods=['get'])
def hello():
    return jsonify("hello")

def generate_short_code(long_url):
    hash_object = hashlib.md5(long_url.encode())
    short_code = base64.urlsafe_b64encode(hash_object.digest())[:6].decode()
    return short_code

@app.route('/longUrl', methods=['POST'])
def create_short_url():
    data = request.get_json()
    long_url = data.get('url')
    custom_alias = data.get('custom_alias')

    if not long_url:
        return jsonify(error="No URL provided"), 400

    if custom_alias:
        # Check if alias taken
        if collection.find_one({"short_code": custom_alias}):
            return jsonify(error="Custom alias already in use"), 400
        short_code = custom_alias
    else:
        short_code = generate_short_code(long_url)

    existing = collection.find_one({"short_code": short_code})
    if not existing:
        collection.insert_one({
            "short_code": short_code,
            "long_url": long_url
        })

    short_url = f"http://short.ly/{short_code}"

    # Generate QR code image (base64)
    qr_img = qrcode.make(short_url)
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    return jsonify(shortUrl=short_url, qrCode=f"data:image/png;base64,{qr_base64}")



# Redirect route: Redirect short URL to original long URL
@app.route('/<short_code>')
def redirect_to_long_url(short_code):
    record = collection.find_one({"short_code": short_code})
    if record:
        return redirect(record["long_url"])
    else:
        return jsonify(error="Short URL not found"), 404

if __name__ == "__main__":
    import os
    debug_mode = os.environ.get("DEBUG", "False") == "True"
    port = int(os.environ.get("PORT", 4000))
    app.run(debug=debug_mode, port=port, host="0.0.0.0")

