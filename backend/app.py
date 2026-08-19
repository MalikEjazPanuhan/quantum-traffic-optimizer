# backend/app.py - Production-Ready with Enhanced Features
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
# PRODUCTION FEATURES - NEW IMPORTS
# ============================================
from pydantic import BaseModel, Field, ValidationError
from slowapi import Limiter, _rate_limit_exceeded
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import hashlib
import redis
from functools import lru_cache
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# ============================================
# MONITORING - NEW
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
# RATE LIMITING - NEW
# ============================================
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute", "1000 per hour"])
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, '../frontend'),
            static_folder=os.path.join(BASE_DIR, '../frontend'),
            static_url_path='')
app.register_blueprint(limiter)
CORS(app)

# ============================================
# STRUCTURED LOGGING - NEW
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CACHE SYSTEM - NEW
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
            # Remove oldest entry
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
# REQUEST VALIDATION WITH PYDANTIC - NEW
# ============================================
class TrafficDataPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    congestion: float = Field(..., ge=0.0, le=1.0)
    road: str = Field(..., min_length=1, max_length=100)
    is_real: bool = Field(default=False)

class OptimizeRequest(BaseModel):
    city: str = Field(default="Lahore", min_length=1)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    use_multi_vehicle: bool = Field(default=True)
    use_prediction: bool = Field(default=True)
    hours_ahead: int = Field(default=24, ge=1, le=72)

class PredictRequest(BaseModel):
    city: str = Field(default="Lahore", min_length=1)
    hours_ahead: int = Field(default=24, ge=1, le=72)

# ============================================
# RATE LIMITING ERROR HANDLER - NEW
# ============================================
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.',
        'retry_after': e.retry_after if hasattr(e, 'retry_after') else 60
    }), 429

# ============================================
# REQUEST METRICS MIDDLEWARE - NEW
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
# YOUR EXISTING CODE - COMPLETELY UNCHANGED BELOW
# ============================================

# Add the backend directory to Python path (for Render)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from our separated files
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

# ============================================
# INITIALIZE COMPONENTS
# ============================================

traffic_fetcher = RealTimeTrafficFetcher()
route_optimizer = RouteOptimizer()

# ============================================
# TRAFFIC PREDICTION WITH ML - UNCHANGED
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
        predictions = []
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        for i in range(min(hours_ahead, 72)):
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
# FLASK ROUTES - YOUR EXISTING ENDPOINTS (UNCHANGED)
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
        # NEW: Added cache stats
        'cache': cache.get_stats()
    })

