import os
import csv

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from functools import wraps
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)

app.secret_key = 'supersecretkey'  # Change this in production

# Use only the Atlas MongoDB URI from environment variable
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb+srv://Mahesh_user2:Mahesh-2004@studentscategorizer.xtci9mi.mongodb.net/studentdb')

mongo = PyMongo(app)

# User management collection
users_collection = mongo.db.users

# Use the same connection for all database operations
client = mongo.cx  # Get the underlying PyMongo client
db = mongo.db  # Use the database from PyMongo

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only allow access if logged in via this session
        if 'logged_in' in session:
            response = make_response(f(*args, **kwargs))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        # Redirect to login if not authenticated
        return redirect(url_for('login'))
    return decorated_function

STUDENT_FIELDS = [
    'name', 'weekend_exam', 'mid_marks', 'crt_score', 'attendance_percent', 'gd_attendance',
    'previous_sem_percent', 'extra_activities_score', 'project_count',
    'backlogs'
]

def get_collection(group_name=None):
    if group_name:
        return mongo.db[group_name]
    return mongo.db.students

# --- Categorization Logic ---
def categorize_student(student):
    red_zone_fields = []
    average_fields = []
    # Weekend Exam (avg) — Good ≥ 80, Average 60–79, Red < 60
    try:
        weekend_avg = float(student.get('weekend_exam', 0))
    except:
        weekend_avg = 0
    if weekend_avg < 60:
        red_zone_fields.append('weekend_exam')
    elif weekend_avg < 80:
        average_fields.append('weekend_exam')
    # Mid Marks (avg) — Good ≥ 80, Average 60–79, Red < 60
    try:
        mid_avg = float(student.get('mid_marks', 0))
    except:
        mid_avg = 0
    if mid_avg < 60:
        red_zone_fields.append('mid_marks')
    elif mid_avg < 80:
        average_fields.append('mid_marks')
    # CRT Score (%) — Good ≥ 80, Average 60–79, Red < 60
    try:
        crt = float(student.get('crt_score', 0))
    except:
        crt = 0
    if crt < 60:
        red_zone_fields.append('crt_score')
    elif crt < 80:
        average_fields.append('crt_score')
    # Attendance (%) — Good ≥ 80, Average 70–79, Red < 70
    try:
        att = float(student.get('attendance_percent', 0))
    except:
        att = 0
    if att < 70:
        red_zone_fields.append('attendance_percent')
    elif att < 80:
        average_fields.append('attendance_percent')
    # GD Attendance (%) — Good ≥ 80, Average 70–79, Red < 70
    try:
        gd = float(student.get('gd_attendance', 0))
    except:
        gd = 0
    if gd < 70:
        red_zone_fields.append('gd_attendance')
    elif gd < 80:
        average_fields.append('gd_attendance')
    # Previous Sem GPA
    try:
        prev_gpa = float(student.get('previous_sem_percent', 0))
    except:
        prev_gpa = 0
    if prev_gpa < 7.0:
        red_zone_fields.append('previous_sem_percent')
    elif prev_gpa < 8.0:
        average_fields.append('previous_sem_percent')
    # Backlogs — if any (> 0), student is in Red Zone
    try:
        backlogs = float(student.get('backlogs', 0))
    except:
        backlogs = 0
    if backlogs > 0:
        red_zone_fields.append('backlogs')
    # Extra Activities — Average if none, Good otherwise
    try:
        extra = float(student.get('extra_activities_score', 0))
    except:
        extra = 0
    if extra == 0:
        average_fields.append('extra_activities_score')
    # Projects Completed — Average if none, Good otherwise
    try:
        projects = float(student.get('project_count', 0))
    except:
        projects = 0
    if projects == 0:
        average_fields.append('project_count')
    # Final Zone
    if red_zone_fields:
        return 'Red Zone', red_zone_fields, average_fields
    elif average_fields:
        return 'Average', [], average_fields
    else:
        return 'Good', [], []

