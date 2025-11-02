import bcrypt
import numpy as np

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def calculate_bmi(weight, height):
    try:
        return round(weight / ((height / 100) ** 2), 2)
    except Exception:
        return 0

def get_recommendations(
    bmi, age, risks, gender=None, history=None, location=None,
    smoker=None, systolic_bp=None, diastolic_bp=None, cholesterol=None, exercise=None
):
    recs = []

    # BMI-based recommendations
    if bmi is not None and bmi != 0:
        if bmi >= 30:
            recs.append("You are in the obese BMI range. Consider consulting a dietitian for a tailored eating plan.")
        elif bmi >= 25:
            recs.append("Maintain a healthy diet and exercise regularly. Aim for at least 150 minutes of moderate exercise per week.")
        if bmi < 18.5:
            recs.append("Increase calorie intake with healthy foods—consider nuts, avocados, and whole grains.")

    # Age-based recommendations
    if age is not None:
        if age >= 40:
            recs.append("Schedule regular health checkups and cardiovascular screening.")
        if age >= 60:
            recs.append("Ask your healthcare provider about annual flu shots and bone health.")
        if age <= 18:
            recs.append("Growing teens should include sports and limit screen time for better overall health.")

    # Gender-specific recommendations
    if gender is not None:
        g = gender.lower()
        if g == "female" and age and age > 50:
            recs.append("Discuss calcium and vitamin D supplementation with your doctor for bone health.")
        if g == "male" and age and age > 50:
            recs.append("Get your prostate health checked during your regular physical exam.")

    # Blood pressure & cholesterol advice
    if (systolic_bp and systolic_bp >= 140) or (diastolic_bp and diastolic_bp >= 90):
        recs.append("Your blood pressure is high. Reduce salt intake and consider seeing a healthcare provider.")
    if cholesterol and cholesterol >= 240:
        recs.append("High cholesterol detected. Avoid trans fats and incorporate more fiber-rich foods (like oats, beans, and fruits).")

    # Smoker advice
    if smoker == 1:
        recs.append("Quitting smoking can rapidly improve your cardiovascular and pulmonary health.")

    # Activity recommendation
    if exercise == "none":
        recs.append("Try to include any physical activity in your daily routine—even a walk after meals is beneficial.")

    # Risk-specific advice (tolerant to extra spaces/emoji)
    if risks.get("Diabetes Risk", "").strip().startswith("High Risk"):
        recs.append("Monitor blood sugar regularly and avoid sugary drinks and snacks.")
        recs.append("Schedule an HbA1c test and discuss with your doctor.")
    if risks.get("Heart Disease Risk", "").strip().startswith("High Risk"):
        recs.append("Check cholesterol and blood pressure, avoid smoking.")
        recs.append("Include more plant-based foods and nuts for heart health.")
    if risks.get("Kidney Disease Risk", "").strip().startswith("High Risk"):
        recs.append("Stay hydrated and monitor kidney function. Limit intake of high-protein and high-salt foods.")
        recs.append("Get your creatinine and urea checked regularly.")
    if risks.get("Cardiovascular Risk", "").strip().startswith("High Risk"):
        recs.append("Include cardio exercises such as brisk walking, cycling, or swimming in your weekly routine.")
        recs.append("Manage stress with mindfulness activities or yoga.")

    # History and trends
    if history and history.count("High Risk") >= 2:
        recs.append("Multiple high risk results. Consider a comprehensive health checkup and follow-up with your healthcare provider.")

    # Geographical/localization example (location-specific advice)
    if location and "Alibag" in location:
        recs.append("Take advantage of local fresh seafood, but avoid adding too much salt to your meals.")

    # Preventive and lifestyle (always shown)
    recs.append("Drink at least 2 liters of water daily unless advised otherwise by your doctor.")
    recs.append("Aim for 7-8 hours of sleep each night for optimal health.")

    return recs
