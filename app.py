"""
Travel Collector App
A simple app to collect and organize travel places by city and category.
View by category or by district for route planning.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['DATABASE'] = 'travel.db'
app.config['GOOGLE_MAPS_SEARCH_URL'] = 'https://www.google.com/maps/search/?api=1&query='

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            district TEXT DEFAULT '',
            address TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            google_maps_query TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def create_google_maps_link(name, address=''):
    """Create a Google Maps search link for a place"""
    query = name
    if address:
        query = f"{name} {address}"
    return f"https://www.google.com/maps/search/?api=1&query=" + query.replace(' ', '+')

# Initialize database on startup
init_db()

@app.route('/')
def index():
    """Main page - show all places or filter by city"""
    city = request.args.get('city', '')
    view_mode = request.args.get('view', 'category')  # 'category' or 'district'
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all cities for the filter dropdown
    cursor.execute('SELECT DISTINCT city FROM places ORDER BY city')
    cities = [row['city'] for row in cursor.fetchall()]
    
    # Get places
    if city:
        cursor.execute('SELECT * FROM places WHERE city = ? ORDER BY category, district, name', (city,))
    else:
        cursor.execute('SELECT * FROM places ORDER BY city, category, district, name')
    
    places = cursor.fetchall()
    conn.close()
    
    # Group places
    if view_mode == 'district':
        grouped = {}
        for place in places:
            key = f"{place['city']} > {place['district']}" if place['district'] else f"{place['city']} > Unknown District"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(place)
    else:
        grouped = {}
        for place in places:
            key = f"{place['city']} > {place['category']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(place)
    
    return render_template(
        'index.html',
        places=places,
        grouped=grouped,
        cities=cities,
        selected_city=city,
        view_mode=view_mode
    )

@app.route('/add', methods=['GET', 'POST'])
def add_place():
    """Add a new place"""
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        district = request.form.get('district', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not city or not name or not category:
            return jsonify({'error': 'City, name, and category are required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO places (city, name, category, district, address, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (city, name, category, district, address, notes))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index', city=city))
    
    # GET request - show the form
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT city FROM places ORDER BY city')
    cities = [row['city'] for row in cursor.fetchall()]
    conn.close()
    
    return render_template('add.html', cities=cities)

@app.route('/api/places', methods=['GET'])
def api_get_places():
    """API endpoint to get places"""
    city = request.args.get('city', '')
    category = request.args.get('category', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM places WHERE 1=1'
    params = []
    
    if city:
        query += ' AND city = ?'
        params.append(city)
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY city, category, district, name'
    cursor.execute(query, params)
    
    places = []
    for row in cursor.fetchall():
        p = dict(row)
        p['maps_url'] = create_google_maps_link(p['name'], p.get('address', ''))
        places.append(p)
    
    conn.close()
    return jsonify(places)

@app.route('/api/add', methods=['POST'])
def api_add_place():
    """API endpoint to add a place"""
    data = request.get_json()
    
    city = data.get('city', '').strip()
    name = data.get('name', '').strip()
    category = data.get('category', '').strip()
    district = data.get('district', '').strip()
    address = data.get('address', '').strip()
    notes = data.get('notes', '').strip()
    
    if not city or not name or not category:
        return jsonify({'error': 'City, name, and category are required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO places (city, name, category, district, address, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (city, name, category, district, address, notes))
    conn.commit()
    place_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': place_id})

@app.route('/delete/<int:place_id>', methods=['POST'])
def delete_place(place_id):
    """Delete a place"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM places WHERE id = ?', (place_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
