import os
import zipfile
import requests
import pandas as pd
from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
from PIL import Image

# Flask App Initialization
app = Flask(__name__)

# Upload & Download Folders
UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = "downloaded_images"
ZIP_PATH = "images.zip"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Function to get image links using BeautifulSoup
def get_image_links(search_term):
    query = search_term.replace(" ", "+")
    url = f"https://www.google.com/search?q={query}&tbm=isch"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        img_tags = soup.find_all("img")
        
        img_urls = [img["src"] for img in img_tags if "src" in img.attrs]
        return img_urls[1:]  # Ignore first result (Google logo)
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching images for {search_term}: {e}")
        return []

# Function to Download & Optimize Images
def download_image(search_term, save_path):
    image_links = get_image_links(search_term)
    
    if not image_links:
        print(f"⚠️ No images found for {search_term}. Skipping...")
        return
    
    try:
        img_url = image_links[0]
        img_data = requests.get(img_url, stream=True).content
        
        with open(save_path, "wb") as f:
            f.write(img_data)
        
        # Convert & Resize Image
        with Image.open(save_path) as img:
            img = img.convert("RGB")
            img = img.resize((300, 300))
            img.save(save_path, "JPEG", quality=80)
        
        print(f"✅ Downloaded & Optimized: {search_term}")

    except Exception as e:
        print(f"❌ Failed to download image for {search_term}: {e}")

# Route for File Upload & Image Download
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

        # Clear previous images safely
        for f in os.listdir(IMAGE_FOLDER):
            file_path = os.path.join(IMAGE_FOLDER, f)
            try:
                os.chmod(file_path, 0o777)
                os.remove(file_path)
            except Exception as e:
                print(f"❌ Could not delete {f}: {e}")

        # Download images
        for _, row in df.iterrows():
            pos_description = str(row["posDescription"])
            valid_filename = "".join(c for c in pos_description if c.isalnum() or c in (' ', '_')).rstrip()
            save_path = os.path.join(IMAGE_FOLDER, f"{valid_filename}.jpg")
            download_image(pos_description, save_path)

        # Create ZIP File
        with zipfile.ZipFile(ZIP_PATH, "w") as zipf:
            for img in os.listdir(IMAGE_FOLDER):
                zipf.write(os.path.join(IMAGE_FOLDER, img), img)

        return render_template("index.html", download_url="/download")

    return render_template("index.html")

# Route to Download the Zip File
@app.route("/download")
def download_zip():
    return send_file(ZIP_PATH, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
