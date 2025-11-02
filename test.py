import numpy as np
import pickle
import joblib

def load_model_and_scaler(model_path, scaler_path):
    """Handles pickle or joblib automatically."""
    try:
        model = joblib.load(model_path)
    except:
        model = pickle.load(open(model_path, 'rb'))
    try:
        scaler = joblib.load(scaler_path)
    except:
        scaler = pickle.load(open(scaler_path, 'rb'))
    return model, scaler


# ---------- Diabetes ----------
try:
    diabetes_model, diabetes_scaler = load_model_and_scaler('models/diabetes_model.pkl', 'models/diabetes_scaler.pkl')
    diabetes_sample = np.array([[6, 148, 72, 35, 0, 33.6, 0.627, 50]])  # 8 features
    scaled = diabetes_scaler.transform(diabetes_sample)
    pred = diabetes_model.predict(scaled)
    print("✅ Diabetes prediction:", pred)
except Exception as e:
    print("❌ Diabetes model error:", e)


# ---------- Heart ----------
try:
    heart_model, heart_scaler = load_model_and_scaler('models/heart_model.pkl', 'models/heart_scaler.pkl')
    # 20 features (example dummy numeric input)
    heart_sample = np.array([[63, 1, 0, 145, 233, 1, 0, 150, 0, 2.3, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0]])
    scaled = heart_scaler.transform(heart_sample)
    pred = heart_model.predict(scaled)
    print("✅ Heart prediction:", pred)
except Exception as e:
    print("❌ Heart model error:", e)


# ---------- Kidney ----------
try:
    kidney_model, kidney_scaler = load_model_and_scaler('models/kidney_model.pkl', 'models/kidney_scaler.pkl')
    # 24 features (example dummy numeric input)
    kidney_sample = np.random.rand(1, 24)  # just random for testing shape
    scaled = kidney_scaler.transform(kidney_sample)
    pred = kidney_model.predict(scaled)
    print("✅ Kidney prediction:", pred)
except Exception as e:
    print("❌ Kidney model error:", e)


# ---------- Cardio ----------
try:
    cardio_model, cardio_scaler = load_model_and_scaler('models/cardio_model.pkl', 'models/cardio_scaler.pkl')
    cardio_sample = np.array([[50, 1, 170, 70, 120, 80, 1, 1, 0, 0, 1]])  # 11 features
    scaled = cardio_scaler.transform(cardio_sample)
    pred = cardio_model.predict(scaled)
    print("✅ Cardio prediction:", pred)
except Exception as e:
    print("❌ Cardio model error:", e)
