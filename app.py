import os
import csv

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from functools import wraps
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

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
        # First check if user is logged in via session
        if 'logged_in' in session:
            # Add cache control headers to prevent caching of protected pages
            response = make_response(f(*args, **kwargs))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Frame-Options'] = 'DENY'  # Prevent clickjacking
            return response
        
        # If not logged in via session, check for remember me cookie
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            # Verify the token (in this case, it's just the username)
            user = users_collection.find_one({'username': remember_token})
            if user:
                # Log the user in by setting session variables
                session['logged_in'] = True
                session['username'] = remember_token
                session['current_group'] = session.get('current_group', None)
                # Add cache control headers to prevent caching of protected pages
                response = make_response(f(*args, **kwargs))
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['X-Frame-Options'] = 'DENY'  # Prevent clickjacking
                return response
        
        # If neither session nor cookie is valid, redirect to login
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
    # Weekend Exam (avg)
    try:
        weekend_avg = float(student.get('weekend_exam', 0))
    except:
        weekend_avg = 0
    if weekend_avg < 50:
        red_zone_fields.append('weekend_exam')
    elif weekend_avg < 75:
        average_fields.append('weekend_exam')
    # Mid Marks (avg)
    try:
        mid_avg = float(student.get('mid_marks', 0))
    except:
        mid_avg = 0
    if mid_avg < 50:
        red_zone_fields.append('mid_marks')
    elif mid_avg < 75:
        average_fields.append('mid_marks')
    # CRT Score (%)
    try:
        crt = float(student.get('crt_score', 0))
    except:
        crt = 0
    if crt < 50:
        red_zone_fields.append('crt_score')
    elif crt < 70:
        average_fields.append('crt_score')
    # Attendance (%)
    try:
        att = float(student.get('attendance_percent', 0))
    except:
        att = 0
    if att < 70:
        red_zone_fields.append('attendance_percent')
    elif att < 80:
        average_fields.append('attendance_percent')
    # GD Attendance (%)
    try:
        gd = float(student.get('gd_attendance', 0))
    except:
        gd = 0
    if gd < 40:
        red_zone_fields.append('gd_attendance')
    elif gd < 70:
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
    # Backlogs
    try:
        backlogs = int(student.get('backlogs', 0))
    except:
        backlogs = 0
    if backlogs > 0:
        red_zone_fields.append('backlogs')
    # Extra Activities
    try:
        extra = int(student.get('extra_activities_score', 0))
    except:
        extra = 0
    if extra == 0:
        red_zone_fields.append('extra_activities_score')
    # Projects Completed
    try:
        projects = int(student.get('project_count', 0))
    except:
        projects = 0
    if projects == 0:
        red_zone_fields.append('project_count')
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
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')  # Get the remember me checkbox value
        
        # Check if user exists in database
        user = users_collection.find_one({'username': username, 'password': password})
        
        if user:
            session['logged_in'] = True
            session['username'] = username
            # Load last selected group from session or default to None
            session['current_group'] = session.get('current_group', None)
            
            # Handle "Remember Me" functionality
            if remember:
                # Set a cookie that expires in 30 days
                response = make_response(redirect(url_for('index')))
                response.set_cookie('remember_token', username, max_age=30*24*60*60)
                # Add security headers
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['X-Frame-Options'] = 'DENY'
                return response
            else:
                # Clear the remember token cookie if it exists
                response = make_response(redirect(url_for('index')))
                response.set_cookie('remember_token', '', expires=0)
                # Add security headers
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['X-Frame-Options'] = 'DENY'
                return response
        else:
            # Check hardcoded credentials for backward compatibility
            # Only allow this if there's no user with username 'Mahesh' in the database
            if username == 'Mahesh' and password == 'Mahesh123':
                # Create user in database if not exists
                if not users_collection.find_one({'username': 'Mahesh'}):
                    users_collection.insert_one({
                        'username': 'Mahesh',
                        'password': 'Mahesh123'
                    })
                
                session['logged_in'] = True
                session['username'] = username
                # Load last selected group from session or default to None
                session['current_group'] = session.get('current_group', None)
                
                # Handle "Remember Me" functionality
                if remember:
                    # Set a cookie that expires in 30 days
                    response = make_response(redirect(url_for('index')))
                    response.set_cookie('remember_token', username, max_age=30*24*60*60)
                    # Add security headers
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    response.headers['X-Frame-Options'] = 'DENY'
                    return response
                else:
                    # Clear the remember token cookie if it exists
                    response = make_response(redirect(url_for('index')))
                    response.set_cookie('remember_token', '', expires=0)
                    # Add security headers
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    response.headers['X-Frame-Options'] = 'DENY'
                    return response
            else:
                error = 'Invalid username or password'
                # Add cache control headers to prevent caching of login page with error
                response = make_response(render_template('login.html', error=error))
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['X-Frame-Options'] = 'DENY'
                return response
    # Add cache control headers to prevent caching of login page
    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.route('/logout')
@login_required
def logout():
    # Clear only logged_in to keep current_group in session
    session.pop('logged_in', None)
    # Create response to clear the remember me cookie
    response = make_response(redirect(url_for('login')))
    response.set_cookie('remember_token', '', expires=0)
    # Add security headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.route('/change_credentials', methods=['GET', 'POST'])
@login_required
def change_credentials():
    # Ensure username is in session
    if 'username' not in session:
        # If not, try to get it from the users collection using the default username
        user = users_collection.find_one({'username': 'Mahesh'})
        if user:
            session['username'] = user['username']
        else:
            # Fallback to default username
            session['username'] = 'Mahesh'
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Get current user
        current_user = users_collection.find_one({'username': session['username']})
        
        # Verify current password
        if current_user and current_user['password'] != current_password:
            return render_template('change_credentials.html', error='Current password is incorrect')
        
        # Check if new password and confirmation match
        if new_password and new_password != confirm_password:
            return render_template('change_credentials.html', error='New passwords do not match')
        
        # Prepare update data
        update_data = {}
        if new_username:
            update_data['username'] = new_username
        if new_password:
            update_data['password'] = new_password
        
        # Update user credentials
        if update_data:
            # Update the user document
            users_collection.update_one(
                {'username': session['username']},
                {'$set': update_data}
            )
            
            # Update session username if changed
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
    
    # If not logged in via session, check for remember me cookie
    remember_token = request.cookies.get('remember_token')
    if remember_token:
        # Verify the token (in this case, it's just the username)
        user = users_collection.find_one({'username': remember_token})
        if user:
            # Log the user in by setting session variables
            session['logged_in'] = True
            session['username'] = remember_token
            session['current_group'] = session.get('current_group', None)
            
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
    
    # If neither session nor cookie is valid, redirect to login
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)






print(mongo.db)  # Should not be None
