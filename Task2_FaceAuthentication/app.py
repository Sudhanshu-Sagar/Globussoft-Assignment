import os
import shutil

from fastapi import FastAPI, UploadFile, File
from predict import verify_faces

app = FastAPI(
    title="Face Authentication API"
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/verify")
async def verify(
    image1: UploadFile = File(...),
    image2: UploadFile = File(...)
):

    image1_path = os.path.join(
        UPLOAD_DIR,
        image1.filename
    )

    image2_path = os.path.join(
        UPLOAD_DIR,
        image2.filename
    )

    with open(image1_path, "wb") as buffer:
        shutil.copyfileobj(
            image1.file,
            buffer
        )

    with open(image2_path, "wb") as buffer:
        shutil.copyfileobj(
            image2.file,
            buffer
        )

    result = verify_faces(
        image1_path,
        image2_path
    )

    return result