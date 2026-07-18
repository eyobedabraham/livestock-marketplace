from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-it-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder for photos
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Allowed extensions for photos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # cow, ox, goat, sheep, dairy
    breed = db.Column(db.String(100))
    gender = db.Column(db.String(20))
    age = db.Column(db.Integer)  # in years
    weight = db.Column(db.Float)  # in kg
    height = db.Column(db.Float)  # in cm (optional)
    price = db.Column(db.Float, nullable=False)  # in ETB
    description = db.Column(db.Text)
    location = db.Column(db.String(100), nullable=False)
    health_status = db.Column(db.String(20), default='Healthy')
    vaccinated = db.Column(db.String(10), default='No')
    photo = db.Column(db.String(200))          # Main photo
    photo_side = db.Column(db.String(200))     # Side view
    photo_front = db.Column(db.String(200))    # Front view
    photo_top = db.Column(db.String(200))      # Top view
    milk_production = db.Column(db.Float)      # L/day (dairy cows)
    feed_type = db.Column(db.String(100))
    feed_amount = db.Column(db.Float)          # kg/day
    lactating = db.Column(db.String(10))
    pregnant = db.Column(db.String(10))
    phone_number = db.Column(db.String(20), default='0940293477')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    
    query = Listing.query
    
    if search_query:
        query = query.filter(
            db.or_(
                Listing.title.contains(search_query),
                Listing.breed.contains(search_query),
                Listing.location.contains(search_query)
            )
        )
    
    if category_filter:
        query = query.filter(Listing.category == category_filter)
    
    listings = query.order_by(Listing.created_at.desc()).all()
    return render_template('index.html', listings=listings, current_user=current_user)

@app.route('/listing/<int:id>')
def listing_detail(id):
    listing = Listing.query.get_or_404(id)
    return render_template('listing.html', listing=listing)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template('admin_dashboard.html', listings=listings)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_listing():
    if request.method == 'POST':
        # Helper to save uploaded file
        def save_photo(file_key):
            if file_key in request.files:
                file = request.files[file_key]
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    new_filename = timestamp + filename
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                    return new_filename
            return None

        photo = save_photo('photo')
        photo_side = save_photo('photo_side')
        photo_front = save_photo('photo_front')
        photo_top = save_photo('photo_top')

        category = request.form['category']
        listing = Listing(
            title=request.form['title'],
            category=category,
            breed=request.form.get('breed', ''),
            gender=request.form.get('gender', ''),
            age=int(request.form.get('age', 0)),
            weight=float(request.form.get('weight', 0)),
            height=float(request.form.get('height', 0)) if request.form.get('height') else None,
            price=float(request.form['price']),
            description=request.form.get('description', ''),
            location=request.form['location'],
            health_status=request.form.get('health_status', 'Healthy'),
            vaccinated=request.form.get('vaccinated', 'No'),
            photo=photo,
            photo_side=photo_side,
            photo_front=photo_front,
            photo_top=photo_top,
            phone_number=request.form.get('phone_number', '0940293477')
        )

        if category == 'cow':
            listing.milk_production = float(request.form.get('milk_production', 0)) if request.form.get('milk_production') else None
            listing.feed_type = request.form.get('feed_type', '')
            listing.feed_amount = float(request.form.get('feed_amount', 0)) if request.form.get('feed_amount') else None
            listing.lactating = request.form.get('lactating', 'No')
            listing.pregnant = request.form.get('pregnant', 'No')

        db.session.add(listing)
        db.session.commit()
        flash('Listing added successfully!')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_listing.html')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_listing(id):
    listing = Listing.query.get_or_404(id)
    if request.method == 'POST':
        # Helper to update photo (deletes old if exists)
        def update_photo(file_key, current_filename):
            if file_key in request.files:
                file = request.files[file_key]
                if file and allowed_file(file.filename):
                    if current_filename:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_filename)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    new_filename = timestamp + filename
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                    return new_filename
            return current_filename

        listing.photo = update_photo('photo', listing.photo)
        listing.photo_side = update_photo('photo_side', listing.photo_side)
        listing.photo_front = update_photo('photo_front', listing.photo_front)
        listing.photo_top = update_photo('photo_top', listing.photo_top)

        listing.title = request.form['title']
        listing.category = request.form['category']
        listing.breed = request.form.get('breed', '')
        listing.gender = request.form.get('gender', '')
        listing.age = int(request.form.get('age', 0))
        listing.weight = float(request.form.get('weight', 0))
        listing.height = float(request.form.get('height', 0)) if request.form.get('height') else None
        listing.price = float(request.form['price'])
        listing.description = request.form.get('description', '')
        listing.location = request.form['location']
        listing.health_status = request.form.get('health_status', 'Healthy')
        listing.vaccinated = request.form.get('vaccinated', 'No')
        listing.phone_number = request.form.get('phone_number', '0940293477')

        if listing.category == 'cow':
            listing.milk_production = float(request.form.get('milk_production', 0)) if request.form.get('milk_production') else None
            listing.feed_type = request.form.get('feed_type', '')
            listing.feed_amount = float(request.form.get('feed_amount', 0)) if request.form.get('feed_amount') else None
            listing.lactating = request.form.get('lactating', 'No')
            listing.pregnant = request.form.get('pregnant', 'No')

        db.session.commit()
        flash('Listing updated successfully!')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_listing.html', listing=listing)

@app.route('/admin/delete/<int:id>')
@login_required
def delete_listing(id):
    listing = Listing.query.get_or_404(id)
    for field in ['photo', 'photo_side', 'photo_front', 'photo_top']:
        filename = getattr(listing, field)
        if filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path):
                os.remove(path)
    db.session.delete(listing)
    db.session.commit()
    flash('Listing deleted successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def create_admin():
    with app.app_context():
        if not User.query.filter_by(username='eyobed').first():
            admin = User(username='eyobed')
            admin.set_password('913421156')
            db.session.add(admin)
            db.session.commit()
            print("Admin created: eyobed / 913421156")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=False, host='0.0.0.0', port=5000)
