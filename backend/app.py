from flask import Flask, jsonify, request, render_template_string
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
# TRAFFIC PREDICTION WITH ML
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
        'timestamp': datetime.now().isoformat()
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
    try:
        data = request.json or {}
        city = data.get('city', 'Lahore')
        lat = data.get('lat')
        lng = data.get('lng')
        use_multi_vehicle = data.get('use_multi_vehicle', True)
        use_prediction = data.get('use_prediction', True)
        hours_ahead = data.get('hours_ahead', 24)
        
        print(f"🔄 Optimizing for city: {city}")
        if lat and lng:
            print(f"📍 Coordinates: {lat}, {lng}")
        
        traffic_data = traffic_fetcher.get_traffic_data(city, lat, lng)
        
        is_real = any(data.get('is_real', False) for data in traffic_data[:3])
        print(f"📊 Data type: {'REAL (Google API)' if is_real else 'SIMULATED (Fallback)'}")
        print(f"📊 Got {len(traffic_data)} traffic data points")
        
        route_results = route_optimizer.optimize_routes(traffic_data)
        
        # Ensure improvement is shown
        improvement = route_results.get('improvement', 0)
        print(f"✅ Route optimization complete")
        print(f"   Classical cost: {route_results['classical_cost']}")
        print(f"   Quantum cost: {route_results['quantum_cost']}")
        print(f"   Improvement: {improvement:.1f}%")
        
        predictions = None
        if use_prediction:
            predictions = traffic_predictor.predict_future_traffic(city, hours_ahead)
            print(f"📈 Generated {len(predictions)} predictions")
        
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
            'features_used': {
                'multi_vehicle': use_multi_vehicle,
                'prediction': use_prediction,
                'real_time': bool(lat and lng)
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json or {}
        city = data.get('city', 'Lahore')
        hours_ahead = data.get('hours_ahead', 24)
        
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
    return jsonify({
        'status': 'reset',
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# MAIN ENTRY POINT
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


