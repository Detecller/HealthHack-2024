import os
from flask import Flask, render_template, request, redirect, flash, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import fitz
import re

app = Flask(__name__)
app.secret_key = "HealthHack 2024"
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_health_data(report_text):
    health_data = {}

    # Extract bone/joint function
    bone_joint_match = re.search(r'Phosphate[^(\d]+([\d.]+)\s*mmol/L[^(\d]+Calcium[^(\d]+([\d.]+)\s*mmol/L[^(\d]+Uric Acid[^(\d]+([\d.]+)\s*mmol/L[^(\d]', report_text)
    if bone_joint_match:
        health_data['bone_joint_profile'] = {
            'phosphate': float(bone_joint_match.group(1)),
            'calcium': float(bone_joint_match.group(2)),
            'uric acid': float(bone_joint_match.group(3))
        }
    else:
        print("Bone/Joint profile data not found in the report text.")
        
    # Extract kidney profile
    kidney_match = re.search(r'Sodium[^(\d]+([\d.]+)\s*mmol/L[^(\d]+Potassium[^(\d]+([\d.]+)\s*mmol/L[^(\d]+Chloride[^(\d]+([\d.]+)\s*mmol/L[^(\d]+Urea[^(\d]+([\d.]+)\s*mmol/L', report_text)
    if kidney_match:
        health_data['kidney_profile'] = {
            'sodium': float(kidney_match.group(1)),
            'potassium': float(kidney_match.group(2)),
            'chloride': float(kidney_match.group(3)),
            'urea': float(kidney_match.group(4))
        }
    else:
        print("Kidney profile data not found in the report text.")

    return health_data


def extract_text_from_image(image_path):
    pil_image = Image.open(image_path)
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    text = pytesseract.image_to_string(pil_image, lang='eng')
    return text


def save_pixmap_as_image(pixmap, image_path):
    img = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    img.save(image_path, format='PNG')


def process_scanned_pdf(filepath):
    scanned_words = []
    doc = fitz.open(filepath)

    for page_num in range(doc.page_count):
        page = doc[page_num]

        # Get the entire page pixmap
        img_matrix = fitz.Matrix(1, 1)
        img = page.get_pixmap(matrix=img_matrix)

        # Save the image as a temporary file
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_img_{page_num}.png')
        save_pixmap_as_image(img, img_path)

        # Extract text from the image using Tesseract OCR
        text = extract_text_from_image(img_path)
        scanned_words.extend(text.split())

    doc.close()

    # Join the scanned words into a string for health data extraction
    report_text = ' '.join(scanned_words)
    #Testing
    print("Scanned Words:", scanned_words)
    print("Report Text:", report_text)
    # Extract health data
    extracted_data = extract_health_data(report_text)
    #Testing
    print("Extracted Data:", extracted_data)
    return extracted_data


# Define webpages
@app.route('/')
def home():
    return render_template('Home.html')


@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part")
            return redirect(url_for('home'))

        file = request.files['file']
        extracted_data = {}

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process the scanned PDF
            extracted_data = process_scanned_pdf(filepath)

        return render_template('Results.html', extracted_data=extracted_data)


if __name__ == '__main__':
    app.run(host='127.0.0.2', port=5000, debug=True)