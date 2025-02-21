import os
import zipfile
import pandas as pd
from flask import Flask, render_template, request, send_file, jsonify
from threading import Thread
from PIL import Image
import requests
from bs4 import BeautifulSoup
import time

# Flask App Initialization
app = Flask(__name__)

# Increase Upload Limit (500MB)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# Folders
UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = "downloaded_images"
ZIP_PATH = "images.zip"
STATUS_FILE = "status.txt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Function to Extract Image URLs from Google Search
def fetch_google_images(search_term):
    search_url = f"https://www.google.com/search?tbm=isch&q={search_term}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        images = soup.find_all("img")

        img_links = [img["src"] for img in images if "http" in img.get("src", "")]
        return img_links[:1]  # Return first valid image URL

    except Exception as e:
        print(f"❌ Error fetching images for {search_term}: {e}")
        return []

# Function to Download & Optimize Image
def download_image(search_term, save_path):
    image_urls = fetch_google_images(search_term)
    if not image_urls:
        print(f"⚠️ No images found for {search_term}. Skipping...")
        return

    try:
        response = requests.get(image_urls[0], stream=True, timeout=10)
        response.raise_for_status()

        with open(save_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)

        # Convert & Resize Image
        img = Image.open(save_path)
        img = img.convert("RGB")
        img = img.resize((300, 300))
        img.save(save_path, "JPEG", quality=80)
        
        print(f"✅ Downloaded & Optimized: {search_term}")

    except Exception as e:
        print(f"❌ Failed to download image for {search_term}: {e}")

# Process Images in Background
def process_images(df):
    with open(STATUS_FILE, "w") as status_file:
        status_file.write("processing")

    for _, row in df.iterrows():
        pos_description = str(row['posDescription'])
        valid_filename = "".join(c for c in pos_description if c.isalnum() or c in (' ', '_')).rstrip()
        save_path = os.path.join(IMAGE_FOLDER, f"{valid_filename}.jpg")
        download_image(pos_description, save_path)

    # Create ZIP File
    with zipfile.ZipFile(ZIP_PATH, 'w') as zipf:
        for img in os.listdir(IMAGE_FOLDER):
            zipf.write(os.path.join(IMAGE_FOLDER, img), img)

    with open(STATUS_FILE, "w") as status_file:
        status_file.write("done")

    print("✅ Image processing complete.")

# File Upload Route
@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error="No file uploaded", processing=False, show_download=False)

        file = request.files["file"]
        if file.filename == "":
            return render_template("index.html", error="No selected file", processing=False, show_download=False)

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except Exception as e:
            return render_template("index.html", error=f"❌ Error reading Excel file: {e}", processing=False, show_download=False)

        if "posDescription" not in df.columns:
            return render_template("index.html", error="❌ Error: Excel file must contain 'posDescription' column.", processing=False, show_download=False)

        # Clear old images
        for f in os.listdir(IMAGE_FOLDER):
            try:
                os.remove(os.path.join(IMAGE_FOLDER, f))
            except PermissionError:
                print(f"Skipping locked file: {f}")

        # Start Background Processing
        thread = Thread(target=process_images, args=(df,))
        thread.start()

        return render_template("index.html", processing=True, show_download=False)

    return render_template("index.html", processing=False, show_download=os.path.exists(ZIP_PATH))

# Check Processing Status
@app.route("/status")
def check_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as file:
            status = file.read().strip()
            return jsonify({"status": status})
    return jsonify({"status": "pending"})

# Download Route
@app.route("/download")
def download_zip():
    return send_file(ZIP_PATH, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