# --- Routes ---

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    group = request.args.get('group')
    if not group:
        group = session.get('group', None)
    if group:
        session['group'] = group
    collection = get_collection(group)
    if request.method == 'POST':
        # Add validation for specific fields
        errors = {}
        
        # Validate previous_sem_percent (GPA) - should be <= 10
        try:
            prev_sem_gpa = float(request.form.get('previous_sem_percent', 0))
            if prev_sem_gpa > 10:
                errors['previous_sem_percent'] = "Previous Sem GPA value must be less than or equal to 10"
        except ValueError:
            pass  # Will be handled by existing validation
        
        # Validate extra_activities_score - should be <= 10
        try:
            extra_activities = float(request.form.get('extra_activities_score', 0))
            if extra_activities > 10:
                errors['extra_activities_score'] = "Extra Activities value must be less than or equal to 10"
        except ValueError:
            pass  # Will be handled by existing validation
            
        # Validate project_count - should be <= 10
        try:
            projects = float(request.form.get('project_count', 0))
            if projects > 10:
                errors['project_count'] = "Projects value must be less than or equal to 10"
        except ValueError:
            pass  # Will be handled by existing validation
            
        # Validate backlogs - should be <= 15
        try:
            backlogs = float(request.form.get('backlogs', 0))
            if backlogs > 15:
                errors['backlogs'] = "Backlogs value must be less than or equal to 15"
        except ValueError:
            pass  # Will be handled by existing validation
            
        # If there are validation errors, display them
        if errors:
            # Pass form data back to populate fields
            form_data = {field: request.form.get(field, '') for field in STUDENT_FIELDS}
            return render_template('add_student.html', fields=STUDENT_FIELDS, group=group, errors=errors, form_data=form_data)
            
        data = {field: request.form.get(field) for field in STUDENT_FIELDS}
        zone, red, avg = categorize_student(data)
        data['zone'] = zone
        data['red_zone_fields'] = red
        data['average_fields'] = avg
        collection.insert_one(data)
        flash('Student added!')
        return redirect(url_for('index', group=group))
    return render_template('add_student.html', fields=STUDENT_FIELDS, group=group)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Placeholder for OCR upload logic
    return render_template('upload.html')

@app.route('/csv_upload', methods=['GET', 'POST'])
def csv_upload():
    # Placeholder for CSV upload logic
    return render_template('csv_upload.html')

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        try:
            num_subjects = int(request.form.get('num_subjects', 0))
            marks_obtained = []
            max_marks_list = []
            subject_names = []
            for i in range(num_subjects):
                subject_name = request.form.get(f'subject_name_{i}', '')
                subject_names.append(subject_name)
                mark = request.form.get(f'mark_{i}', '')
                max_mark = request.form.get(f'max_mark_{i}', '')
                mark_val = float(mark) if mark != '' else 0
                max_mark_val = float(max_mark) if max_mark != '' else 0
                marks_obtained.append(mark_val)
                max_marks_list.append(max_mark_val)
            total_obtained = sum(marks_obtained)
            total_max = sum(max_marks_list)
            percentage = (total_obtained * 100) / total_max if total_max > 0 else 0
            return render_template('calculator.html', percentage=percentage, num_subjects=num_subjects, marks_obtained=marks_obtained, max_marks_list=max_marks_list, subject_names=subject_names)
        except Exception as e:
            error = str(e)
            return render_template('calculator.html', error=error)
    else:
        # Do not show any message about creating students here
        return render_template('calculator.html', percentage=None)

@app.route('/categorization')
def categorization():
    return render_template('categorization.html')

@app.route('/api/students', methods=['GET'])
def api_get_students():
    group = request.args.get('group')
    collection = get_collection(group)
    students = list(collection.find())
    for s in students:
        s['id'] = str(s['_id'])
        zone, red, avg = categorize_student(s)
        s['zone'] = zone
        s['red_zone_fields'] = red
        s['average_fields'] = avg
        s.pop('_id', None)
    return jsonify({'students': students})

