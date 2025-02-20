import os
import zipfile
import pandas as pd
from flask import Flask, request, render_template, send_file
from google_images_search import GoogleImagesSearch

# Flask app initialization
app = Flask(__name__)

# Google API Key and CSE ID
API_KEY = "AIzaSyCMTGZgBiOCBKmVyVtBwWedolEwKpYmJFo"
CSE_ID = "22a1154af09b44051"

# Directory for saving images
IMAGE_DIR = "static/downloaded_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Initialize Google Images Search
gis = GoogleImagesSearch(API_KEY, CSE_ID)

def download_image(search_term, save_path):
    """Search for an image on Google and download the first result."""
    search_params = {
        'q': search_term,
        'num': 1,
        'fileType': 'jpg|png',
        'imgType': 'photo',
        'safe': 'off'
    }
    gis.search(search_params=search_params)
    for image in gis.results():
        image.download(save_path)
        break  # Only download the first result

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            # Save uploaded file
            file_path = os.path.join("uploads", file.filename)
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)

            # Read Excel file
            df = pd.read_excel(file_path)

            # Ensure required column exists
            if "posDescription" not in df.columns:
                return "Error: Excel file must contain 'posDescription' column."

            # Download images
            for index, row in df.iterrows():
                pos_description = str(row["posDescription"])
                filename = "".join(c for c in pos_description if c.isalnum() or c in (' ', '_')).rstrip() + ".jpg"
                save_path = os.path.join(IMAGE_DIR, filename)
                try:
                    download_image(pos_description, save_path)
                except Exception as e:
                    print(f"Failed to download image for: {pos_description}. Error: {e}")

            # Create a ZIP file
            zip_path = "static/images.zip"
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for root, _, files in os.walk(IMAGE_DIR):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            return render_template("index.html", download_url=zip_path)

    return render_template("index.html", download_url=None)

@app.route("/download")
def download():
    return send_file("static/images.zip", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
