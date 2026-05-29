# Globussoft Data Science Assignment

Submitted by: Sudhanshu Sagar

## Project Structure

```text
Globussoft-Assignment/
│
├── Task1/
│   ├── amazon_scraper.py
│   ├── amazon_laptop_20260529_113735.csv
│   └── README.md
│
└── Task2/
    ├── app.py
    ├── train.py
    ├── predict.py
    ├── models/
    │   └── face_model.pkl
    ├── sample_images/
    └── README.md
```

## Task 1 - Amazon Laptop Scraper

A Python-based web scraping solution that extracts laptop product information from Amazon India.

### Extracted Fields

* Product Title
* Product Price
* Product Rating
* Product Image URL
* Ad / Organic Result

### Output

The scraped data is stored in a timestamped CSV file.

Example:

```text
amazon_laptop_20260529_113735.csv
```

---

## Task 2 - Face Authentication

A FastAPI-based face verification system using InsightFace.

### Features

* Accepts two face images
* Detects faces in both images
* Extracts face embeddings
* Computes cosine similarity
* Returns:

  * Verification Result
  * Similarity Score
  * Bounding Boxes

### Technologies Used

* FastAPI
* InsightFace
* OpenCV
* NumPy
* ONNX Runtime

### API Endpoint

POST /verify

### Response Example

```json
{
  "verification_result": "same person",
  "similarity_score": 0.82,
  "bounding_box_image1": [x1, y1, x2, y2],
  "bounding_box_image2": [x1, y1, x2, y2]
}
```

## Installation

```bash
pip install -r requirements.txt
```

## Run Face Authentication API

```bash
cd Task2

python train.py

uvicorn app:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```