@app.route('/api/students', methods=['POST'])
def api_add_student():
    group = request.args.get('group')
    collection = get_collection(group)
    
    # Add validation for specific fields
    errors = []
    
    # Validate previous_sem_percent (GPA) - should be <= 10
    try:
        prev_sem_gpa = float(request.form.get('previous_sem_percent', 0))
        if prev_sem_gpa > 10:
            errors.append("Previous Sem GPA value must be less than or equal to 10")
    except ValueError:
        pass  # Will be handled by existing validation
    
    # Validate extra_activities_score - should be <= 10
    try:
        extra_activities = float(request.form.get('extra_activities_score', 0))
        if extra_activities > 10:
            errors.append("Extra Activities value must be less than or equal to 10")
    except ValueError:
        pass  # Will be handled by existing validation
        
    # Validate project_count - should be <= 10
    try:
        projects = float(request.form.get('project_count', 0))
        if projects > 10:
            errors.append("Projects value must be less than or equal to 10")
    except ValueError:
        pass  # Will be handled by existing validation
        
    # Validate backlogs - should be <= 15
    try:
        backlogs = float(request.form.get('backlogs', 0))
        if backlogs > 15:
            errors.append("Backlogs value must be less than or equal to 15")
    except ValueError:
        pass  # Will be handled by existing validation
        
    # If there are validation errors, return them
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    
    data = {field: request.form.get(field) for field in STUDENT_FIELDS}
    zone, red, avg = categorize_student(data)
    data['zone'] = zone
    collection.insert_one(data)
    return jsonify({'success': True})

@app.route('/api/students/<id>', methods=['DELETE'])
def api_delete_student(id):
    group = request.args.get('group')
    collection = get_collection(group)
    collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

@app.route('/api/students/<id>', methods=['PUT'])
def api_update_student(id):
    group = request.args.get('group')
    collection = get_collection(group)
    
    # Add validation for specific fields
    errors = []
    
    # Validate previous_sem_percent (GPA) - should be <= 10
    try:
        prev_sem_gpa = float(request.form.get('previous_sem_percent', 0))
        if prev_sem_gpa > 10:
            errors.append("Previous Sem GPA value must be less than or equal to 10")
    except ValueError:
        pass  # Will be handled by existing validation
    
    # Validate extra_activities_score - should be <= 10
    try:
        extra_activities = float(request.form.get('extra_activities_score', 0))
        if extra_activities > 10:
            errors.append("Extra Activities value must be less than or equal to 10")
    except ValueError:
        pass  # Will be handled by existing validation
        
    # Validate project_count - should be <= 10
    try:
        projects = float(request.form.get('project_count', 0))
        if projects > 10:
            errors.append("Projects value must be less than or equal to 10")
    except ValueError:
        pass  # Will be handled by existing validation
        
    # Validate backlogs - should be <= 15
    try:
        backlogs = float(request.form.get('backlogs', 0))
        if backlogs > 15:
            errors.append("Backlogs value must be less than or equal to 15")
    except ValueError:
        pass  # Will be handled by existing validation
        
    # If there are validation errors, return them
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    
    # Get the updated data from the request
    data = {field: request.form.get(field) for field in STUDENT_FIELDS}
    
    # Recalculate zone based on updated data
    zone, red, avg = categorize_student(data)
    data['zone'] = zone
    data['red_zone_fields'] = red
    data['average_fields'] = avg
    
    # Update the student in the database
    collection.update_one(
        {'_id': ObjectId(id)},
        {'$set': data}
    )
    
    # Return the updated student data
    updated_student = collection.find_one({'_id': ObjectId(id)})
    updated_student['id'] = str(updated_student['_id'])
    updated_student.pop('_id', None)
    
    return jsonify({'success': True, 'student': updated_student})


@app.route('/api/groups', methods=['GET'])
def api_get_groups():
    # List all collections in the database as groups
    collections = mongo.db.list_collection_names()
    # Filter out system collections if any
    groups = [c for c in collections if not c.startswith('system.')]
    return jsonify({'groups': groups})

@app.route('/api/groups', methods=['POST'])
def api_create_group():
    group_name = request.form.get('group_name')
    if not group_name:
        return jsonify({'success': False, 'error': 'Group name is required'}), 400
    # Create collection by inserting a dummy document and deleting it
    collection = mongo.db[group_name]
    collection.insert_one({'init': True})
    collection.delete_many({'init': True})
    return jsonify({'success': True, 'group': group_name})

@app.route('/api/groups/<group_name>', methods=['DELETE'])
def api_delete_group(group_name):
    if not group_name:
        return jsonify({'success': False, 'error': 'Group name is required'}), 400
    # Drop the collection to delete the group and its data
    if group_name in mongo.db.list_collection_names():
        mongo.db.drop_collection(group_name)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Group not found'}), 404

