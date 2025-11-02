from flask import Flask, render_template, request, redirect, session, url_for, g, flash
import sqlite3, os, pickle, joblib
from utils import hash_password, check_password, calculate_bmi, get_recommendations
from datetime import datetime


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')
DB_PATH = 'database.db'

# -- DATABASE --
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def initialize_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT, middle_name TEXT, surname TEXT,
                    email TEXT UNIQUE, phone TEXT, dob DATE, age INTEGER, gender TEXT,
                    height REAL, weight REAL, location TEXT, password BLOB
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS health_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    disease TEXT,
                    result TEXT,
                    glucose REAL, bmi REAL, pregnancies INTEGER, dpf REAL,
                    cp INTEGER, trestbps REAL, chol REAL, exang INTEGER,
                    sc REAL, bu REAL, hemo REAL, bp REAL,
                    ap_hi REAL, ap_lo REAL, cholesterol REAL, smoke INTEGER
                )''')
    conn.commit()
    conn.close()


initialize_db()

# -- MODEL LOADER --
def load_model_scaler(model_path, scaler_path):
    model, scaler = None, None
    try:
        if os.path.exists(model_path):
            model = joblib.load(model_path)
        if os.path.exists(scaler_path):
            scaler = joblib.load(scaler_path)
    except:
        model = pickle.load(open(model_path, 'rb'))
        scaler = pickle.load(open(scaler_path, 'rb'))
    return model, scaler

diabetes_model, diabetes_scaler = load_model_scaler('models/diabetes_model.pkl', 'models/diabetes_scaler.pkl')
heart_model, heart_scaler = load_model_scaler('models/heart_model.pkl', 'models/heart_scaler.pkl')
kidney_model, kidney_scaler = load_model_scaler('models/kidney_model.pkl', 'models/kidney_scaler.pkl')
cardio_model, cardio_scaler = load_model_scaler('models/cardio_model.pkl', 'models/cardio_scaler.pkl')

# ---- AUTH & PROFILE ROUTES ----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            form = request.form
            first_name = form['first_name']
            middle_name = form['middle_name']
            surname = form['surname']
            email = form['email']
            phone = form['phone']
            dob_str = form['dob']
            gender = form['gender']
            height = float(form['height'])
            weight = float(form['weight'])
            location = form['location']
            password = hash_password(form['password'])
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            db = get_db()
            db.execute('''INSERT INTO users (first_name, middle_name, surname, email, phone, dob, age, gender, height, weight, location, password)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (first_name, middle_name, surname, email, phone, dob_str, age, gender, height, weight, location, password))
            db.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Email already exists. Please use a different one.", "error")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password(password, user['password']):
            session['user_id'] = user['id']
            session['first_name'] = user['first_name']
            flash("Login successful!", "info")
            return redirect('/dashboard')
        else:
            flash("Invalid email or password.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect('/')

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    if request.method == 'POST':
        user_id = session['user_id']
        form = request.form
        first_name = form['first_name']
        middle_name = form['middle_name']
        surname = form['surname']
        phone = form['phone']
        dob_str = form['dob']
        gender = form['gender']
        height = float(form['height'])
        weight = float(form['weight'])
        location = form['location']
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        db.execute('''UPDATE users SET first_name=?, middle_name=?, surname=?, phone=?, dob=?, age=?, gender=?, height=?, weight=?, location=?
                        WHERE id=?''',
                   (first_name, middle_name, surname, phone, dob_str, age, gender, height, weight, location, user_id))
        db.commit()
        flash("Profile updated successfully!")
        return redirect('/dashboard')
    else:
        user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        return render_template('edit_profile.html', user=user)

# ---- DASHBOARD ----
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    return render_template('dashboard.html', user=user)


# Add these feature names for each model
DIABETES_FEATURES = ['Glucose', 'BMI', 'Age', 'Pregnancies', 'DPF', 'Pad1', 'Pad2', 'Pad3']
HEART_FEATURES = ['CP', 'Trestbps', 'Chol', 'Exang'] + ['Pad' + str(i) for i in range(1, 17)]
KIDNEY_FEATURES = ['SC', 'BU', 'Hemo', 'BP'] + ['Pad' + str(i) for i in range(1, 21)]
CARDIO_FEATURES = ['Age', 'Gender', 'AP_hi', 'AP_lo', 'Cholesterol', 'Smoke'] + ['Pad' + str(i) for i in range(1, 6)]

# ---- DISEASE PREDICTION ROUTES ----

@app.route('/predict_diabetes', methods=['GET', 'POST'])
def predict_diabetes():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if request.method == 'POST':
        pregnancies = float(request.form.get('pregnancies', 0))
        glucose = float(request.form.get('glucose', 0))
        bmi = float(request.form.get('bmi', 0))
        dpf = float(request.form.get('dpf', 0))
        age = float(user['age'])
        diabetes_input = [glucose, bmi, age, pregnancies, dpf]
        # Pad zeros if needed
        missing = [0]*3  # Adjust if your model expects more features
        pred_input = diabetes_input + missing
        risk_pred = int(diabetes_model.predict(diabetes_scaler.transform([pred_input]))[0])
        risk_label = 'High Risk ' if risk_pred == 1 else 'Low Risk '
        recommendations = get_recommendations(bmi, age, {'Diabetes Risk': risk_label})
        db.execute(
            """INSERT INTO health_data (user_id, disease, result, glucose, bmi, pregnancies, dpf)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user['id'], 'diabetes', risk_label, glucose, bmi, pregnancies, dpf)
        )
        db.commit()
        return render_template('result.html', risk_name="Diabetes",
                              risk_label=risk_label, explain_data=None, recommendations=recommendations)
    return render_template('form_diabetes.html', user=user)


@app.route('/predict_heart', methods=['GET', 'POST'])
def predict_heart():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if request.method == 'POST':
        cp = int(request.form.get('cp', 0))
        trestbps = float(request.form.get('trestbps', 0))
        chol = float(request.form.get('chol', 0))
        exang = int(request.form.get('exang', 0))
        heart_input = [cp, trestbps, chol, exang]
        # Pad for model
        missing = [0]*16
        pred_input = heart_input + missing
        sex = 1 if user['gender'].lower() == 'male' else 0
        age = user['age']
        risk_pred = int(heart_model.predict(heart_scaler.transform([pred_input]))[0])
        risk_label = 'High Risk ' if risk_pred == 1 else 'Low Risk '
        recommendations = get_recommendations(0, age, {'Heart Disease Risk': risk_label})
        db.execute(
            """INSERT INTO health_data (user_id, disease, result, cp, trestbps, chol, exang)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user['id'], 'heart', risk_label, cp, trestbps, chol, exang)
        )
        db.commit()
        return render_template('result.html', risk_name="Heart Disease",
                              risk_label=risk_label, explain_data=None, recommendations=recommendations)
    return render_template('form_heart.html', user=user)


