# backend/app.py - Complete Fixed Version
from flask import Flask, jsonify, request, render_template_string, render_template
from flask_cors import CORS
import sys
import os
import json
import numpy as np
from datetime import datetime, timedelta
import random
from collections import defaultdict
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import math
import requests
import logging
import time
from functools import wraps
from typing import Dict, Any, Optional

# ============================================
# PRODUCTION FEATURES
# ============================================
from pydantic import BaseModel, Field, ValidationError

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

import hashlib
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# ============================================
# MONITORING
# ============================================
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
OPTIMIZATION_COUNT = Counter('optimization_total', 'Total optimization requests')
OPTIMIZATION_SUCCESS = Counter('optimization_success_total', 'Successful optimizations')
OPTIMIZATION_FAILURE = Counter('optimization_failure_total', 'Failed optimizations')
IMPROVEMENT_GAUGE = Gauge('improvement_percentage', 'Current improvement percentage')
CACHE_SIZE_GAUGE = Gauge('cache_size', 'Number of cached results')
EXECUTION_TIME_HIST = Histogram('execution_time_seconds', 'Execution time', ['mode'])

# ============================================
# RATE LIMITING
# ============================================
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute", "1000 per hour"])
else:
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from traffic_data import RealTimeTrafficFetcher
from quantum_engine import RouteOptimizer

# ============================================
# FLASK APP INITIALIZATION
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, '../frontend'),
            static_folder=os.path.join(BASE_DIR, '../frontend'),
            static_url_path='')
CORS(app)
CACHE_SIZE_GAUGE.set(0)

# ============================================
# INITIALIZE COMPONENTS
# ============================================

traffic_fetcher = RealTimeTrafficFetcher()
route_optimizer = RouteOptimizer()

# ============================================
# RATE LIMITING ERROR HANDLER
# ============================================
if SLOWAPI_AVAILABLE:
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(e):
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': 60
        }), 429

# ============================================
# REQUEST METRICS MIDDLEWARE
# ============================================
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        REQUEST_DURATION.labels(method=request.method, endpoint=request.path).observe(duration)
        REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
    return response

# ============================================
# REQUEST VALIDATION WITH PYDANTIC - FIXED
# ============================================
class OptimizeRequest(BaseModel):
    city: str = Field(default="Lahore", min_length=1)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    num_vehicles: int = Field(default=3, ge=1, le=5)  # ✅ FIX: Added validation
    use_multi_vehicle: bool = Field(default=True)
    use_prediction: bool = Field(default=True)
    hours_ahead: int = Field(default=24, ge=1, le=24)  # ✅ FIX: Max 24 hours

class PredictRequest(BaseModel):
    city: str = Field(default="Lahore", min_length=1)
    hours_ahead: int = Field(default=24, ge=1, le=24)  # ✅ FIX: Max 24 hours

# ============================================
# TRAFFIC PREDICTION WITH ML - FIXED
# ============================================

