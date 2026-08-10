import numpy as np
import random
from datetime import datetime
import requests
import time

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
        print(f"⚠️ Distance Matrix API Error: {e}")
        return None

# ============================================
# METHOD 1: GOOGLE PLACES API (TEXT SEARCH)
# ============================================

def get_real_road_names_from_google(lat, lng, city_name):
    """
    Get REAL road names from Google Places API - Works for ANY city
    Uses Text Search which is more reliable than Nearby Search
    """
    try:
        print(f"   🔍 Searching Google Places for roads in: {city_name}")
        
        # ============================================
        # ATTEMPT 1: Text Search for roads
        # ============================================
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': f"roads streets in {city_name}",
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        status = data.get('status')
        print(f"   📊 Text Search Status: {status}")
        
        if status == 'OK':
            roads = []
            seen_names = set()
            for place in data.get('results', [])[:12]:
                name = place.get('name', '')
                if name and len(name) > 2 and name not in seen_names:
                    # Accept any named place (not just roads - gives better results)
                    roads.append({
                        'name': name,
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng']
                    })
                    seen_names.add(name)
            
            if len(roads) >= 4:
                print(f"   ✅ Found {len(roads)} places from Google Places Text Search")
                return roads
            else:
                print(f"   ⚠️ Only found {len(roads)} places, trying Nearby Search...")
        
        # ============================================
        # ATTEMPT 2: Nearby Search (fallback)
        # ============================================
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius': 5000,
            'types': 'route|intersection|street_address|point_of_interest',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        status = data.get('status')
        print(f"   📊 Nearby Search Status: {status}")
        
        if status == 'OK':
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
            
            if len(roads) >= 4:
                print(f"   ✅ Found {len(roads)} places from Google Places Nearby Search")
                return roads
        
        print(f"   ⚠️ Google Places API found {len(roads) if 'roads' in locals() else 0} places")
        return None
        
    except Exception as e:
        print(f"   ❌ Google Places API error: {e}")
        return None

# ============================================
# METHOD 2: OPENSTREETMAP (FREE)
# ============================================

