import cv2
import numpy as np
from insightface.app import FaceAnalysis

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0)


def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (
        np.linalg.norm(v1) * np.linalg.norm(v2)
    )


def verify_faces(img1_path, img2_path):

    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    if img1 is None:
        return {"error": "Unable to read image1"}

    if img2 is None:
        return {"error": "Unable to read image2"}

    faces1 = face_app.get(img1)
    faces2 = face_app.get(img2)

    if len(faces1) == 0:
        return {"error": "No face detected in image1"}

    if len(faces2) == 0:
        return {"error": "No face detected in image2"}

    face1 = faces1[0]
    face2 = faces2[0]

    similarity = cosine_similarity(
        face1.embedding,
        face2.embedding
    )

    result = (
        "same person"
        if similarity > 0.60
        else "different person"
    )

    return {
        "verification_result": result,
        "similarity_score": round(float(similarity), 4),
        "bounding_box_image1": face1.bbox.tolist(),
        "bounding_box_image2": face2.bbox.tolist()
    }