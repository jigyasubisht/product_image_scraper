import os
import zipfile
import pandas as pd
from flask import Flask, render_template, request, send_file
from google_images_search import GoogleImagesSearch
from PIL import Image

# Flask App Initialization
app = Flask(__name__)

# Google API Credentials
API_KEY = 'AIzaSyCMTGZgBiOCBKmVyVtBwWedolEwKpYmJFo'
CSE_ID = '22a1154af09b44051'

gis = GoogleImagesSearch(API_KEY, CSE_ID)

# Upload Folder
UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = "downloaded_images"
ZIP_PATH = "images.zip"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Function to Download & Optimize Image
def download_image(search_term, save_path):
    search_params = {
        'q': search_term,
        'num': 1,
        'fileType': 'jpg|png',
        'imgType': 'photo',
        'safe': 'off'
    }
    try:
        gis.search(search_params=search_params)
        if not gis.results():
            print(f"⚠️ No images found for {search_term}. Skipping...")
            return

        for image in gis.results():
            image.download(save_path)

            # Convert & Resize Image
            img = Image.open(save_path)
            img = img.convert("RGB")
            img = img.resize((300, 300))
            img.save(save_path, "JPEG", quality=80)
            break

        print(f"✅ Downloaded & Optimized: {search_term}")

    except Exception as e:
        print(f"❌ Failed to download image for {search_term}: {e}")

# File Upload Route
@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file uploaded", 400

        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except Exception as e:
            return f"❌ Error reading Excel file: {e}", 500

        if "posDescription" not in df.columns:
            return "❌ Error: Excel file must contain a 'posDescription' column.", 400

        # Clear previous images
        for f in os.listdir(IMAGE_FOLDER):
            os.remove(os.path.join(IMAGE_FOLDER, f))

        # Download images
        for _, row in df.iterrows():
            pos_description = str(row['posDescription'])
            valid_filename = "".join(c for c in pos_description if c.isalnum() or c in (' ', '_')).rstrip()
            save_path = os.path.join(IMAGE_FOLDER, f"{valid_filename}.jpg")
            download_image(pos_description, save_path)

        # Create Zip File
        with zipfile.ZipFile(ZIP_PATH, 'w') as zipf:
            for img in os.listdir(IMAGE_FOLDER):
                zipf.write(os.path.join(IMAGE_FOLDER, img), img)

        return render_template("index.html", download_url="/download")

    return render_template("index.html")

# Download Route
@app.route("/download")
def download_zip():
    return send_file(ZIP_PATH, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