@app.route('/zone/<zone>')
def zone_students(zone):
    students = list(mongo.db.students.find({'zone': zone}))
    for s in students:
        s['zone'], s['red_zone_fields'], s['average_fields'] = categorize_student(s)
    return render_template('index.html', students=students)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # 1) Look up user in users collection
        user = users_collection.find_one({'username': username})

        # Back-compat: migrate plain password -> password_hash if found
        if user and 'password' in user and 'password_hash' not in user:
            if user['password'] == password:
                users_collection.update_one({'_id': user['_id']}, {'$set': {'password_hash': generate_password_hash(password)}, '$unset': {'password': ''}})
                user = users_collection.find_one({'_id': user['_id']})

        if user and 'password_hash' in user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session['current_group'] = session.get('current_group', None)
            response = make_response(redirect(url_for('index')))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Frame-Options'] = 'DENY'
            return response

        # 2) Default: allow login using a student name (username == student.name and password == same name)
        student = mongo.db.students.find_one({'name': username})
        if student and password == username:
            # Create a corresponding user with hashed default password = student's name
            users_collection.insert_one({
                'username': username,
                'password_hash': generate_password_hash(password)
            })
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session['current_group'] = session.get('current_group', None)
            response = make_response(redirect(url_for('index')))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Frame-Options'] = 'DENY'
            return response

        # Invalid
        error = 'Invalid username or password'
        response = make_response(render_template('login.html', error=error))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.route('/logout')
@login_required
def logout():
    # Fully clear the session and any auth cookies to force revalidation next login
    session.clear()
    response = make_response(redirect(url_for('login')))
    response.set_cookie('remember_token', '', expires=0)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.route('/change_credentials', methods=['GET', 'POST'])
@login_required
def change_credentials():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_username = (request.form.get('new_username') or '').strip()
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        current_user = users_collection.find_one({'username': session['username']})
        if not current_user:
            return render_template('change_credentials.html', error='User not found')

        # Verify current password against hash (support legacy plain password)
        valid_current = False
        if 'password_hash' in current_user:
            valid_current = check_password_hash(current_user['password_hash'], current_password)
        elif 'password' in current_user:
            valid_current = (current_user['password'] == current_password)
        if not valid_current:
            return render_template('change_credentials.html', error='Current password is incorrect')

        if new_password and new_password != confirm_password:
            return render_template('change_credentials.html', error='New passwords do not match')

        update_data = {}
        old_username = current_user['username']
        if new_username:
            # Ensure target username not already taken
            if users_collection.find_one({'username': new_username, '_id': {'$ne': current_user['_id']}}):
                return render_template('change_credentials.html', error='Username already taken')
            update_data['username'] = new_username
        if new_password:
            update_data['password_hash'] = generate_password_hash(new_password)
            # If legacy field exists, remove it
            update = {'$set': update_data, '$unset': {'password': ''}}
        else:
            update = {'$set': update_data}

        if update_data:
            users_collection.update_one({'_id': current_user['_id']}, update)

            # Optionally sync student name if it uniquely matches old username
            if new_username:
                matching = list(mongo.db.students.find({'name': old_username}))
                if len(matching) == 1:
                    mongo.db.students.update_one({'_id': matching[0]['_id']}, {'$set': {'name': new_username}})

            if new_username:
                session['username'] = new_username

            return render_template('change_credentials.html', success='Credentials updated successfully')
        else:
            return render_template('change_credentials.html', error='No changes provided')

    return render_template('change_credentials.html')

@app.route('/')
def index():
    # Check if user is logged in via session
    if 'logged_in' in session:
        group = session.get('current_group', None)
        if group:
            session['group'] = group
        collection = get_collection(group)
        students = list(collection.find())
        for s in students:
            zone, red, avg = categorize_student(s)
            s['zone'] = zone
            s['red_zone_fields'] = red
            s['average_fields'] = avg
        # Add cache control headers to prevent caching of protected pages
        response = make_response(render_template('index.html', students=students, group=group))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Frame-Options'] = 'DENY'
        return response
    
    # Not logged in — redirect to login (no cookie auto-login)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)






print(mongo.db)  # Should not be None
