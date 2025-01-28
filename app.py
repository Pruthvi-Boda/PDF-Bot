from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from pdf_processor import PDFBot
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
import os
from dotenv import load_dotenv
import time
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Set a secure secret key
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdfbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure CORS is properly handled
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

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
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        # Check if a file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
            
        file = request.files['file']
        
        # Check if a file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
            
        # Check file extension
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Only PDF files are allowed'
            }), 400
            
        # Create upload directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        # Secure the filename and get full path
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file in chunks to handle large files
        chunk_size = 8192  # 8KB chunks
        with open(filepath, 'wb') as f:
            while True:
                chunk = file.stream.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        # Initialize PDFBot if needed
        global pdf_bot
        if pdf_bot is None:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError('Google API key not found')
            pdf_bot = PDFBot(api_key)
            
        # Process the PDF in the background
        def process_pdf_async():
            try:
                pdf_bot.process_pdf(filepath)
            except Exception as e:
                print(f"Error processing PDF: {str(e)}")
                
        thread = threading.Thread(target=process_pdf_async)
        thread.daemon = True
        thread.start()
        
        # Return success response immediately
        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        # Clean up file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        return jsonify({
            'success': False,
            'error': 'An error occurred while uploading the file'
        }), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.get_json()
        message = data.get('message')
        filename = data.get('filename')
        
        if not message or not filename:
            return jsonify({
                'success': False,
                'error': 'Missing message or filename'
            }), 400
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'PDF file not found'
            }), 404
            
        # Initialize PDFBot if needed
        global pdf_bot
        if pdf_bot is None:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError('Google API key not found')
            pdf_bot = PDFBot(api_key)
            
        # Get response from PDFBot
        response = pdf_bot.chat(filepath, message)
        
        if not response:
            return jsonify({
                'success': False,
                'error': 'Failed to generate response'
            }), 500
            
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your message'
        }), 500

@app.route('/summarize', methods=['POST'])
@login_required
def summarize():
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'error': 'No filename provided'}), 400
            
        filename = secure_filename(data['filename'])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
        if not pdf_bot:
            return jsonify({'success': False, 'error': 'PDF processor not initialized'}), 500
            
        summary = pdf_bot.get_summary(filepath)
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        print(f"Summarize error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while summarizing the PDF. Please try again.'
        }), 500

@app.route('/key-points', methods=['POST'])
@login_required
def key_points():
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'error': 'No filename provided'}), 400
            
        filename = secure_filename(data['filename'])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
        if not pdf_bot:
            return jsonify({'success': False, 'error': 'PDF processor not initialized'}), 500
            
        key_points = pdf_bot.get_key_points(filepath)
        return jsonify({
            'success': True,
            'key_points': key_points
        })
        
    except Exception as e:
        print(f"Key points error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while extracting key points from the PDF. Please try again.'
        }), 500

@app.route('/get-pdfs', methods=['GET'])
@login_required
def get_pdfs():
    try:
        # Create upload folder if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        # Get all PDF files in the upload directory
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.lower().endswith('.pdf'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                files.append({
                    'name': filename,
                    'added': os.path.getctime(filepath),
                    'size': os.path.getsize(filepath),
                    'path': filepath
                })
        
        # Sort files by date added (newest first)
        files.sort(key=lambda x: x['added'], reverse=True)
        
        # Convert timestamps to readable format
        for file in files:
            file['added'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file['added']))
            file['size'] = f"{file['size'] / (1024*1024):.2f} MB"
        
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        print(f"Get PDFs error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while retrieving PDFs. Please try again.'
        }), 500

@app.route('/delete-pdf', methods=['POST'])
@login_required
def delete_pdf():
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            }), 400
            
        # Get the full path to the PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'error': 'PDF file not found'
            }), 404
            
        try:
            # Delete the file
            os.remove(pdf_path)
            
            # Delete any cached data for this PDF
            cache_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cache', filename + '.json')
            if os.path.exists(cache_path):
                os.remove(cache_path)
            
            return jsonify({
                'success': True,
                'message': 'PDF deleted successfully'
            })
            
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to delete the PDF file'
            }), 500
            
    except Exception as e:
        print(f"Error in delete-pdf: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@app.route('/explain-document', methods=['POST'])
@login_required
def explain_document():
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            }), 400
            
        # Get the full path to the PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'error': 'PDF file not found'
            }), 404
            
        # Use the PDF processor to get the text
        try:
            text = pdf_bot.extract_text_with_ocr(pdf_path)
            
            # Create a prompt for the explanation
            prompt = f"""Please provide a clear and concise explanation of the following document. 
            Focus on the main topics, key points, and any important conclusions:
            
            {text[:3000]}  # Limit text to prevent token overflow
            
            If this is part of a longer document, I've focused on the beginning. Let me know if you'd like to explore other parts."""
            
            # Get explanation from Gemini
            response = pdf_bot.llm.invoke(prompt).content
            
            return jsonify({
                'success': True,
                'explanation': response
            })
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to process the PDF. Please make sure it contains readable text.'
            }), 500
            
    except Exception as e:
        print(f"Error in explain-document: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@app.route('/key-insights', methods=['POST'])
@login_required
def key_insights():
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Missing filename'
            }), 400
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
            
        # Initialize PDFBot if needed
        global pdf_bot
        if pdf_bot is None:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError('Google API key not found')
            pdf_bot = PDFBot(api_key)
            
        # Get key insights
        insights = pdf_bot.get_key_insights(filepath)
        
        if not insights:
            return jsonify({
                'success': False,
                'error': 'Failed to generate insights'
            }), 500
            
        return jsonify({
            'success': True,
            'insights': insights
        })
        
    except Exception as e:
        print(f"Key insights error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting key insights'
        }), 500

@app.route('/summary', methods=['POST'])
@login_required
def get_summary():
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Missing filename'
            }), 400
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
            
        # Initialize PDFBot if needed
        global pdf_bot
        if pdf_bot is None:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError('Google API key not found')
            pdf_bot = PDFBot(api_key)
            
        # Get summary
        summary = pdf_bot.get_summary(filepath)
        
        if not summary:
            return jsonify({
                'success': False,
                'error': 'Failed to generate summary'
            }), 500
            
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        print(f"Summary error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while generating summary'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
