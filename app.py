import os
import zipfile
import pandas as pd
from flask import Flask, request, render_template, send_file
from google_images_search import GoogleImagesSearch

# Initialize Flask app
app = Flask(__name__)

# Google API Credentials (Replace with your own)
API_KEY = 'AIzaSyCMTGZgBiOCBKmVyVtBwWedolEwKpYmJFo'
CSE_ID = '22a1154af09b44051'

# Initialize Google Image Search
gis = GoogleImagesSearch(API_KEY, CSE_ID)

# Configure Uploads & Download Folder
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloaded_images"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limit file size to 10MB

# Ensure necessary folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Function to download the top image for a given search term
def download_image(search_term, save_path):
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

# Route for Uploading Excel & Downloading Images
@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file uploaded", 400

        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400
        
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        # Process Excel file
        df = pd.read_excel(file_path, engine='openpyxl')

        # Check if 'posDescription' column exists
        if 'posDescription' not in df.columns:
            return "Error: Excel must contain a 'posDescription' column", 400

        # Download images for each product
        for index, row in df.iterrows():
            pos_description = str(row['posDescription'])
            valid_filename = "".join(c for c in pos_description if c.isalnum() or c in (' ', '_')).rstrip()
            save_path = os.path.join(DOWNLOAD_FOLDER, f"{valid_filename}.jpg")

            try:
                download_image(pos_description, save_path)
            except Exception as e:
                print(f"Failed to download image for: {pos_description}. Error: {e}")

        # Zip all images
        zip_path = os.path.join(DOWNLOAD_FOLDER, "images.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(DOWNLOAD_FOLDER):
                for file in files:
                    if file.endswith(".jpg") or file.endswith(".png"):
                        zipf.write(os.path.join(root, file), file)

        return render_template("index.html", download_url="/download")

    return render_template("index.html")

# Route to Download Images ZIP
@app.route("/download")
def download():
    zip_path = os.path.join(DOWNLOAD_FOLDER, "images.zip")
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
