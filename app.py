"""
Travel Collector App
A simple app to collect and organize travel places by city and category.
View by category or by district for route planning.
"""

import sqlite3
import os
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'data', 'travel.db')

# Ensure data directory exists
os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
app.config['GOOGLE_MAPS_SEARCH_URL'] = 'https://www.google.com/maps/search/?api=1&query='

# Force UTF-8 encoding for the whole app
app.config['JSON_AS_ASCII'] = False

def get_db():
    """Get database connection with UTF-8 support"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.execute('PRAGMA encoding = "UTF-8"')
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
            latitude REAL DEFAULT NULL,
            longitude REAL DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add lat/lng columns if they don't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE places ADD COLUMN latitude REAL DEFAULT NULL')
        cursor.execute('ALTER TABLE places ADD COLUMN longitude REAL DEFAULT NULL')
    except:
        pass
    
    conn.commit()
    conn.close()

def create_google_maps_link(name, address=''):
    """Create a Google Maps search link for a place"""
    query = name
    if address:
        query = f"{name} {address}"
    return f"https://www.google.com/maps/search/?api=1&query=" + query.replace(' ', '+')

def geocode_address(name, address='', city=''):
    """Geocode an address and return (lat, lng) or (None, None)"""
    import time
    import urllib.request
    import json
    
    query = f"{name} {address} {city}".strip()
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}&limit=1"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TravelCollectorApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Geocoding failed for {query}: {e}")
    return None, None

import urllib.parse

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
        if city.startswith('_all:'):
            # Filter by prefecture name contained in city string
            prefecture_filter = city[5:]  # Remove '_all:' prefix
            cursor.execute(
                'SELECT * FROM places WHERE city LIKE ? ORDER BY city, category, district, name',
                (f'%{prefecture_filter}%',)
            )
        else:
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
    
    # Get selected city for filter display
    selected_city = city
    
    return render_template(
        'index.html',
        places=places,
        grouped=grouped,
        cities=cities,
        selected_city=selected_city,
        view_mode=view_mode
    )

@app.route('/map')
def map_view():
    """Map view - show all places with Google Maps links"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM places ORDER BY city, category, name')
    places = cursor.fetchall()
    
    # Get unique cities
    cursor.execute('SELECT DISTINCT city FROM places ORDER BY city')
    cities = [row['city'] for row in cursor.fetchall()]
    conn.close()
    
    # Convert to list of dicts for JSON
    places_list = []
    for place in places:
        p = dict(place)
        p['maps_url'] = create_google_maps_link(p['name'], p.get('address', ''))
        places_list.append(p)
    
    import json
    return render_template('map.html', places=places_list, cities=cities, places_json=json.dumps(places_list))

@app.route('/add', methods=['GET', 'POST'])
def add_place():
    """Add a new place"""
    if request.method == 'POST':
        country = request.form.get('country', '').strip()
        prefecture = request.form.get('prefecture', '').strip()
        city = request.form.get('city', '').strip()
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        district = request.form.get('district', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not city or not name or not category:
            return jsonify({'error': 'City, name, and category are required'}), 400
        
        # Build display city name: "City (Prefecture, Country)" or just "City"
        if country and prefecture and prefecture not in city:
            display_city = f"{city} ({prefecture}, {country})"
        elif country:
            display_city = f"{city} ({country})"
        else:
            display_city = city
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO places (city, name, category, district, address, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (display_city, name, category, district, address, notes))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index', city=display_city))
    
    # GET request - show the form (no cities needed, they're hardcoded in JS)
    return render_template('add.html')

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
    
    # Geocode the address
    lat, lng = geocode_address(name, address, city)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO places (city, name, category, district, address, notes, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (city, name, category, district, address, notes, lat, lng))
    conn.commit()
    place_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': place_id, 'latitude': lat, 'longitude': lng})

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
    # Use port 5000 for container, map to 5003 externally via docker-compose
    app.run(host='0.0.0.0', port=5000, debug=False)