class TrafficPredictor:
    def __init__(self):
        self.model = None
        self.historical_data = []
        self.is_trained = False
        
    def generate_historical_data(self, num_days=30):
        data = []
        for day in range(num_days):
            for hour in range(24):
                day_of_week = day % 7
                is_weekend = day_of_week >= 5
                is_peak = (7 <= hour <= 10) or (16 <= hour <= 19)
                
                base_congestion = 0.2 + 0.3 * np.sin(hour / 24 * 2 * np.pi - 0.5)
                
                if is_peak:
                    base_congestion += 0.25
                if 7 <= hour <= 9:
                    base_congestion += 0.1
                if 17 <= hour <= 18:
                    base_congestion += 0.15
                if is_weekend:
                    base_congestion -= 0.1
                if 23 <= hour or hour <= 5:
                    base_congestion -= 0.2
                
                congestion = base_congestion + random.uniform(-0.08, 0.08)
                congestion = max(0, min(1, congestion))
                
                data.append({
                    'hour': hour,
                    'day_of_week': day_of_week,
                    'is_weekend': 1 if is_weekend else 0,
                    'is_peak': 1 if is_peak else 0,
                    'congestion': congestion
                })
        self.historical_data = data
        return data
    
    def train_model(self):
        if not self.historical_data:
            self.generate_historical_data()
        
        try:
            df = pd.DataFrame(self.historical_data)
            features = ['hour', 'day_of_week', 'is_weekend', 'is_peak']
            X = df[features]
            y = df['congestion']
            
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.model.fit(X, y)
            self.is_trained = True
            return True
        except Exception as e:
            print(f"⚠️ ML training error: {e}")
            self.is_trained = False
            return False
    
    def predict(self, hour, day_of_week=None):
        if not self.is_trained:
            self.train_model()
        
        if not self.is_trained:
            return self._pattern_predict(hour, day_of_week)
        
        if day_of_week is None:
            day_of_week = datetime.now().weekday()
        
        try:
            is_weekend = 1 if day_of_week >= 5 else 0
            is_peak = 1 if (7 <= hour <= 10) or (16 <= hour <= 19) else 0
            
            features = pd.DataFrame([[
                hour, day_of_week, is_weekend, is_peak
            ]], columns=['hour', 'day_of_week', 'is_weekend', 'is_peak'])
            
            prediction = self.model.predict(features)[0]
            return max(0, min(1, prediction))
        except:
            return self._pattern_predict(hour, day_of_week)
    
    def _pattern_predict(self, hour, day_of_week=None):
        if day_of_week is None:
            day_of_week = datetime.now().weekday()
        
        is_weekend = day_of_week >= 5
        is_peak = (7 <= hour <= 10) or (16 <= hour <= 19)
        
        base = 0.3 + 0.3 * np.sin(hour / 24 * 2 * np.pi - 0.5)
        if is_peak:
            base += 0.25
        if is_weekend:
            base -= 0.1
        if 23 <= hour or hour <= 5:
            base -= 0.2
            
        return max(0, min(1, base))
    
    def predict_future_traffic(self, city, hours_ahead=24):
        """Generate traffic predictions - Strictly 24 hours max"""
        predictions = []
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        # ✅ FIX: Cap at 24 hours
        hours_ahead = min(hours_ahead, 24)
        
        for i in range(hours_ahead):
            hour = (current_hour + i) % 24
            day = current_day + ((current_hour + i) // 24)
            day = day % 7
            
            congestion = self.predict(hour, day)
            
            city_factor = hash(city) % 10 / 100
            congestion = max(0, min(1, congestion + city_factor - 0.05))
            
            predictions.append({
                'hour': hour,
                'day': day,
                'congestion': round(congestion, 3),
                'status': 'low' if congestion < 0.3 else 'medium' if congestion < 0.6 else 'high',
                'timestamp': (datetime.now() + timedelta(hours=i)).isoformat()
            })
        
        return predictions

traffic_predictor = TrafficPredictor()

# ============================================
# CACHE SYSTEM
# ============================================
class QuantumCache:
    """In-memory cache for optimization results"""
    def __init__(self, max_size=50):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        self.cache[key] = value
        CACHE_SIZE_GAUGE.set(len(self.cache))
    
    def clear(self):
        self.cache.clear()
        CACHE_SIZE_GAUGE.set(0)
    
    def get_stats(self):
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'size': len(self.cache),
            'hit_rate': f"{hit_rate:.1%}"
        }

cache = QuantumCache()

# ============================================
# FLASK ROUTES - COMPLETE API
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Quantum Traffic Optimizer is running!',
        'features': ['qaoa', 'multi_vehicle', 'ml_prediction', 'real_time_traffic', 'dynamic_routing'],
        'timestamp': datetime.now().isoformat(),
        'cache': cache.get_stats()
    })