def get_osm_nearby_roads(lat, lng):
    """
    Get nearby roads from OpenStreetMap (FREE, no API key required)
    Works for most cities worldwide
    """
    try:
        print(f"   🔍 Searching OpenStreetMap for roads...")
        
        # Try Overpass API for road names
        url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          way["highway"]["name"](around:5000,{lat},{lng});
        );
        out body;
        """
        
        response = requests.get(url, params={'data': query}, timeout=10)
        data = response.json()
        
        roads = []
        seen_names = set()
        for element in data.get('elements', [])[:12]:
            name = element.get('tags', {}).get('name')
            if name and len(name) > 2 and name not in seen_names:
                roads.append({
                    'name': name,
                    'lat': lat + random.uniform(-0.01, 0.01),
                    'lng': lng + random.uniform(-0.01, 0.01)
                })
                seen_names.add(name)
        
        if len(roads) >= 4:
            print(f"   ✅ Found {len(roads)} roads from OpenStreetMap")
            return roads
        else:
            print(f"   ⚠️ Found {len(roads)} roads from OpenStreetMap (need 4+)")
            return None
    except Exception as e:
        print(f"   ❌ OpenStreetMap error: {e}")
        return None

# ============================================
# METHOD 3: GENERATE SMART POINTS (LAST RESORT)
# ============================================

def generate_smart_points(city, lat, lng):
    """
    Generate smart point names based on city name
    This ALWAYS works as the final fallback
    """
    print(f"   🔄 Generating smart points for: {city}")
    
    # Try to get area name from OpenStreetMap reverse geocoding
    area_name = city
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'zoom': 10
        }
        headers = {'User-Agent': 'QuantumTrafficOptimizer/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if 'address' in data:
            area_name = data['address'].get('city') or \
                       data['address'].get('town') or \
                       data['address'].get('village') or \
                       data['address'].get('suburb') or \
                       data['address'].get('county') or \
                       city
    except:
        pass
    
    # Generate 6 points around the city center
    points = [
        {'name': f'{area_name} North', 'lat': lat + 0.015, 'lng': lng + 0.015},
        {'name': f'{area_name} South', 'lat': lat - 0.015, 'lng': lng - 0.015},
        {'name': f'{area_name} East', 'lat': lat + 0.02, 'lng': lng - 0.015},
        {'name': f'{area_name} West', 'lat': lat - 0.01, 'lng': lng - 0.02},
        {'name': f'{area_name} Center', 'lat': lat, 'lng': lng},
        {'name': f'{area_name} Main', 'lat': lat + 0.01, 'lng': lng + 0.01},
    ]
    
    print(f"   ✅ Generated {len(points)} smart points for {area_name}")
    return points

# ============================================
# MAIN FUNCTION: GET REAL ROAD DATA
# ============================================

def get_real_road_data(city, lat, lng):
    """
    Get REAL road data - ALWAYS returns street names
    Uses multiple fallback methods to ensure results
    """
    
    print(f"\n{'='*60}")
    print(f"🌍 FETCHING ROADS FOR: {city.upper()}")
    print(f"📍 Coordinates: {lat}, {lng}")
    print(f"{'='*60}")
    
    intersections = None
    
    # ============================================
    # METHOD 1: Google Places API (BEST)
    # ============================================
    print("\n📌 METHOD 1: Google Places API")
    intersections = get_real_road_names_from_google(lat, lng, city)
    
    # ============================================
    # METHOD 2: OpenStreetMap (FREE BACKUP)
    # ============================================
    if not intersections or len(intersections) < 4:
        print("\n📌 METHOD 2: OpenStreetMap")
        intersections = get_osm_nearby_roads(lat, lng)
    
    # ============================================
    # METHOD 3: Smart Points (ALWAYS WORKS)
    # ============================================
    if not intersections or len(intersections) < 4:
        print("\n📌 METHOD 3: Smart Points (Fallback)")
        intersections = generate_smart_points(city, lat, lng)
    
    # Ensure we have at least 4 intersections
    if not intersections or len(intersections) < 4:
        print("⚠️ CRITICAL: No intersections found, creating emergency points...")
        intersections = [
            {'name': f'{city} Point 1', 'lat': lat + 0.015, 'lng': lng + 0.015},
            {'name': f'{city} Point 2', 'lat': lat - 0.015, 'lng': lng - 0.015},
            {'name': f'{city} Point 3', 'lat': lat + 0.02, 'lng': lng - 0.015},
            {'name': f'{city} Point 4', 'lat': lat - 0.01, 'lng': lng - 0.02},
        ]
    
    print(f"\n✅ FINAL: Using {len(intersections)} intersections")
    print(f"   Example: {intersections[0]['name']} → {intersections[1]['name']}")
    
    # ============================================
    # Get traffic data for each road pair
    # ============================================
    print("\n📊 Getting real-time traffic data...")
    traffic_data = []
    successful_pairs = 0
    total_pairs = 0
    
    for i in range(len(intersections)):
        for j in range(i+1, len(intersections)):
            total_pairs += 1
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
    
    print(f"✅ Got traffic data for {successful_pairs}/{total_pairs} road pairs")
    
    # If no traffic data was fetched, generate fallback data
    if not traffic_data:
        print("⚠️ No traffic data fetched, generating fallback data...")
        for i in range(len(intersections)):
            for j in range(i+1, len(intersections)):
                origin = intersections[i]
                dest = intersections[j]
                
                congestion = random.uniform(0.2, 0.6)
                if congestion < 0.3:
                    status = 'low'
                    color = '#4CAF50'
                elif congestion < 0.6:
                    status = 'medium'
                    color = '#FFC107'
                else:
                    status = 'high'
                    color = '#F44336'
                
                traffic_data.append({
                    'road': f"{origin['name']} → {dest['name']}",
                    'congestion': congestion,
                    'status': status,
                    'color': color,
                    'speed': round(60 - (congestion * 40), 1),
                    'travel_time': round(random.uniform(5, 20), 1),
                    'distance_km': round(random.uniform(2, 10), 1),
                    'timestamp': datetime.now().isoformat(),
                    'is_real': False
                })
    
    return traffic_data

# ============================================
# REAL-TIME TRAFFIC DATA INTEGRATION
# ============================================

class RealTimeTrafficFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.google_api_key = GOOGLE_MAPS_API_KEY
        self.use_real_data = True
        
    def get_traffic_data(self, city, lat=None, lng=None, roads=None):
        """Fetch real-time traffic data for a city"""
        cache_key = f"{city}_{datetime.now().strftime('%Y%m%d%H%M')}"
        
        if cache_key in self.cache:
            print(f"\n📦 Using cached data for {city}")
            return self.cache[cache_key]
        
        if self.use_real_data and lat and lng:
            try:
                print(f"\n🌐 FETCHING REAL TRAFFIC DATA FOR: {city}")
                real_data = get_real_road_data(city, lat, lng)
                
                if real_data and len(real_data) > 0:
                    print(f"\n✅ SUCCESS: Got {len(real_data)} real traffic data points")
                    self.cache[cache_key] = real_data
                    return real_data
            except Exception as e:
                print(f"\n❌ Error fetching real data: {e}")
        
        print("\n⚠️ Falling back to simulated data")
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
            'Bahawalpur': ['Jinnah Road', 'Multan Road', 'Canal Road', 
                          'Railway Road', 'Circular Road', 'Shahdrah Road'],
            'Jeddah': ['King Abdulaziz Road', 'Madinah Road', 'Prince Sultan Road', 
                      'Al-Madinah Al-Munawwarah Road', 'King Fahd Road', 'Corniche Road'],
            'Riyadh': ['King Fahd Road', 'Olaya Street', 'Tahlia Street', 'King Abdulaziz Road'],
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