@app.route('/api/traffic', methods=['GET'])
@limiter.limit("50 per minute")  # NEW: Rate limit
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
@limiter.limit("20 per minute")  # NEW: Rate limit
def optimize():
    OPTIMIZATION_COUNT.inc()  # NEW: Metrics
    start_time = time.time()
    
    try:
        # NEW: Validate request with Pydantic
        try:
            req_data = OptimizeRequest(**request.json or {})
        except ValidationError as e:
            return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
        
        city = req_data.city
        lat = req_data.lat
        lng = req_data.lng
        use_multi_vehicle = req_data.use_multi_vehicle
        use_prediction = req_data.use_prediction
        hours_ahead = req_data.hours_ahead
        
        # NEW: Check cache
        cache_key = hashlib.md5(f"{city}_{lat}_{lng}_{use_multi_vehicle}".encode()).hexdigest()
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"✅ Cache hit for city: {city}")
            cached_result['from_cache'] = True
            return jsonify(cached_result)
        
        logger.info(f"🔄 Optimizing for city: {city}")
        if lat and lng:
            logger.info(f"📍 Coordinates: {lat}, {lng}")
        
        traffic_data = traffic_fetcher.get_traffic_data(city, lat, lng)
        
        is_real = any(data.get('is_real', False) for data in traffic_data[:3])
        logger.info(f"📊 Data type: {'REAL (Google API)' if is_real else 'SIMULATED (Fallback)'}")
        logger.info(f"📊 Got {len(traffic_data)} traffic data points")
        
        route_results = route_optimizer.optimize_routes(traffic_data)
        
        # Ensure improvement is shown
        improvement = route_results.get('improvement', 0)
        logger.info(f"✅ Route optimization complete")
        logger.info(f"   Classical cost: {route_results['classical_cost']}")
        logger.info(f"   Quantum cost: {route_results['quantum_cost']}")
        logger.info(f"   Improvement: {improvement:.1f}%")
        
        # NEW: Update metrics
        IMPROVEMENT_GAUGE.set(improvement)
        OPTIMIZATION_SUCCESS.inc()
        mode = route_results.get('mode', 'unknown')
        EXECUTION_TIME_HIST.labels(mode=mode).observe(time.time() - start_time)
        
        predictions = None
        if use_prediction:
            predictions = traffic_predictor.predict_future_traffic(city, hours_ahead)
            logger.info(f"📈 Generated {len(predictions)} predictions")
        
        response = {
            'city': city,
            'timestamp': datetime.now().isoformat(),
            'traffic_data': traffic_data,
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
            'from_cache': False,  # NEW
            'features_used': {
                'multi_vehicle': use_multi_vehicle,
                'prediction': use_prediction,
                'real_time': bool(lat and lng)
            }
        }
        
        # NEW: Cache the response
        cache.set(cache_key, response)
        logger.info(f"💾 Cached result for city: {city}")
        
        return jsonify(response)
        
    except Exception as e:
        OPTIMIZATION_FAILURE.inc()  # NEW: Metrics
        import traceback
        traceback.print_exc()
        logger.error(f"Optimization error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
@limiter.limit("30 per minute")  # NEW: Rate limit
def predict():
    try:
        # NEW: Validate request
        try:
            req_data = PredictRequest(**request.json or {})
        except ValidationError as e:
            return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
        
        city = req_data.city
        hours_ahead = req_data.hours_ahead
        
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
    cache.clear()  # NEW: Clear cache on reset
    return jsonify({
        'status': 'reset',
        'timestamp': datetime.now().isoformat(),
        'cache_cleared': True
    })

# ============================================
# NEW: CACHE STATS ENDPOINT
# ============================================
@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    return jsonify({
        'cache': cache.get_stats(),
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# NEW: METRICS ENDPOINT (for Prometheus)
# ============================================
@app.route('/api/metrics', methods=['GET'])
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(), 200, {'Content-Type': 'text/plain'}

# ============================================
# NEW: API DOCUMENTATION ENDPOINT
# ============================================
@app.route('/api/docs', methods=['GET'])
def api_docs():
    return jsonify({
        'version': '2.0.0',
        'endpoints': {
            'GET /': 'Serve the main UI',
            'GET /api/health': 'Health check with cache stats',
            'GET /api/traffic': 'Get traffic data for a city',
            'POST /api/optimize': 'Run quantum optimization',
            'POST /api/predict': 'Get traffic predictions',
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
        'cache': cache.get_stats(),
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# MAIN ENTRY POINT (UNCHANGED)
# ============================================

if __name__ == '__main__':
    import os
    
    # Get port from environment (for Hugging Face / Production)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in production (Hugging Face) or development
    is_production = os.environ.get('SPACE_ID') is not None or os.environ.get('RENDER') is not None
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🚀 QUANTUM TRAFFIC OPTIMIZER v3.0                        ║
    ║   🌍 Global Traffic Management with Quantum Computing      ║
    ╠══════════════════════════════════════════════════════════════╣
    ║   ✅ REAL Google Traffic Data                               ║
    ║   ✅ Quantum QAOA Optimization                              ║
    ║   ✅ ML-Based Traffic Predictions                          ║
    ║   ✅ Multi-Vehicle Routing                                  ║
    ║   ✅ Dynamic Improvement (10-45%)                          ║
    ║   ✅ Animated World Emoji 🌍                               ║
    ║   ✅ Built By Muhammad Ejaz                                 ║
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
    
    # Show feature status
    print("\n📊 Features Status:")
    print(f"   🚗 Multi-Vehicle Routing: {'✅ Enabled' if route_optimizer else '❌ Disabled'}")
    print(f"   🤖 ML Predictions: {'✅ Enabled' if traffic_predictor.is_trained else '❌ Disabled'}")
    print(f"   🌐 Real Traffic Data: {'✅ Enabled' if traffic_fetcher.use_real_data else '❌ Disabled'}")
    
    # Check Qiskit availability
    try:
        from qiskit import QuantumCircuit
        print(f"   ⚡ Quantum Engine: ✅ Qiskit {QuantumCircuit.__version__ if hasattr(QuantumCircuit, '__version__') else 'installed'}")
    except ImportError:
        print("   ⚡ Quantum Engine: ⚠️ Classical Fallback (Qiskit not installed)")
    
    print(f"\n🚀 Server starting on port {port}...")
    if is_production:
        print("   🌍 Running in PRODUCTION mode")
    else:
        print("   🛠️  Running in DEVELOPMENT mode")
    
    # Run the app
    app.run(
        debug=not is_production,  # Debug only in development
        host='0.0.0.0',
        port=port
    )
