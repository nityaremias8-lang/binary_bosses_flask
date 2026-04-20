# imports from flask
from datetime import datetime
from urllib.parse import urljoin, urlparse
from flask import abort, redirect, render_template, request, send_from_directory, url_for, jsonify, current_app, g
from flask_login import current_user, login_user, logout_user
from flask.cli import AppGroup
from flask_login import current_user, login_required
from flask import current_app
from dotenv import load_dotenv
# Add this with your other imports
from flask_cors import CORS

# import "objects" from "this" project
from __init__ import app, db, login_manager  # Key Flask objects 
# API endpoints
from api.user import user_api 
from api.python_exec_api import python_exec_api
from api.javascript_exec_api import javascript_exec_api
from api.section import section_api
from api.persona_api import persona_api
from api.pfp import pfp_api
from api.analytics import analytics_api
from api.student import student_api
from api.groq_api import groq_api
from api.gemini_api import gemini_api
from api.microblog_api import microblog_api
from api.classroom_api import classroom_api
from api.data_export_import_api import data_export_import_api
from hacks.joke import joke_api
from api.post import post_api
from api.titanic import titanic_api

# database Initialization functions
from model.user import User, initUsers
from model.user import Section
from model.github import GitHubUser
from model.feedback import Feedback
from api.analytics import get_date_range
from api.study import study_api
from api.feedback_api import feedback_api
from model.study import Study, initStudies
from model.classroom import Classroom
from model.persona import Persona, initPersonas, initPersonaUsers
from model.post import Post, init_posts
from model.microblog import MicroBlog, Topic, initMicroblogs
from hacks.jokes import initJokes
from model.titanic import initTitanic
from chatbot import chatbot_bp, init_db

# New imports for volunteer systems
import sqlite3
import json
import uuid
import os
import requests
from datetime import datetime, timedelta

# After app is created, add this line
CORS(app)

CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:4500",
            "http://127.0.0.1:4500",
            "http://localhost:8376",
            "http://127.0.0.1:8376"
        ]
    }
})

# Load environment variables
load_dotenv()

app.config['KASM_SERVER'] = os.getenv('KASM_SERVER')
app.config['KASM_API_KEY'] = os.getenv('KASM_API_KEY')
app.config['KASM_API_KEY_SECRET'] = os.getenv('KASM_API_KEY_SECRET')

# ============================================================================
# BINGO VOLUNTEER DATABASE SYSTEM
# ============================================================================

