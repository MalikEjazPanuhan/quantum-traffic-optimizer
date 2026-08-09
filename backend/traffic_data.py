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
# DYNAMIC ROAD NAME FETCHING - Google Places API
# ============================================

def get_real_road_names_from_google(lat, lng, api_key):
    """
    Get REAL road names from Google Places API
    Works for ANY city in the world!
    """
    try:
        # Nearby search for roads and intersections
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius': 3000,  # 3km radius
            'types': 'route|intersection',
            'key': api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        roads = []
        if data.get('status') == 'OK':
            for place in data.get('results', [])[:8]:
                name = place.get('name', '')
                # Filter out generic names
                if name and not name.startswith('Unnamed') and len(name) > 2:
                    roads.append({
                        'name': name,
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng']
                    })
        
        # If we have at least 4 roads, return them
        if len(roads) >= 4:
            print(f"✅ Found {len(roads)} real roads from Google Places API")
            return roads
        else:
            print(f"⚠️ Only found {len(roads)} roads, trying text search...")
            return None
            
    except Exception as e:
        print(f"⚠️ Google Places API error: {e}")
        return None


def get_real_road_names_from_google_text_search(city, lat, lng, api_key):
    """
    Fallback: Use Google Places Text Search for major roads
    """
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': f"major roads in {city}",
            'key': api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        roads = []
        if data.get('status') == 'OK':
            for place in data.get('results', [])[:6]:
                name = place.get('name', '')
                if name and not name.startswith('Unnamed'):
                    roads.append({
                        'name': name,
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng']
                    })
        return roads if len(roads) >= 4 else None
    except Exception as e:
        print(f"⚠️ Text search error: {e}")
        return None


# ============================================
# FALLBACK: HARDCODED CITY ROADS
# ============================================

def get_fallback_roads(city, lat, lng):
    """Fallback hardcoded roads for known cities"""
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
        'Dammam': [
            {'name': 'King Fahd Road', 'lat': 26.4207, 'lng': 50.0888},
            {'name': 'Prince Mohammed Street', 'lat': 26.4307, 'lng': 50.0988},
            {'name': 'Dammam Corniche', 'lat': 26.4107, 'lng': 50.0788},
            {'name': 'King Abdulaziz Road', 'lat': 26.4407, 'lng': 50.0688},
        ],
        'Tokyo': [
            {'name': 'Shibuya Crossing', 'lat': 35.6595, 'lng': 139.7006},
            {'name': 'Omotesando', 'lat': 35.6654, 'lng': 139.7065},
            {'name': 'Ginza', 'lat': 35.6710, 'lng': 139.7630},
            {'name': 'Shinjuku', 'lat': 35.6895, 'lng': 139.6917},
        ],
        'Singapore': [
            {'name': 'Orchard Road', 'lat': 1.3039, 'lng': 103.8318},
            {'name': 'Marina Bay', 'lat': 1.2834, 'lng': 103.8607},
            {'name': 'Sentosa', 'lat': 1.2494, 'lng': 103.8302},
            {'name': 'Changi', 'lat': 1.3644, 'lng': 103.9915},
        ],
        'Istanbul': [
            {'name': 'Istiklal Avenue', 'lat': 41.0347, 'lng': 28.9789},
            {'name': 'Bagdat Avenue', 'lat': 40.9914, 'lng': 29.0312},
            {'name': 'Bosphorus', 'lat': 41.0455, 'lng': 29.0135},
            {'name': 'Sultanahmet', 'lat': 41.0082, 'lng': 28.9784},
        ],
    }
    
    # Try to find the city (case-insensitive)
    for key in city_roads:
        if key.lower() in city.lower() or city.lower() in key.lower():
            print(f"✅ Found fallback roads for {city}")
            return city_roads[key]
    
    # If city not found, generate points around the location
    print(f"⚠️ No fallback roads for {city}, generating points")
    return [
        {'name': f'Point {i+1}', 'lat': lat + (i*0.015), 'lng': lng + (i*0.01)} 
        for i in range(4)
    ]


# ============================================
# MAIN FUNCTION: GET REAL ROAD DATA
# ============================================

def get_real_road_data(city, lat, lng):
    """
    Get REAL road data - DYNAMIC from Google Places API
    Falls back to hardcoded roads if API fails
    """
    
    print(f"\n🌐 Fetching real roads for '{city}' from Google Places...")
    
    intersections = None
    
    # STRATEGY 1: Try Google Places API (Works for ANY city)
    try:
        intersections = get_real_road_names_from_google(lat, lng, GOOGLE_MAPS_API_KEY)
        if intersections and len(intersections) >= 4:
            print(f"✅ Using {len(intersections)} roads from Google Places API")
    except Exception as e:
        print(f"⚠️ Google Places API failed: {e}")
    
    # STRATEGY 2: If Places API fails, try Text Search
    if not intersections or len(intersections) < 4:
        try:
            print("🔄 Trying Google Places Text Search...")
            intersections = get_real_road_names_from_google_text_search(city, lat, lng, GOOGLE_MAPS_API_KEY)
            if intersections and len(intersections) >= 4:
                print(f"✅ Using {len(intersections)} roads from Text Search")
        except Exception as e:
            print(f"⚠️ Text Search failed: {e}")
    
    # STRATEGY 3: Fallback to hardcoded roads
    if not intersections or len(intersections) < 4:
        print(f"🔄 Using fallback roads for '{city}'")
        intersections = get_fallback_roads(city, lat, lng)
        print(f"✅ Using {len(intersections)} fallback roads")
    
    # Now get traffic data for each road pair
    print(f"\n📊 Getting traffic data for {len(intersections)} roads...")
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
                    delay_factor = 0.1
                elif congestion < 0.6:
                    status = 'medium'
                    color = '#FFC107'
                    delay_factor = 0.3
                else:
                    status = 'high'
                    color = '#F44336'
                    delay_factor = 0.6
                
                speed = 60 - (congestion * 40)
                
                traffic_data.append({
                    'road': road_name,
                    'congestion': congestion,
                    'status': status,
                    'color': color,
                    'speed': round(speed, 1),
                    'travel_time': real_data['travel_time_minutes'],
                    'distance_km': real_data['distance_km'],
                    'delay_factor': delay_factor,
                    'event': None,
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
                print(f"\n{'='*60}")
                print(f"🌍 FETCHING REAL TRAFFIC DATA FOR: {city.upper()}")
                print(f"{'='*60}")
                real_data = get_real_road_data(city, lat, lng)
                if real_data and len(real_data) > 0:
                    print(f"\n✅ SUCCESS: Got {len(real_data)} real traffic data points")
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
                       'Madison Avenue', 'Lexington Avenue']
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
                delay_factor = 0.1
            elif congestion < 0.6:
                status = 'medium'
                color = '#FFC107'
                delay_factor = 0.3
            else:
                status = 'high'
                color = '#F44336'
                delay_factor = 0.6
                
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
                'delay_factor': delay_factor,
                'event': event,
                'timestamp': current_time.isoformat(),
                'is_real': False
            })
            
        return traffic_data

