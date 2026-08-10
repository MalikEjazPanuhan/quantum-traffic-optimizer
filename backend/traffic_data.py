import numpy as np
import random
from datetime import datetime
import requests

# ============================================
# GOOGLE MAPS API KEY
# ============================================

GOOGLE_MAPS_API_KEY = "AIzaSyDwr5H6ix3zRMJSlIiSEIaMAJfPFZXDtmw"

# ============================================
# REAL DATA INTEGRATION - Google Distance Matrix
# ============================================

def get_real_travel_time(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Get REAL travel time from Google Distance Matrix API
    Returns: travel_time in minutes, distance in km, congestion level
    """
    try:
        origin = f"{origin_lat},{origin_lng}"
        destination = f"{dest_lat},{dest_lng}"
        
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': origin,
            'destinations': destination,
            'key': GOOGLE_MAPS_API_KEY,
            'departure_time': 'now',
            'traffic_model': 'best_guess'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            element = data['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                duration_in_traffic = element.get('duration_in_traffic', {}).get('value', 0)
                duration = element.get('duration', {}).get('value', 0)
                distance = element.get('distance', {}).get('value', 0)
                
                travel_time_seconds = duration_in_traffic if duration_in_traffic > 0 else duration
                travel_time_minutes = travel_time_seconds / 60
                distance_km = distance / 1000
                
                congestion = 0.5
                if duration > 0 and duration_in_traffic > 0:
                    ratio = duration_in_traffic / duration
                    if ratio <= 1.0:
                        congestion = 0.2
                    elif ratio <= 1.3:
                        congestion = 0.4
                    elif ratio <= 1.6:
                        congestion = 0.6
                    elif ratio <= 2.0:
                        congestion = 0.8
                    else:
                        congestion = 0.95
                
                return {
                    'travel_time_minutes': round(travel_time_minutes, 1),
                    'distance_km': round(distance_km, 1),
                    'congestion': round(congestion, 3)
                }
        return None
    except Exception as e:
        print(f"⚠️ API Error: {e}")
        return None

# ============================================
# METHOD 1: GOOGLE PLACES API
# ============================================

def get_real_road_names_from_google(lat, lng):
    """Get REAL road names from Google Places API"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius': 5000,
            'types': 'route|intersection',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        status = data.get('status')
        print(f"📊 Google Places API Status: {status}")
        
        if status != 'OK':
            print(f"⚠️ API Error: {status}")
            return None
        
        roads = []
        seen_names = set()
        for place in data.get('results', [])[:12]:
            name = place.get('name', '')
            if name and len(name) > 2 and name not in seen_names:
                if not name.startswith('Unnamed'):
                    roads.append({
                        'name': name,
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng']
                    })
                    seen_names.add(name)
        
        print(f"✅ Found {len(roads)} roads from Google Places")
        return roads if len(roads) >= 4 else None
    except Exception as e:
        print(f"⚠️ Google Places API error: {e}")
        return None

# ============================================
# METHOD 2: OPENSTREETMAP (FREE)
# ============================================

def get_osm_nearby_roads(lat, lng):
    """Get nearby roads from OpenStreetMap (FREE)"""
    try:
        url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          way["highway"]["name"](around:5000,{lat},{lng});
        );
        out body;
        """
        response = requests.get(url, params={'data': query})
        data = response.json()
        
        roads = []
        seen_names = set()
        for element in data.get('elements', [])[:10]:
            name = element.get('tags', {}).get('name')
            if name and len(name) > 2 and name not in seen_names:
                roads.append({
                    'name': name,
                    'lat': lat,
                    'lng': lng
                })
                seen_names.add(name)
        
        print(f"✅ Found {len(roads)} roads from OpenStreetMap")
        return roads if len(roads) >= 4 else None
    except Exception as e:
        print(f"⚠️ Overpass API error: {e}")
        return None

# ============================================
# METHOD 3: HARDCODED CITY DICTIONARY
# ============================================

def get_hardcoded_roads(city):
    """Get roads from hardcoded dictionary"""
    city_roads = {
        'Lahore': [
            {'name': 'Liberty Chowk', 'lat': 31.5125, 'lng': 74.3382},
            {'name': 'Kalma Chowk', 'lat': 31.5204, 'lng': 74.3473},
            {'name': 'Gulberg Signal', 'lat': 31.5234, 'lng': 74.3331},
            {'name': 'Mall Road', 'lat': 31.5604, 'lng': 74.3329},
            {'name': 'Qurtaba Chowk', 'lat': 31.5484, 'lng': 74.3526},
            {'name': 'Ferozepur Road', 'lat': 31.4954, 'lng': 74.3744},
        ],
        'Karachi': [
            {'name': 'Tariq Road', 'lat': 24.8746, 'lng': 67.0614},
            {'name': 'Shahrah-e-Faisal', 'lat': 24.8568, 'lng': 67.0553},
            {'name': 'Clifton Bridge', 'lat': 24.8108, 'lng': 67.0357},
            {'name': 'Korangi Road', 'lat': 24.8117, 'lng': 67.1478},
            {'name': 'University Road', 'lat': 24.9324, 'lng': 67.0824},
            {'name': 'MA Jinnah Road', 'lat': 24.8607, 'lng': 67.0011},
        ],
        'Islamabad': [
            {'name': 'Faisal Avenue', 'lat': 33.6880, 'lng': 73.0730},
            {'name': 'Blue Area', 'lat': 33.6997, 'lng': 73.0479},
            {'name': 'Constitution Avenue', 'lat': 33.7050, 'lng': 73.0880},
            {'name': 'Margalla Road', 'lat': 33.6743, 'lng': 73.0878},
            {'name': 'Park Road', 'lat': 33.6512, 'lng': 73.0885},
            {'name': 'Srinagar Highway', 'lat': 33.6714, 'lng': 73.0679},
        ],
        'Rawalpindi': [
            {'name': 'Murree Road', 'lat': 33.5651, 'lng': 73.0169},
            {'name': 'Mall Road', 'lat': 33.6042, 'lng': 73.0875},
            {'name': 'Airport Road', 'lat': 33.6164, 'lng': 73.0994},
            {'name': 'GT Road', 'lat': 33.5851, 'lng': 73.0575},
            {'name': 'Saddar Road', 'lat': 33.5900, 'lng': 73.0470},
        ],
        'Dubai': [
            {'name': 'Sheikh Zayed Road', 'lat': 25.2048, 'lng': 55.2708},
            {'name': 'Al Khail Road', 'lat': 25.2108, 'lng': 55.2908},
            {'name': 'Emirates Road', 'lat': 25.2208, 'lng': 55.3108},
            {'name': 'Hessa Street', 'lat': 25.1908, 'lng': 55.2508},
        ],
        'London': [
            {'name': 'Oxford Street', 'lat': 51.5155, 'lng': -0.1420},
            {'name': 'Regent Street', 'lat': 51.5105, 'lng': -0.1380},
            {'name': 'Piccadilly', 'lat': 51.5090, 'lng': -0.1340},
            {'name': 'Bond Street', 'lat': 51.5135, 'lng': -0.1480},
        ],
        'NewYork': [
            {'name': '5th Avenue', 'lat': 40.7746, 'lng': -73.9653},
            {'name': 'Broadway', 'lat': 40.7590, 'lng': -73.9845},
            {'name': 'Wall Street', 'lat': 40.7069, 'lng': -74.0090},
            {'name': 'Park Avenue', 'lat': 40.7711, 'lng': -73.9675},
            {'name': 'Madison Avenue', 'lat': 40.7592, 'lng': -73.9686},
            {'name': 'Lexington Avenue', 'lat': 40.7551, 'lng': -73.9708},
        ],
        'Jeddah': [
            {'name': 'King Abdulaziz Road', 'lat': 21.5433, 'lng': 39.1728},
            {'name': 'Madinah Road', 'lat': 21.5532, 'lng': 39.1780},
            {'name': 'Prince Sultan Road', 'lat': 21.5132, 'lng': 39.1680},
            {'name': 'Al-Madinah Al-Munawwarah Road', 'lat': 21.5732, 'lng': 39.1580},
            {'name': 'King Fahd Road', 'lat': 21.5332, 'lng': 39.1880},
            {'name': 'Corniche Road', 'lat': 21.5232, 'lng': 39.1480},
        ],
        'Riyadh': [
            {'name': 'King Fahd Road', 'lat': 24.7136, 'lng': 46.6753},
            {'name': 'Olaya Street', 'lat': 24.7236, 'lng': 46.6853},
            {'name': 'Tahlia Street', 'lat': 24.7336, 'lng': 46.6653},
            {'name': 'King Abdulaziz Road', 'lat': 24.7036, 'lng': 46.6953},
        ],
        'Makkah': [
            {'name': 'King Fahd Road', 'lat': 21.4225, 'lng': 39.8262},
            {'name': 'Al-Masjid Al-Haram', 'lat': 21.4325, 'lng': 39.8362},
            {'name': 'Ibrahim Al-Khalil Road', 'lat': 21.4125, 'lng': 39.8162},
            {'name': 'Al-Madinah Road', 'lat': 21.4425, 'lng': 39.8062},
        ],
        'Medina': [
            {'name': 'King Fahd Road', 'lat': 24.4672, 'lng': 39.6112},
            {'name': 'Al-Madinah Road', 'lat': 24.4772, 'lng': 39.6212},
            {'name': 'Prince Abdulmajeed Road', 'lat': 24.4572, 'lng': 39.6012},
            {'name': 'King Abdulaziz Road', 'lat': 24.4872, 'lng': 39.5912},
        ],
    }
    
    # Try to find the city (case-insensitive)
    for key in city_roads:
        if key.lower() in city.lower() or city.lower() in key.lower():
            print(f"✅ Found {len(city_roads[key])} roads in hardcoded dictionary for {key}")
            return city_roads[key]
    
    return None

# ============================================
# METHOD 4: SMART POINTS (LAST RESORT)
# ============================================

def generate_smart_points(city, lat, lng):
    """Generate smart point names based on location"""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'zoom': 10
        }
        headers = {'User-Agent': 'QuantumTrafficOptimizer/1.0'}
        
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        area_name = city if city else 'Area'
        if 'address' in data:
            area_name = data['address'].get('city') or \
                       data['address'].get('town') or \
                       data['address'].get('village') or \
                       data['address'].get('suburb') or \
                       area_name
        
        points = [
            {'name': f'{area_name} North', 'lat': lat + 0.015, 'lng': lng + 0.015},
            {'name': f'{area_name} South', 'lat': lat - 0.015, 'lng': lng - 0.015},
            {'name': f'{area_name} East', 'lat': lat + 0.02, 'lng': lng - 0.015},
            {'name': f'{area_name} West', 'lat': lat - 0.01, 'lng': lng - 0.02},
            {'name': f'{area_name} Center', 'lat': lat, 'lng': lng},
            {'name': f'{area_name} Main', 'lat': lat + 0.01, 'lng': lng + 0.01},
        ]
        print(f"✅ Generated {len(points)} smart points for {area_name}")
        return points
    except:
        points = [
            {'name': f'{city} North', 'lat': lat + 0.015, 'lng': lng + 0.015},
            {'name': f'{city} South', 'lat': lat - 0.015, 'lng': lng - 0.015},
            {'name': f'{city} East', 'lat': lat + 0.02, 'lng': lng - 0.015},
            {'name': f'{city} West', 'lat': lat - 0.01, 'lng': lng - 0.02},
            {'name': f'{city} Center', 'lat': lat, 'lng': lng},
            {'name': f'{city} Main', 'lat': lat + 0.01, 'lng': lng + 0.01},
        ]
        print(f"✅ Generated {len(points)} default points for {city}")
        return points

# ============================================
# MAIN FUNCTION: GET REAL ROAD DATA
# ============================================

def get_real_road_data(city, lat, lng):
    """
    Get REAL road data - ALWAYS returns street names
    Uses multiple fallback methods
    """
    
    print(f"\n{'='*60}")
    print(f"🌍 FETCHING ROADS FOR: {city.upper()}")
    print(f"{'='*60}")
    
    intersections = None
    
    # ============================================
    # METHOD 1: Try Google Places API
    # ============================================
    print("\n📌 METHOD 1: Google Places API")
    intersections = get_real_road_names_from_google(lat, lng)
    
    # ============================================
    # METHOD 2: Try OpenStreetMap (FREE)
    # ============================================
    if not intersections or len(intersections) < 4:
        print("\n📌 METHOD 2: OpenStreetMap")
        intersections = get_osm_nearby_roads(lat, lng)
    
    # ============================================
    # METHOD 3: Use Hardcoded Dictionary
    # ============================================
    if not intersections or len(intersections) < 4:
        print("\n📌 METHOD 3: Hardcoded Dictionary")
        intersections = get_hardcoded_roads(city)
    
    # ============================================
    # METHOD 4: Generate Smart Points (Last Resort)
    # ============================================
    if not intersections or len(intersections) < 4:
        print("\n📌 METHOD 4: Smart Points")
        intersections = generate_smart_points(city, lat, lng)
    
    print(f"\n✅ FINAL: Using {len(intersections)} intersections")
    print(f"   Roads: {', '.join([r['name'] for r in intersections[:4]])}...")
    
    # ============================================
    # Get traffic data for each road pair
    # ============================================
    print("\n📊 Getting traffic data...")
    traffic_data = []
    successful_pairs = 0
    
    for i in range(len(intersections)):
        for j in range(i+1, len(intersections)):
            origin = intersections[i]
            dest = intersections[j]
            
            real_data = get_real_travel_time(
                origin['lat'], origin['lng'],
                dest['lat'], dest['lng']
            )
            
            if real_data:
                road_name = f"{origin['name']} → {dest['name']}"
                congestion = real_data['congestion']
                
                if congestion < 0.3:
                    status = 'low'
                    color = '#4CAF50'
                elif congestion < 0.6:
                    status = 'medium'
                    color = '#FFC107'
                else:
                    status = 'high'
                    color = '#F44336'
                
                speed = 60 - (congestion * 40)
                
                traffic_data.append({
                    'road': road_name,
                    'congestion': congestion,
                    'status': status,
                    'color': color,
                    'speed': round(speed, 1),
                    'travel_time': real_data['travel_time_minutes'],
                    'distance_km': real_data['distance_km'],
                    'timestamp': datetime.now().isoformat(),
                    'is_real': True
                })
                successful_pairs += 1
    
    print(f"✅ Got traffic data for {successful_pairs} road pairs")
    return traffic_data

# ============================================
# REAL-TIME TRAFFIC DATA INTEGRATION
# ============================================

class RealTimeTrafficFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300
        self.google_api_key = GOOGLE_MAPS_API_KEY
        self.use_real_data = True
        
    def get_traffic_data(self, city, lat=None, lng=None, roads=None):
        cache_key = f"{city}_{datetime.now().strftime('%Y%m%d%H%M')}"
        if cache_key in self.cache:
            print(f"📦 Using cached data for {city}")
            return self.cache[cache_key]
        
        if self.use_real_data and lat and lng:
            try:
                real_data = get_real_road_data(city, lat, lng)
                if real_data and len(real_data) > 0:
                    print(f"✅ SUCCESS: Got {len(real_data)} real traffic data points")
                    self.cache[cache_key] = real_data
                    return real_data
            except Exception as e:
                print(f"❌ Error fetching real data: {e}")
        
        print("⚠️ Falling back to simulated data")
        data = self._generate_mock_traffic(city, roads)
        self.cache[cache_key] = data
        return data
    
    def _generate_mock_traffic(self, city, roads):
        """Fallback: Generate realistic mock traffic data"""
        city_roads = {
            'Karachi': ['MA Jinnah Road', 'Shahrah-e-Faisal', 'University Road', 
                       'Rashid Minhas Road', 'Korangi Road', 'Clifton Road', 'Tariq Road'],
            'Lahore': ['The Mall', 'Ferozepur Road', 'Gulberg Boulevard', 
                      'Johar Town Road', 'Canal Road', 'MM Alam Road', 'Liberty Market Road'],
            'Islamabad': ['Islamabad Highway', 'Margalla Road', 'Kashmir Highway',
                         'Srinagar Highway', 'Park Road', 'Faisal Avenue', 'Constitution Avenue'],
            'Rawalpindi': ['Murree Road', 'Mall Road', 'Airport Road', 
                          'GT Road', 'Saddar Road', 'Iqbal Road', 'Bank Road'],
            'Dubai': ['Sheikh Zayed Road', 'Al Khail Road', 'Emirates Road', 
                     'Hessa Street', 'Dubai-Al Ain Road', 'Jumeirah Road'],
            'London': ['Oxford Street', 'Regent Street', 'Piccadilly', 
                      'Bond Street', 'Park Lane', 'Kensington High Street'],
            'NewYork': ['5th Avenue', 'Broadway', 'Wall Street', 'Park Avenue', 
                       'Madison Avenue', 'Lexington Avenue'],
            'Jeddah': ['King Abdulaziz Road', 'Madinah Road', 'Prince Sultan Road', 
                      'Al-Madinah Al-Munawwarah Road', 'King Fahd Road', 'Corniche Road'],
        }
        
        road_names = city_roads.get(city, [f"Road {i}" for i in range(1, 8)])
        if roads:
            road_names = roads
            
        traffic_data = []
        current_time = datetime.now()
        hour = current_time.hour
        is_peak_hour = (7 <= hour <= 10) or (16 <= hour <= 19)
        is_night = (22 <= hour <= 6)
        is_weekend = current_time.weekday() >= 5
        
        for i, road in enumerate(road_names):
            base_congestion = random.uniform(0.2, 0.6)
            
            if is_peak_hour:
                base_congestion += random.uniform(0.3, 0.5)
            elif is_night:
                base_congestion -= random.uniform(0.3, 0.5)
                
            if is_weekend:
                if is_peak_hour:
                    base_congestion += random.uniform(0.1, 0.2)
                else:
                    base_congestion -= random.uniform(0.1, 0.2)
            
            if random.random() < 0.05:
                base_congestion += random.uniform(0.3, 0.6)
                event = random.choice(['accident', 'construction', 'event', 'road closure'])
            else:
                event = None
                
            base_congestion += (i * 0.03) % 0.2
            congestion = min(1.0, max(0.0, base_congestion))
            
            if congestion < 0.3:
                status = 'low'
                color = '#4CAF50'
            elif congestion < 0.6:
                status = 'medium'
                color = '#FFC107'
            else:
                status = 'high'
                color = '#F44336'
                
            base_speed = random.uniform(50, 70)
            speed = base_speed * (1 - congestion * 0.7)
            travel_time = 60 / max(speed, 5)
            
            traffic_data.append({
                'road': road,
                'congestion': round(congestion, 3),
                'status': status,
                'color': color,
                'speed': round(speed, 1),
                'travel_time': round(travel_time, 1),
                'event': event,
                'timestamp': current_time.isoformat(),
                'is_real': False
            })
            
        return traffic_data
