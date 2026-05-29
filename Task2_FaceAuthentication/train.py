import os
import pickle
from insightface.app import FaceAnalysis

os.makedirs("models", exist_ok=True)

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0)

model_info = {
    "model_name": "InsightFace Buffalo_L"
}

with open("models/face_model.pkl", "wb") as f:
    pickle.dump(model_info, f)

print("Model initialized and saved successfully!")