@app.route('/predict_kidney', methods=['GET', 'POST'])
def predict_kidney():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if request.method == 'POST':
        sc = float(request.form.get('sc', 0))
        bu = float(request.form.get('bu', 0))
        hemo = float(request.form.get('hemo', 0))
        bp = float(request.form.get('bp', 0))
        kidney_input = [sc, bu, hemo, bp]
        missing = [1]*20
        pred_input = kidney_input + missing
        age = float(user['age'])
        risk_pred = int(kidney_model.predict(kidney_scaler.transform([pred_input]))[0])
        risk_label = 'High Risk ' if risk_pred == 1 else 'Low Risk '
        recommendations = get_recommendations(0, age, {'Kidney Disease Risk': risk_label})
        db.execute(
            """INSERT INTO health_data (user_id, disease, result, sc, bu, hemo, bp)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user['id'], 'kidney', risk_label, sc, bu, hemo, bp)
        )
        db.commit()
        return render_template('result.html', risk_name="Kidney Disease",
                              risk_label=risk_label, explain_data=None, recommendations=recommendations)
    return render_template('form_kidney.html', user=user)


@app.route('/predict_cardio', methods=['GET', 'POST'])
def predict_cardio():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if request.method == 'POST':
        age = user['age']
        gender = 1 if user['gender'].lower() == 'male' else 2
        ap_hi = float(request.form.get('ap_hi', 0))
        ap_lo = float(request.form.get('ap_lo', 0))
        cholesterol = int(request.form.get('cholesterol', 0))
        smoke = int(request.form.get('smoke', 0))
        cardio_input = [age, gender, ap_hi, ap_lo, cholesterol, smoke]
        missing = [0]*5 # for model consistency
        pred_input = cardio_input + missing
        risk_pred = int(cardio_model.predict(cardio_scaler.transform([pred_input]))[0])
        risk_label = 'High Risk ' if risk_pred == 1 else 'Low Risk '
        recommendations = get_recommendations(0, age, {'Cardiovascular Risk': risk_label})
        db.execute(
            """INSERT INTO health_data (user_id, disease, result, ap_hi, ap_lo, cholesterol, smoke)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user['id'], 'cardio', risk_label, ap_hi, ap_lo, cholesterol, smoke)
        )
        db.commit()
        return render_template('result.html', risk_name="Cardiovascular",
                              risk_label=risk_label, explain_data=None, recommendations=recommendations)
    return render_template('form_cardio.html', user=user)


