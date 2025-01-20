from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pdf_processor import PDFBot
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdfbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database
db.init_app(app)

# Ensure the instance folder exists
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        print("Database created successfully!")

init_db()

# Initialize global PDF-Bot instance
pdf_bot = None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember_me') == 'on'
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('signup.html')
        
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    global pdf_bot
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Initialize PDF-Bot with the uploaded file
        pdf_bot = PDFBot()
        pdf_bot.load_pdf(filepath)
        
        return jsonify({'message': 'File uploaded successfully'})
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    global pdf_bot
    if not pdf_bot:
        return jsonify({'error': 'Please upload a PDF first'}), 400
    
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        response = pdf_bot.chat(data['message'])
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summarize')
@login_required
def summarize():
    global pdf_bot
    if not pdf_bot:
        return jsonify({'error': 'Please upload a PDF first'}), 400
    
    try:
        summary = pdf_bot.summarize()
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/key_points')
@login_required
def key_points():
    global pdf_bot
    if not pdf_bot:
        return jsonify({'error': 'Please upload a PDF first'}), 400
    
    try:
        points = pdf_bot.extract_key_points()
        return jsonify({'key_points': points})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