class BingoVolunteerDB:
    """Database for Bingo volunteer signups and management"""
    
    def __init__(self):
        self.db_path = "bingo_volunteers.db"
        self.init_database()
    
    def init_database(self):
        """Create database tables for volunteer management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                tshirt_size TEXT,
                availability TEXT,
                experience TEXT,
                notes TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteer_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                time_preference TEXT,
                FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteer_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                role_name TEXT NOT NULL,
                FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteer_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                shift_date DATE NOT NULL,
                shift_type TEXT,
                role TEXT,
                check_in_time TIMESTAMP,
                check_out_time TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_volunteer_id ON volunteers(volunteer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_volunteer_email ON volunteers(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_volunteer_status ON volunteers(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedule_date ON volunteer_schedule(shift_date)')
        
        conn.commit()
        conn.close()
        print(" Bingo Volunteer Database initialized")
    
    def add_volunteer(self, volunteer_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            volunteer_id = str(uuid.uuid4())[:8]
            
            cursor.execute('''
                INSERT INTO volunteers (
                    volunteer_id, first_name, last_name, email, phone, address,
                    emergency_contact_name, emergency_contact_phone, tshirt_size,
                    availability, experience, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                volunteer_id,
                volunteer_data.get('first_name'),
                volunteer_data.get('last_name'),
                volunteer_data.get('email'),
                volunteer_data.get('phone'),
                volunteer_data.get('address'),
                volunteer_data.get('emergency_contact_name'),
                volunteer_data.get('emergency_contact_phone'),
                volunteer_data.get('tshirt_size'),
                volunteer_data.get('availability'),
                volunteer_data.get('experience'),
                volunteer_data.get('notes'),
                'pending'
            ))
            
            availability_days = volunteer_data.get('availability_days', [])
            if availability_days:
                for day in availability_days:
                    cursor.execute('INSERT INTO volunteer_availability (volunteer_id, day_of_week) VALUES (?, ?)', (volunteer_id, day))
            
            preferred_roles = volunteer_data.get('preferred_roles', [])
            if preferred_roles:
                for role in preferred_roles:
                    cursor.execute('INSERT INTO volunteer_roles (volunteer_id, role_name) VALUES (?, ?)', (volunteer_id, role))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'volunteer_id': volunteer_id, 'message': 'Volunteer application submitted successfully!'}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'A volunteer with this email may already exist.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_volunteer(self, volunteer_id=None, email=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if volunteer_id:
                cursor.execute('SELECT * FROM volunteers WHERE volunteer_id = ?', (volunteer_id,))
            elif email:
                cursor.execute('SELECT * FROM volunteers WHERE email = ?', (email,))
            else:
                conn.close()
                return {'success': False, 'error': 'No volunteer_id or email provided'}
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {'success': False, 'error': 'Volunteer not found'}
            
            columns = [desc[0] for desc in cursor.description]
            volunteer = dict(zip(columns, row))
            
            cursor.execute('SELECT day_of_week FROM volunteer_availability WHERE volunteer_id = ?', (volunteer_id,))
            volunteer['availability_days'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute('SELECT role_name FROM volunteer_roles WHERE volunteer_id = ?', (volunteer_id,))
            volunteer['preferred_roles'] = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return {'success': True, 'volunteer': volunteer}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_volunteers(self, status=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if status:
                cursor.execute('SELECT * FROM volunteers WHERE status = ? ORDER BY created_at DESC', (status,))
            else:
                cursor.execute('SELECT * FROM volunteers ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            volunteers = []
            for row in rows:
                volunteer = dict(zip(columns, row))
                volunteers.append(volunteer)
            
            conn.close()
            return {'success': True, 'count': len(volunteers), 'volunteers': volunteers}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_volunteer_status(self, volunteer_id, status):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE volunteers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE volunteer_id = ?', (status, volunteer_id))
            conn.commit()
            conn.close()
            return {'success': True, 'message': f'Volunteer status updated to {status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_volunteer(self, volunteer_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM volunteers WHERE volunteer_id = ?', (volunteer_id,))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Volunteer deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_volunteer_stats(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM volunteers')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT status, COUNT(*) FROM volunteers GROUP BY status')
            status_counts = dict(cursor.fetchall())
            conn.close()
            return {'success': True, 'stats': {'total_volunteers': total, 'by_status': status_counts}}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================================
# RERUNS SHOPPE VOLUNTEER DATABASE SYSTEM
# ============================================================================

class ReRunsVolunteerDB:
    """Database for ReRuns Shoppe volunteer signups and management"""
    
    def __init__(self):
        self.db_path = "reruns_volunteers.db"
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reruns_volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                availability TEXT,
                preferred_roles TEXT,
                experience TEXT,
                program TEXT DEFAULT 'ReRuns Shoppe',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reruns_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                FOREIGN KEY (volunteer_id) REFERENCES reruns_volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reruns_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                role_name TEXT NOT NULL,
                FOREIGN KEY (volunteer_id) REFERENCES reruns_volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reruns_volunteer_id ON reruns_volunteers(volunteer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reruns_email ON reruns_volunteers(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reruns_status ON reruns_volunteers(status)')
        
        conn.commit()
        conn.close()
        print(" ReRuns Shoppe Volunteer Database initialized")
    
    def add_volunteer(self, volunteer_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            volunteer_id = str(uuid.uuid4())[:8]
            
            cursor.execute('''
                INSERT INTO reruns_volunteers (
                    volunteer_id, first_name, last_name, email, phone,
                    availability, preferred_roles, experience, program, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                volunteer_id,
                volunteer_data.get('first_name'),
                volunteer_data.get('last_name'),
                volunteer_data.get('email'),
                volunteer_data.get('phone'),
                volunteer_data.get('availability'),
                volunteer_data.get('preferred_roles'),
                volunteer_data.get('experience'),
                'ReRuns Shoppe',
                'pending'
            ))
            
            availability_days = volunteer_data.get('availability_days', [])
            if availability_days:
                for day in availability_days:
                    cursor.execute('INSERT INTO reruns_availability (volunteer_id, day_of_week) VALUES (?, ?)', (volunteer_id, day))
            
            preferred_roles_list = volunteer_data.get('preferred_roles_list', [])
            if preferred_roles_list:
                for role in preferred_roles_list:
                    cursor.execute('INSERT INTO reruns_roles (volunteer_id, role_name) VALUES (?, ?)', (volunteer_id, role))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'volunteer_id': volunteer_id, 'message': 'Thank you for volunteering with ReRuns Shoppe! We will contact you soon.'}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'A volunteer with this email already exists.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_volunteers(self, status=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if status:
                cursor.execute('SELECT * FROM reruns_volunteers WHERE status = ? ORDER BY created_at DESC', (status,))
            else:
                cursor.execute('SELECT * FROM reruns_volunteers ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            volunteers = [dict(zip(columns, row)) for row in rows]
            conn.close()
            return {'success': True, 'count': len(volunteers), 'volunteers': volunteers}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_volunteer_status(self, volunteer_id, status):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE reruns_volunteers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE volunteer_id = ?', (status, volunteer_id))
            conn.commit()
            conn.close()
            return {'success': True, 'message': f'Volunteer status updated to {status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_volunteer(self, volunteer_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM reruns_volunteers WHERE volunteer_id = ?', (volunteer_id,))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Volunteer deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_volunteer_stats(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM reruns_volunteers')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT status, COUNT(*) FROM reruns_volunteers GROUP BY status')
            status_counts = dict(cursor.fetchall())
            conn.close()
            return {'success': True, 'stats': {'total_volunteers': total, 'by_status': status_counts}}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================================
# SOCIAL LUNCH VOLUNTEER DATABASE SYSTEM
# ============================================================================

class SocialLunchVolunteerDB:
    """Database for Social Lunch volunteer signups and lunch reservations"""
    
    def __init__(self):
        self.db_path = "social_lunch_volunteers.db"
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Social Lunch Volunteers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_lunch_volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                availability TEXT,
                preferred_roles TEXT,
                experience TEXT,
                dietary_restrictions TEXT,
                program TEXT DEFAULT 'Social Lunch',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Social Lunch Availability
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_lunch_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                FOREIGN KEY (volunteer_id) REFERENCES social_lunch_volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        # Social Lunch Roles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_lunch_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id TEXT NOT NULL,
                role_name TEXT NOT NULL,
                FOREIGN KEY (volunteer_id) REFERENCES social_lunch_volunteers(volunteer_id) ON DELETE CASCADE
            )
        ''')
        
        # Lunch Reservations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lunch_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reservation_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                reservation_date DATE NOT NULL,
                number_of_guests INTEGER DEFAULT 1,
                dietary_restrictions TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_social_volunteer_id ON social_lunch_volunteers(volunteer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_social_email ON social_lunch_volunteers(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_social_status ON social_lunch_volunteers(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reservation_date ON lunch_reservations(reservation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reservation_email ON lunch_reservations(email)')
        
        conn.commit()
        conn.close()
        print(" Social Lunch Volunteer Database initialized")
    
    def add_volunteer(self, volunteer_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            volunteer_id = str(uuid.uuid4())[:8]
            
            cursor.execute('''
                INSERT INTO social_lunch_volunteers (
                    volunteer_id, first_name, last_name, email, phone,
                    availability, preferred_roles, experience, dietary_restrictions, program, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                volunteer_id,
                volunteer_data.get('first_name'),
                volunteer_data.get('last_name'),
                volunteer_data.get('email'),
                volunteer_data.get('phone'),
                volunteer_data.get('availability'),
                volunteer_data.get('preferred_roles'),
                volunteer_data.get('experience'),
                volunteer_data.get('dietary_restrictions'),
                'Social Lunch',
                'pending'
            ))
            
            availability_days = volunteer_data.get('availability_days', [])
            if availability_days:
                for day in availability_days:
                    cursor.execute('INSERT INTO social_lunch_availability (volunteer_id, day_of_week) VALUES (?, ?)', (volunteer_id, day))
            
            preferred_roles_list = volunteer_data.get('preferred_roles_list', [])
            if preferred_roles_list:
                for role in preferred_roles_list:
                    cursor.execute('INSERT INTO social_lunch_roles (volunteer_id, role_name) VALUES (?, ?)', (volunteer_id, role))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'volunteer_id': volunteer_id, 'message': 'Thank you for volunteering with Social Lunch! We will contact you soon.'}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'A volunteer with this email already exists.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_reservation(self, reservation_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            reservation_id = str(uuid.uuid4())[:8]
            
            cursor.execute('''
                INSERT INTO lunch_reservations (
                    reservation_id, first_name, last_name, email, phone,
                    reservation_date, number_of_guests, dietary_restrictions, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reservation_id,
                reservation_data.get('first_name'),
                reservation_data.get('last_name'),
                reservation_data.get('email'),
                reservation_data.get('phone'),
                reservation_data.get('reservation_date'),
                reservation_data.get('number_of_guests', 1),
                reservation_data.get('dietary_restrictions'),
                'confirmed'
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'reservation_id': reservation_id, 'message': 'Lunch reservation confirmed! Please arrive by 11:30 AM.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_volunteers(self, status=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if status:
                cursor.execute('SELECT * FROM social_lunch_volunteers WHERE status = ? ORDER BY created_at DESC', (status,))
            else:
                cursor.execute('SELECT * FROM social_lunch_volunteers ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            volunteers = [dict(zip(columns, row)) for row in rows]
            conn.close()
            return {'success': True, 'count': len(volunteers), 'volunteers': volunteers}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_reservations(self, date=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if date:
                cursor.execute('SELECT * FROM lunch_reservations WHERE reservation_date = ? ORDER BY created_at DESC', (date,))
            else:
                cursor.execute('SELECT * FROM lunch_reservations ORDER BY reservation_date DESC, created_at DESC')
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            reservations = [dict(zip(columns, row)) for row in rows]
            conn.close()
            return {'success': True, 'count': len(reservations), 'reservations': reservations}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_volunteer_status(self, volunteer_id, status):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE social_lunch_volunteers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE volunteer_id = ?', (status, volunteer_id))
            conn.commit()
            conn.close()
            return {'success': True, 'message': f'Volunteer status updated to {status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_volunteer(self, volunteer_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM social_lunch_volunteers WHERE volunteer_id = ?', (volunteer_id,))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Volunteer deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_volunteer_stats(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM social_lunch_volunteers')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT status, COUNT(*) FROM social_lunch_volunteers GROUP BY status')
            status_counts = dict(cursor.fetchall())
            cursor.execute('SELECT COUNT(*) FROM lunch_reservations WHERE reservation_date >= date("now")')
            upcoming_reservations = cursor.fetchone()[0]
            conn.close()
            return {'success': True, 'stats': {'total_volunteers': total, 'by_status': status_counts, 'upcoming_reservations': upcoming_reservations}}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Create volunteer database instances
bingo_db = BingoVolunteerDB()
reruns_db = ReRunsVolunteerDB()
social_lunch_db = SocialLunchVolunteerDB()


# ============================================================================
# BINGO API ENDPOINTS
# ============================================================================

@app.route('/api/bingo/volunteer', methods=['POST'])
def add_volunteer():
    try:
        data = request.get_json()
        required_fields = ['first_name', 'last_name', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        result = bingo_db.add_volunteer(data)
        if result['success']:
            return jsonify(result), 201
        return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bingo/volunteers', methods=['GET'])
def get_all_volunteers():
    try:
        status = request.args.get('status')
        result = bingo_db.get_all_volunteers(status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bingo/volunteer/<volunteer_id>/status', methods=['PUT'])
@login_required
def update_volunteer_status(volunteer_id):
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        data = request.get_json()
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        result = bingo_db.update_volunteer_status(volunteer_id, status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bingo/stats', methods=['GET'])
def get_bingo_stats():
    try:
        result = bingo_db.get_volunteer_stats()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bingo/test', methods=['GET'])
def test_bingo_api():
    return jsonify({'success': True, 'message': 'Bingo Volunteer API is running!', 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


# ============================================================================
# RERUNS SHOPPE API ENDPOINTS
# ============================================================================

@app.route('/api/reruns/volunteer', methods=['POST'])
def add_reruns_volunteer():
    try:
        data = request.get_json()
        required_fields = ['first_name', 'last_name', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        availability_days = data.get('availability_days', [])
        data['availability'] = ', '.join(availability_days) if availability_days else ''
        
        preferred_roles_list = data.get('preferred_roles', [])
        data['preferred_roles'] = ', '.join(preferred_roles_list) if preferred_roles_list else ''
        data['preferred_roles_list'] = preferred_roles_list
        
        result = reruns_db.add_volunteer(data)
        if result['success']:
            return jsonify(result), 201
        return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reruns/volunteers', methods=['GET'])
def get_all_reruns_volunteers():
    try:
        status = request.args.get('status')
        result = reruns_db.get_all_volunteers(status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reruns/volunteer/<volunteer_id>/status', methods=['PUT'])
@login_required
def update_reruns_volunteer_status(volunteer_id):
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        data = request.get_json()
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        result = reruns_db.update_volunteer_status(volunteer_id, status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reruns/stats', methods=['GET'])
@login_required
def get_reruns_stats():
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        result = reruns_db.get_volunteer_stats()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reruns/test', methods=['GET'])
def test_reruns_api():
    return jsonify({'success': True, 'message': 'ReRuns Shoppe Volunteer API is running!', 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


# ============================================================================
# SOCIAL LUNCH API ENDPOINTS
# ============================================================================

@app.route('/api/social-lunch/volunteer', methods=['POST'])
def add_social_lunch_volunteer():
    try:
        data = request.get_json()
        required_fields = ['first_name', 'last_name', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        availability_days = data.get('availability_days', [])
        data['availability'] = ', '.join(availability_days) if availability_days else ''
        
        preferred_roles_list = data.get('preferred_roles', [])
        data['preferred_roles'] = ', '.join(preferred_roles_list) if preferred_roles_list else ''
        data['preferred_roles_list'] = preferred_roles_list
        
        result = social_lunch_db.add_volunteer(data)
        if result['success']:
            return jsonify(result), 201
        return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/social-lunch/reserve', methods=['POST'])
def add_lunch_reservation():
    try:
        data = request.get_json()
        required_fields = ['first_name', 'last_name', 'email', 'reservation_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        result = social_lunch_db.add_reservation(data)
        if result['success']:
            return jsonify(result), 201
        return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/social-lunch/volunteers', methods=['GET'])
@login_required
def get_all_social_lunch_volunteers():
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        status = request.args.get('status')
        result = social_lunch_db.get_all_volunteers(status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/social-lunch/reservations', methods=['GET'])
@login_required
def get_lunch_reservations():
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        date = request.args.get('date')
        result = social_lunch_db.get_reservations(date)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/social-lunch/volunteer/<volunteer_id>/status', methods=['PUT'])
@login_required
def update_social_lunch_volunteer_status(volunteer_id):
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        data = request.get_json()
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        result = social_lunch_db.update_volunteer_status(volunteer_id, status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/social-lunch/stats', methods=['GET'])
@login_required
def get_social_lunch_stats():
    try:
        if current_user.role != 'Admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        result = social_lunch_db.get_volunteer_stats()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/social-lunch/test', methods=['GET'])
def test_social_lunch_api():
    return jsonify({'success': True, 'message': 'Social Lunch API is running!', 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


# ============================================================================
# PAGE ROUTES
# ============================================================================

@app.route('/fopsbingo')
def fops_bingo():
    return render_template("fopsbingo.html")

@app.route('/fopsshop')
def fops_shop():
    return render_template("fopsshop.html")

@app.route('/fopslunchmd')
def fops_lunch():
    return render_template("fopslunchmd.html")


# register URIs for api endpoints
app.register_blueprint(python_exec_api)
app.register_blueprint(javascript_exec_api)
app.register_blueprint(user_api)
app.register_blueprint(section_api)
app.register_blueprint(persona_api)
app.register_blueprint(pfp_api)
app.register_blueprint(groq_api)
app.register_blueprint(gemini_api)
app.register_blueprint(microblog_api)
app.register_blueprint(analytics_api)
app.register_blueprint(student_api)
app.register_blueprint(study_api)
app.register_blueprint(classroom_api)
app.register_blueprint(feedback_api)
app.register_blueprint(data_export_import_api)
app.register_blueprint(joke_api)
app.register_blueprint(post_api)
app.register_blueprint(titanic_api)
app.register_blueprint(chatbot_bp)
init_db()

# Jokes file initialization
with app.app_context():
    initJokes()

# Tell Flask-Login the view function name of your login route
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next', '') or request.form.get('next', '')
    if request.method == 'POST':
        user = User.query.filter_by(_uid=request.form['username']).first()
        if user and user.is_password(request.form['password']):
            login_user(user)
            if not is_safe_url(next_page):
                return abort(400)
            return redirect(next_page or url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template("login.html", error=error, next=next_page)

@app.route('/studytracker')
def studytracker():
    return render_template("studytracker.html")
    
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    print("Home:", current_user)
    return render_template("index.html")

@app.route('/users/table2')
@login_required
def u2table():
    users = User.query.all()
    return render_template("u2table.html", user_data=users)

@app.route('/sections/')
@login_required
def sections():
    sections = Section.query.all()
    return render_template("sections.html", sections=sections)

@app.route('/persona/')
@login_required
def persona():
    personas = Persona.query.all()
    return render_template("persona.html", personas=personas)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
 
@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.delete()
        return jsonify({'message': 'User deleted successfully'}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

@app.route('/kasm_users')
def kasm_users():
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return render_template('error.html', message='KASM keys are missing'), 400

    try:
        url = f"{SERVER}/api/public/get_users"
        data = {"api_key": API_KEY, "api_key_secret": API_KEY_SECRET}
        response = requests.post(url, json=data, timeout=10)

        if response.status_code != 200:
            return render_template('error.html', message='Failed to get users', code=response.status_code), response.status_code

        users = response.json().get('users', [])
        for user in users:
            last_session = user.get('last_session')
            try:
                user['last_session'] = datetime.fromisoformat(last_session) if last_session else None
            except ValueError:
                user['last_session'] = None

        sorted_users = sorted(users, key=lambda x: x['last_session'] or datetime.min, reverse=True)
        return render_template('kasm_users.html', users=sorted_users)

    except requests.RequestException as e:
        return render_template('error.html', message=f"Error connecting to KASM API: {str(e)}"), 500
        
@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user_kasm(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return {'message': 'KASM keys are missing'}, 400

    try:
        url = f"{SERVER}/api/public/delete_user"
        data = {"api_key": API_KEY, "api_key_secret": API_KEY_SECRET, "target_user": {"user_id": user_id}, "force": False}
        response = requests.post(url, json=data)

        if response.status_code == 200:
            return {'message': 'User deleted successfully'}, 200
        else:
            return {'message': 'Failed to delete user'}, response.status_code

    except requests.RequestException as e:
        return {'message': 'Error connecting to KASM API', 'error': str(e)}, 500

@app.route('/update_user/<string:uid>', methods=['PUT'])
def update_user(uid):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    user = User.query.filter_by(_uid=uid).first()
    if user:
        user.update(data)
        return jsonify({"message": "User updated successfully."}), 200
    else:
        return jsonify({"message": "User not found."}), 404

# Create an AppGroup for custom commands
custom_cli = AppGroup('custom', help='Custom commands')

@custom_cli.command('generate_data')
def generate_data():
    initUsers()
    initMicroblogs()
    initPersonas()
    initPersonaUsers()
    initTitanic()

app.cli.add_command(custom_cli)
        
if __name__ == "__main__":
    host = "0.0.0.0"
    port = app.config['FLASK_PORT']
    print("=" * 70)
    print(" FLASK APPLICATION STARTING")
    print("=" * 70)
    print(f" Main Server: http://localhost:{port}")
    print(f" Bingo Volunteer Page: http://localhost:{port}/fopsbingo")
    print(f" ReRuns Shoppe Page: http://localhost:{port}/fopsshop")
    print(f" Social Lunch Page: http://localhost:{port}/fopslunchmd")
    
    print("\n BINGO VOLUNTEER API ENDPOINTS:")
    print(f"  POST   http://localhost:{port}/api/bingo/volunteer")
    print(f"  GET    http://localhost:{port}/api/bingo/volunteers")
    print(f"  GET    http://localhost:{port}/api/bingo/test")
    
    print("\n RERUNS SHOPPE API ENDPOINTS:")
    print(f"  POST   http://localhost:{port}/api/reruns/volunteer")
    print(f"  GET    http://localhost:{port}/api/reruns/volunteers")
    print(f"  GET    http://localhost:{port}/api/reruns/test")
    
    print("\n SOCIAL LUNCH API ENDPOINTS:")
    print(f"  POST   http://localhost:{port}/api/social-lunch/volunteer")
    print(f"  POST   http://localhost:{port}/api/social-lunch/reserve")
    print(f"  GET    http://localhost:{port}/api/social-lunch/volunteers (admin)")
    print(f"  GET    http://localhost:{port}/api/social-lunch/reservations (admin)")
    print(f"  GET    http://localhost:{port}/api/social-lunch/stats (admin)")
    print(f"  GET    http://localhost:{port}/api/social-lunch/test")
    
    print("\n Databases: bingo_volunteers.db, reruns_volunteers.db, social_lunch_volunteers.db")
    print("=" * 70)
    
    app.run(debug=True, host=host, port=port, use_reloader=False)