@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    history = db.execute("""
        SELECT created_at, disease, result, glucose, bmi, pregnancies, dpf,
               cp, trestbps, chol, exang, sc, bu, hemo, bp, ap_hi, ap_lo, cholesterol, smoke
        FROM health_data
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session['user_id'],)).fetchall()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    return render_template('history.html', user=user, history=history)

@app.route('/progress')
def progress():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    user_id = session['user_id']
    # Example for heart disease risk trend
    rows = db.execute("""
        SELECT created_at, result
        FROM health_data
        WHERE user_id=? AND disease='heart'
        ORDER BY created_at ASC
    """, (user_id,))
    dates = [r['created_at'][:10] for r in rows]
    risks = [1 if 'High' in r['result'] else 0 for r in rows]
    return render_template('progress.html', dates=dates, risks=risks)


if __name__ == "__main__":
    app.run(debug=True)



# from flask import Flask, render_template, request, redirect, session, url_for, g, flash
# import sqlite3, os, pickle, joblib
# from utils import hash_password, check_password, calculate_bmi, get_recommendations
# from datetime import datetime
# import shap

# app = Flask(__name__)
# app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')
# DB_PATH = 'database.db'

# # Feature names — update these to match your model training order!
# DIABETES_FEATURES = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI', 'DPF', 'Age']
# HEART_FEATURES = ['Age', 'Sex', 'CP', 'Trestbps', 'Chol', 'Exang'] + ['Pad' + str(i) for i in range(1, 15)]
# KIDNEY_FEATURES = ['SC', 'BU', 'Hemo', 'Age', 'BP'] + ['Pad' + str(i) for i in range(1, 19)]
# CARDIO_FEATURES = ['Age', 'Gender', 'AP_hi', 'AP_lo', 'Cholesterol', 'Smoke'] + ['Pad' + str(i) for i in range(1, 5)]

# def get_db():
#     if 'db' not in g:
#         g.db = sqlite3.connect(DB_PATH)
#         g.db.row_factory = sqlite3.Row
#     return g.db

# @app.teardown_appcontext
# def close_db(exception=None):
#     db = g.pop('db', None)
#     if db is not None:
#         db.close()

# def initialize_db():
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute('''CREATE TABLE IF NOT EXISTS users (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     first_name TEXT, middle_name TEXT, surname TEXT,
#                     email TEXT UNIQUE, phone TEXT, dob DATE, age INTEGER, gender TEXT,
#                     height REAL, weight REAL, location TEXT, password BLOB
#                 )''')
#     c.execute('''CREATE TABLE IF NOT EXISTS health_data (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     user_id INTEGER,
#                     created_at TEXT DEFAULT CURRENT_TIMESTAMP,
#                     disease TEXT,
#                     result TEXT
#                 )''')
#     conn.commit()
#     conn.close()

# initialize_db()

# def load_model_scaler(model_path, scaler_path):
#     model, scaler = None, None
#     try:
#         if os.path.exists(model_path):
#             model = joblib.load(model_path)
#         if os.path.exists(scaler_path):
#             scaler = joblib.load(scaler_path)
#     except:
#         model = pickle.load(open(model_path, 'rb'))
#         scaler = pickle.load(open(scaler_path, 'rb'))
#     return model, scaler

# diabetes_model, diabetes_scaler = load_model_scaler('models/diabetes_model.pkl', 'models/diabetes_scaler.pkl')
# heart_model, heart_scaler = load_model_scaler('models/heart_model.pkl', 'models/heart_scaler.pkl')
# kidney_model, kidney_scaler = load_model_scaler('models/kidney_model.pkl', 'models/kidney_scaler.pkl')
# cardio_model, cardio_scaler = load_model_scaler('models/cardio_model.pkl', 'models/cardio_scaler.pkl')

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         try:
#             form = request.form
#             first_name = form['first_name']
#             middle_name = form['middle_name']
#             surname = form['surname']
#             email = form['email']
#             phone = form['phone']
#             dob_str = form['dob']
#             gender = form['gender']
#             height = float(form['height'])
#             weight = float(form['weight'])
#             location = form['location']
#             password = hash_password(form['password'])
#             dob = datetime.strptime(dob_str, "%Y-%m-%d")
#             today = datetime.today()
#             age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
#             db = get_db()
#             db.execute('''INSERT INTO users (first_name, middle_name, surname, email, phone, dob, age, gender, height, weight, location, password)
#                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
#                        (first_name, middle_name, surname, email, phone, dob_str, age, gender, height, weight, location, password))
#             db.commit()
#             flash("Registration successful! Please log in.", "success")
#             return redirect('/login')
#         except sqlite3.IntegrityError:
#             flash("Email already exists. Please use a different one.", "error")
#     return render_template('signup.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         db = get_db()
#         user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
#         if user and check_password(password, user['password']):
#             session['user_id'] = user['id']
#             session['first_name'] = user['first_name']
#             flash("Login successful!", "info")
#             return redirect('/dashboard')
#         else:
#             flash("Invalid email or password.", "error")
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     session.clear()
#     flash("You have been logged out.", "info")
#     return redirect('/')

# @app.route('/update_profile', methods=['GET', 'POST'])
# def update_profile():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     if request.method == 'POST':
#         user_id = session['user_id']
#         form = request.form
#         first_name = form['first_name']
#         middle_name = form['middle_name']
#         surname = form['surname']
#         phone = form['phone']
#         dob_str = form['dob']
#         gender = form['gender']
#         height = float(form['height'])
#         weight = float(form['weight'])
#         location = form['location']
#         dob = datetime.strptime(dob_str, "%Y-%m-%d")
#         today = datetime.today()
#         age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
#         db.execute('''UPDATE users SET first_name=?, middle_name=?, surname=?, phone=?, dob=?, age=?, gender=?, height=?, weight=?, location=?
#                       WHERE id=?''',
#                    (first_name, middle_name, surname, phone, dob_str, age, gender, height, weight, location, user_id))
#         db.commit()
#         flash("Profile updated successfully!")
#         return redirect('/dashboard')
#     else:
#         user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#         return render_template('edit_profile.html', user=user)

# @app.route('/dashboard')
# def dashboard():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#     return render_template('dashboard.html', user=user)

# @app.route('/predict_diabetes', methods=['GET', 'POST'])
# def predict_diabetes():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#     explain_data = None
#     if request.method == 'POST':
#         pregnancies = float(request.form.get('pregnancies', 0))
#         glucose = float(request.form.get('glucose', 0))
#         bloodpressure = float(request.form.get('bloodpressure', 0))
#         skinthickness = float(request.form.get('skinthickness', 0))
#         insulin = float(request.form.get('insulin', 0))
#         bmi = float(request.form.get('bmi', 0))
#         dpf = float(request.form.get('dpf', 0))
#         age = float(user['age'])
#         diabetes_input = [pregnancies, glucose, bloodpressure, skinthickness, insulin, bmi, dpf, age]
#         scaled_input = diabetes_scaler.transform([diabetes_input])
#         risk_pred = int(diabetes_model.predict(scaled_input)[0])
#         risk_label = 'High Risk ⚠️' if risk_pred == 1 else 'Low Risk ✅'
#         # SHAP - XGBoost Model
#         explainer = shap.TreeExplainer(diabetes_model)
#         shap_values = explainer.shap_values(scaled_input)
#         vals = shap_values if not isinstance(shap_values, list) else shap_values[1]
#         feature_contrib = zip(DIABETES_FEATURES, vals[0])
#         top_features = sorted(feature_contrib, key=lambda x: abs(x[1]), reverse=True)[:3]
#         explain_data = {f: round(val, 3) for f, val in top_features}
#         recommendations = get_recommendations(bmi, age, {'Diabetes Risk': risk_label})
#         db.execute("INSERT INTO health_data (user_id, disease, result) VALUES (?, ?, ?)",
#                    (user['id'], 'diabetes', risk_label))
#         db.commit()
#         return render_template('result.html', risk_name="Diabetes",
#                               risk_label=risk_label, explain_data=explain_data, recommendations=recommendations)
#     return render_template('form_diabetes.html', user=user)

# @app.route('/predict_heart', methods=['GET', 'POST'])
# def predict_heart():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#     explain_data = None
#     if request.method == 'POST':
#         sex = 1 if user['gender'].lower() == 'male' else 0
#         age = user['age']
#         cp = int(request.form.get('cp', 0))
#         trestbps = float(request.form.get('trestbps', 0))
#         chol = float(request.form.get('chol', 0))
#         exang = int(request.form.get('exang', 0))
#         # Ensure 20 features! Pad remainder to match your scaler/model training
#         heart_input = [age, sex, cp, trestbps, chol, exang] + [0]*14
#         scaled_input = heart_scaler.transform([heart_input])
#         risk_pred = int(heart_model.predict(scaled_input)[0])
#         risk_label = 'High Risk ⚠️' if risk_pred == 1 else 'Low Risk ✅'
        
#         # SHAP - Robust extraction for binary RandomForestClassifier
#         explainer = shap.TreeExplainer(heart_model)
#         shap_values = explainer.shap_values(scaled_input)
#         # (1, 20, 2) array: one sample, 20 features, 2 classes
#         contribs = shap_values[0, :, 1]  # first sample, all features, positive class
#         HEART_FEATURES = ['Age', 'Sex', 'CP', 'Trestbps', 'Chol', 'Exang'] + ['Pad' + str(i) for i in range(1, 15)]
#         feature_contrib = zip(HEART_FEATURES, contribs)
#         top_features = sorted(feature_contrib, key=lambda x: abs(x[1]), reverse=True)[:3]
#         explain_data = {f: round(val, 3) for f, val in top_features}

#         recommendations = get_recommendations(0, age, {'Heart Disease Risk': risk_label})
#         db.execute("INSERT INTO health_data (user_id, disease, result) VALUES (?, ?, ?)",
#                    (user['id'], 'heart', risk_label))
#         db.commit()
#         return render_template('result.html', risk_name="Heart Disease",
#                               risk_label=risk_label, explain_data=explain_data, recommendations=recommendations)
#     return render_template('form_heart.html', user=user)

# @app.route('/predict_kidney', methods=['GET', 'POST'])
# def predict_kidney():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#     explain_data = None
#     if request.method == 'POST':
#         sc = float(request.form.get('sc', 0))
#         bu = float(request.form.get('bu', 0))
#         hemo = float(request.form.get('hemo', 0))
#         age = float(user['age'])
#         bp = float(request.form.get('bp', 0))
#         # Pad for scaler/model length (assumed 24 features total)
#         kidney_input = [sc, bu, hemo, age, bp] + [1]*19
#         scaled_input = kidney_scaler.transform([kidney_input])
#         risk_pred = int(kidney_model.predict(scaled_input)[0])
#         risk_label = 'High Risk ⚠️' if risk_pred == 1 else 'Low Risk ✅'
#         explainer = shap.TreeExplainer(kidney_model)
#         shap_values = explainer.shap_values(scaled_input)
#         vals = shap_values if not isinstance(shap_values, list) else shap_values[1]
#         feature_contrib = zip(KIDNEY_FEATURES, vals[0])
#         top_features = sorted(feature_contrib, key=lambda x: abs(x[1]), reverse=True)[:3]
#         explain_data = {f: round(val, 3) for f, val in top_features}
#         recommendations = get_recommendations(0, age, {'Kidney Disease Risk': risk_label})
#         db.execute("INSERT INTO health_data (user_id, disease, result) VALUES (?, ?, ?)",
#                    (user['id'], 'kidney', risk_label))
#         db.commit()
#         return render_template('result.html', risk_name="Kidney Disease",
#                               risk_label=risk_label, explain_data=explain_data, recommendations=recommendations)
#     return render_template('form_kidney.html', user=user)

# @app.route('/predict_cardio', methods=['GET', 'POST'])
# def predict_cardio():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#     explain_data = None
#     if request.method == 'POST':
#         age = user['age']
#         gender = 1 if user['gender'].lower() == 'male' else 2
#         ap_hi = float(request.form.get('ap_hi', 0))
#         ap_lo = float(request.form.get('ap_lo', 0))
#         cholesterol = int(request.form.get('cholesterol', 0))
#         smoke = int(request.form.get('smoke', 0))
#         # Pad for scaler/model length (assumed 11 features total)
#         cardio_input = [age, gender, ap_hi, ap_lo, cholesterol, smoke] + [0]*5
#         scaled_input = cardio_scaler.transform([cardio_input])
#         risk_pred = int(cardio_model.predict(scaled_input)[0])
#         risk_label = 'High Risk ⚠️' if risk_pred == 1 else 'Low Risk ✅'
#         explainer = shap.TreeExplainer(cardio_model)
#         shap_values = explainer.shap_values(scaled_input)
#         vals = shap_values if not isinstance(shap_values, list) else shap_values[1]
#         feature_contrib = zip(CARDIO_FEATURES, vals[0])
#         top_features = sorted(feature_contrib, key=lambda x: abs(x[1]), reverse=True)[:3]
#         explain_data = {f: round(val, 3) for f, val in top_features}
#         recommendations = get_recommendations(0, age, {'Cardiovascular Risk': risk_label})
#         db.execute("INSERT INTO health_data (user_id, disease, result) VALUES (?, ?, ?)",
#                    (user['id'], 'cardio', risk_label))
#         db.commit()
#         return render_template('result.html', risk_name="Cardiovascular",
#                               risk_label=risk_label, explain_data=explain_data, recommendations=recommendations)
#     return render_template('form_cardio.html', user=user)

# @app.route('/history')
# def history():
#     if 'user_id' not in session:
#         return redirect('/login')
#     db = get_db()
#     history = db.execute("""
#         SELECT created_at, disease, result, glucose, bmi, pregnancies, dpf,
#                cp, trestbps, chol, exang, sc, bu, hemo, bp, ap_hi, ap_lo, cholesterol, smoke
#         FROM health_data
#         WHERE user_id=?
#         ORDER BY created_at DESC
#     """, (session['user_id'],)).fetchall()
#     user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
#     return render_template('history.html', user=user, history=history)

# if __name__ == "__main__":
#     app.run(debug=True)