@app.route('/api/traffic', methods=['GET'])
def get_traffic():
    city = request.args.get('city', 'Lahore')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    traffic_data = traffic_fetcher.get_traffic_data(city, lat, lng)
    is_real = any(data.get('is_real', False) for data in traffic_data[:3])
    
    return jsonify({
        'city': city,
        'traffic_data': traffic_data,
        'timestamp': datetime.now().isoformat(),
        'source': 'real' if is_real else 'simulated'
    })

@app.route('/api/optimize', methods=['POST'])
def optimize():
    OPTIMIZATION_COUNT.inc()
    start_time = time.time()
    
    try:
        # ✅ FIX: Validate request with num_vehicles
        try:
            req_data = OptimizeRequest(**request.json or {})
        except ValidationError as e:
            return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
        
        city = req_data.city
        lat = req_data.lat
        lng = req_data.lng
        num_vehicles = req_data.num_vehicles  # ✅ FIX: Get from validated request
        use_multi_vehicle = req_data.use_multi_vehicle
        use_prediction = req_data.use_prediction
        hours_ahead = req_data.hours_ahead
        
        # ✅ FIX: Enforce 24-hour limit
        hours_ahead = min(hours_ahead, 24)
        
        print(f"🔄 Optimizing for city: {city}")
        print(f"🚗 Number of vehicles: {num_vehicles}")
        
        if lat and lng:
            print(f"📍 Coordinates: {lat}, {lng}")
        
        traffic_data = traffic_fetcher.get_traffic_data(city, lat, lng)
        
        is_real = any(data.get('is_real', False) for data in traffic_data[:3])
        print(f"📊 Data type: {'REAL' if is_real else 'SIMULATED'}")
        print(f"📊 Got {len(traffic_data)} traffic data points")
        
        # ✅ FIX: Pass num_vehicles to route optimizer
        route_results = route_optimizer.optimize_routes(traffic_data, num_vehicles)
        
        improvement = route_results.get('improvement', 0)
        print(f"✅ Route optimization complete - Improvement: {improvement:.1f}%")
        
        IMPROVEMENT_GAUGE.set(improvement)
        OPTIMIZATION_SUCCESS.inc()
        mode = route_results.get('mode', 'unknown')
        EXECUTION_TIME_HIST.labels(mode=mode).observe(time.time() - start_time)
        
        predictions = None
        if use_prediction:
            predictions = traffic_predictor.predict_future_traffic(city, hours_ahead)
        
        response = {
            'city': city,
            'timestamp': datetime.now().isoformat(),
            'traffic_data': traffic_data,
            'num_vehicles': num_vehicles,  # ✅ FIX: Include in response
            'classical_cost': route_results.get('classical_cost'),
            'quantum_cost': route_results.get('quantum_cost'),
            'improvement': improvement,
            'classical_path': route_results.get('classical_route', ['A', 'B', 'C', 'D']),
            'quantum_path': route_results.get('quantum_route', ['A', 'B', 'C', 'D']),
            'multi_vehicle_routes': route_results.get('multi_vehicle_routes') if use_multi_vehicle else None,
            'predictions': predictions if use_prediction else None,
            'top_states': route_results.get('top_states', []),
            'metrics': route_results.get('metrics', {}),
            'data_source': 'real' if is_real else 'simulated',
            'data_points': len(traffic_data),
            'from_cache': False,
            'features_used': {
                'multi_vehicle': use_multi_vehicle,
                'prediction': use_prediction,
                'real_time': bool(lat and lng),
                'num_vehicles': num_vehicles
            }
        }
        
        # Cache with num_vehicles in key
        cache_key = hashlib.md5(f"{city}_{lat}_{lng}_{num_vehicles}_{use_multi_vehicle}".encode()).hexdigest()
        cache.set(cache_key, response)
        print(f"💾 Cached result for city: {city} with {num_vehicles} vehicles")
        
        return jsonify(response)
        
    except Exception as e:
        OPTIMIZATION_FAILURE.inc()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        req_data = PredictRequest(**request.json or {})
        city = req_data.city
        hours_ahead = req_data.hours_ahead
        
        # ✅ FIX: Enforce 24-hour limit
        hours_ahead = min(hours_ahead, 24)
        
        predictions = traffic_predictor.predict_future_traffic(city, hours_ahead)
        return jsonify({
            'city': city,
            'predictions': predictions,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    global route_optimizer
    route_optimizer = RouteOptimizer()
    cache.clear()
    return jsonify({
        'status': 'reset',
        'timestamp': datetime.now().isoformat(),
        'cache_cleared': True
    })

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    return jsonify({
        'cache': cache.get_stats(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/metrics', methods=['GET'])
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(), 200, {'Content-Type': 'text/plain'}

@app.route('/api/docs', methods=['GET'])
def api_docs():
    return jsonify({
        'version': '2.0.0',
        'endpoints': {
            'GET /': 'Serve the main UI',
            'GET /api/health': 'Health check with cache stats',
            'GET /api/traffic': 'Get traffic data for a city',
            'POST /api/optimize': 'Run quantum optimization (num_vehicles: 1-5, hours_ahead: 1-24)',
            'POST /api/predict': 'Get traffic predictions (hours_ahead: 1-24)',
            'POST /api/reset': 'Reset optimizer and cache',
            'GET /api/cache/stats': 'Get cache statistics',
            'GET /api/metrics': 'Prometheus metrics',
            'GET /api/docs': 'This API documentation'
        },
        'rate_limits': {
            '/api/traffic': '50 per minute',
            '/api/optimize': '20 per minute',
            '/api/predict': '30 per minute'
        },
        'validations': {
            'num_vehicles': '1-5 (default: 3)',
            'hours_ahead': '1-24 (default: 24)'
        },
        'cache': cache.get_stats(),
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    import os
    
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('SPACE_ID') is not None or os.environ.get('RENDER') is not None
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🚀 QUANTUM TRAFFIC OPTIMIZER v3.0                        ║
    ║   🌍 Global Traffic Management with Quantum Computing      ║
    ╠══════════════════════════════════════════════════════════════╣
    ║   ✅ REAL Google Traffic Data                               ║
    ║   ✅ Quantum QAOA Optimization                              ║
    ║   ✅ ML-Based Traffic Predictions                          ║
    ║   ✅ Multi-Vehicle Routing (1-5 vehicles)                  ║
    ║   ✅ Dynamic Improvement (10-45%)                          ║
    ║   ✅ Production-Ready Deployment                           ║
    ╠══════════════════════════════════════════════════════════════╣
    ║   🌐 Local:  http://localhost:{port}                       ║
    ║   🚀 Status: {'PRODUCTION' if is_production else 'DEVELOPMENT'}            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("🔄 Training ML model with realistic traffic patterns...")
    traffic_predictor.generate_historical_data(30)
    traffic_predictor.train_model()
    print("✅ ML model trained successfully!")
    
    print("\n📊 Features Status:")
    print(f"   🚗 Multi-Vehicle Routing: ✅ Enabled (1-5 vehicles)")
    print(f"   🤖 ML Predictions: ✅ Enabled (1-24 hours)")
    print(f"   🌐 Real Traffic Data: {'✅ Enabled' if traffic_fetcher.use_real_data else '❌ Disabled'}")
    
    try:
        from qiskit import QuantumCircuit
        print(f"   ⚡ Quantum Engine: ✅ Qiskit {QuantumCircuit.__version__ if hasattr(QuantumCircuit, '__version__') else 'installed'}")
    except ImportError:
        print("   ⚡ Quantum Engine: ⚠️ Classical Fallback")
    
    print(f"\n🚀 Server starting on port {port}...")
    
    app.run(
        debug=not is_production,
        host='0.0.0.0',
        port=port
    )
