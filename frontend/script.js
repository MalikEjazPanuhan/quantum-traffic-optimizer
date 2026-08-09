// Google Maps initialization
function initMap() {
    var defaultCity = { lat: 31.5204, lng: 74.3587 };
    window.map = new google.maps.Map(document.getElementById('map'), {
        center: defaultCity,
        zoom: 13,
        gestureHandling: 'cooperative',
        styles: [
            { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
            { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
            { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] }
        ]
    });
    window.trafficLayer = new google.maps.TrafficLayer();
    window.trafficLayer.setMap(window.map);

    window.markers = [];
    window.classicalRoutePolyline = null;
    window.quantumRoutePolyline = null;

    addMarkers(31.5204, 74.3587);

    var input = document.getElementById('citySearchInput');
    window.autocomplete = new google.maps.places.Autocomplete(input, { types: ['(cities)'] });
    window.autocomplete.addListener('place_changed', onPlaceChanged);

    console.log('Map loaded with analytics dashboard!');
}

function getMarkerPositions(lat, lng) {
    // Generate up to 8 markers for routes A-H
    var positions = [];
    var labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
    var count = 8;
    
    for (var i = 0; i < count; i++) {
        var angle = (i / count) * 2 * Math.PI;
        var radius = 0.025;
        var offsetLat = radius * Math.cos(angle);
        var offsetLng = radius * Math.sin(angle);
        positions.push({
            lat: lat + offsetLat,
            lng: lng + offsetLng,
            label: labels[i]
        });
    }
    return positions;
}

function addMarkers(lat, lng) {
    if (window.markers) {
        window.markers.forEach(m => m.setMap(null));
    }
    window.markers = [];
    var positions = getMarkerPositions(lat, lng);
    
    // Add up to 8 markers
    for (var i = 0; i < positions.length; i++) {
        var pos = positions[i];
        var marker = new google.maps.Marker({
            position: { lat: pos.lat, lng: pos.lng },
            map: window.map,
            label: pos.label,
            title: 'Intersection ' + pos.label
        });
        window.markers.push(marker);
    }
    updateRoadStatus();
}

function goToCity(lat, lng, name) {
    if (!window.map) return;
    window.map.setCenter({ lat: lat, lng: lng });
    window.map.setZoom(13);
    document.getElementById('currentCityDisplay').textContent = name;
    window.currentLat = lat;
    window.currentLng = lng;
    window.currentCityName = name;
    clearRoutes();
    addMarkers(lat, lng);
    fetchTrafficData(lat, lng, name);
}

function onPlaceChanged() {
    var place = window.autocomplete.getPlace();
    if (!place.geometry) { alert('No details available. Please try another.'); return; }
    goToCity(place.geometry.location.lat(), place.geometry.location.lng(), place.name || 'Selected City');
}

function fetchTrafficData(lat, lng, city) {
    var url = `/api/traffic?city=${encodeURIComponent(city)}&lat=${lat}&lng=${lng}`;
    fetch(url).then(res => res.json()).then(data => {
        updateRoadStatus(data.traffic_data);
    }).catch(err => console.error('Error fetching traffic:', err));
}

function updateRoadStatus(trafficData) {
    var container = document.getElementById('roadSegments');
    if (!trafficData || trafficData.length === 0) {
        container.innerHTML = '<div class="road-segment"><span class="route">No data available</span></div>';
        return;
    }
    container.innerHTML = '';
    trafficData.slice(0, 4).forEach(function(item) {
        var div = document.createElement('div');
        div.className = 'road-segment';
        div.innerHTML = '<span class="route">' + item.road + '</span>' +
            '<span class="status"><span class="status-dot-small" style="background:' + item.color + ';"></span> ' +
            item.status + ' (' + (item.congestion * 100).toFixed(0) + '%)</span>';
        container.appendChild(div);
    });
}

function clearRoutes() {
    if (window.classicalRoutePolyline) { window.classicalRoutePolyline.setMap(null);
        window.classicalRoutePolyline = null; }
    if (window.quantumRoutePolyline) { window.quantumRoutePolyline.setMap(null);
        window.quantumRoutePolyline = null; }
    document.getElementById('resultsPanel').classList.remove('show');
    document.getElementById('predictionSection').style.display = 'none';
    document.getElementById('vehicleRoutes').style.display = 'none';
    document.getElementById('placeholder').style.display = 'flex';
}

function drawRoutes(lat, lng, classicalOrder, quantumOrder) {
    var positions = getMarkerPositions(lat, lng);

    if (window.classicalRoutePolyline) {
        window.classicalRoutePolyline.setMap(null);
        window.classicalRoutePolyline = null;
    }
    if (window.quantumRoutePolyline) {
        window.quantumRoutePolyline.setMap(null);
        window.quantumRoutePolyline = null;
    }

    function buildPath(order) {
        var path = [];
        if (!order) return path;
        for (var i = 0; i < order.length; i++) {
            var idx = order[i].charCodeAt(0) - 65;
            if (idx >= 0 && idx < positions.length) {
                path.push({ lat: positions[idx].lat, lng: positions[idx].lng });
            }
        }
        return path;
    }

    var classicalPath = buildPath(classicalOrder);
    if (classicalPath.length > 1) {
        window.classicalRoutePolyline = new google.maps.Polyline({
            path: classicalPath,
            geodesic: true,
            strokeColor: '#f87171',
            strokeOpacity: 0.9,
            strokeWeight: 5,
            map: window.map
        });
    }

    var quantumPath = buildPath(quantumOrder);
    if (quantumPath.length > 1) {
        window.quantumRoutePolyline = new google.maps.Polyline({
            path: quantumPath,
            geodesic: true,
            strokeColor: '#4ade80',
            strokeOpacity: 0.9,
            strokeWeight: 5,
            map: window.map
        });
    }
}

function displayResults(data) {
    console.log('Displaying results:', data);

    document.getElementById('placeholder').style.display = 'none';
    document.getElementById('resultsPanel').classList.add('show');

    var sourceElement = document.getElementById('dataSource');
    if (data.data_source === 'real') {
        sourceElement.textContent = '✅ LIVE REAL DATA (Google API)';
        sourceElement.className = 'source real';
    } else {
        sourceElement.textContent = '🔄 SIMULATED DATA (Demo)';
        sourceElement.className = 'source simulated';
    }
    document.getElementById('dataTimestamp').textContent = '🕐 ' + new Date().toLocaleTimeString();

    var improvement = data.improvement || 0;
    document.getElementById('improvementValue').textContent = improvement.toFixed(1) + '%';

    var metrics = data.metrics || {};
    document.getElementById('timeSavedValue').textContent = (metrics.time_saved_minutes || '--') + ' min';
    document.getElementById('fuelSavedValue').textContent = (metrics.fuel_saved_liters || '--') + ' L';
    document.getElementById('co2Value').textContent = (metrics.co2_reduced_kg || '--') + ' kg';

    var classicalCost = data.classical_cost || 1;
    var quantumCost = data.quantum_cost || 1;
    var maxCost = Math.max(classicalCost, quantumCost, 1);
    var classicalHeight = (classicalCost / maxCost) * 150;
    var quantumHeight = (quantumCost / maxCost) * 150;

    document.getElementById('classicalBar').style.height = Math.max(classicalHeight, 20) + 'px';
    document.getElementById('quantumBar').style.height = Math.max(quantumHeight, 20) + 'px';
    document.getElementById('classicalBarValue').textContent = classicalCost.toFixed(2);
    document.getElementById('quantumBarValue').textContent = quantumCost.toFixed(2);

    document.getElementById('efficiencyValue').textContent = (metrics.efficiency_improvement || '--') + '%';
    document.getElementById('congestionValue').textContent = (metrics.congestion_reduction || '--') + '%';

    var advantage = metrics.quantum_advantage || 0;
    document.getElementById('advantagePercent').textContent = advantage + '%';
    document.getElementById('advantageFill').style.width = Math.min(advantage, 100) + '%';
    document.getElementById('advantageFill').textContent = Math.min(advantage, 100) + '%';

    document.getElementById('classicalCost').textContent = classicalCost.toFixed(2);
    document.getElementById('quantumCost').textContent = quantumCost.toFixed(2);

    var classicalPath = data.classical_path || ['A', 'B', 'C', 'D'];
    var quantumPath = data.quantum_path || ['A', 'C', 'D', 'B'];
    document.getElementById('classicalPath').textContent = classicalPath.join(' → ');
    document.getElementById('quantumPath').textContent = quantumPath.join(' → ');

    if (improvement > 0) {
        var badge = document.getElementById('improvementBadge');
        badge.style.display = 'inline-block';
        badge.textContent = '✨ ' + improvement.toFixed(1) + '% Better';
    }

    var grid = document.getElementById('statesGrid');
    grid.innerHTML = '';
    var topStates = data.top_states || [];
    if (topStates.length > 0) {
        topStates.forEach(function(s) {
            var div = document.createElement('div');
            div.className = 'state-item';
            div.innerHTML = '<span class="label">|' + s.state + '></span><span class="count">' + s.count + ' (' + s.percentage.toFixed(1) + '%)</span>';
            grid.appendChild(div);
        });
    }

    // Draw routes with up to 8 markers
    drawRoutes(window.currentLat || 31.5204, window.currentLng || 74.3587,
        classicalPath, quantumPath);

    var predictions = data.predictions || [];
    if (predictions.length > 0) {
        document.getElementById('predictionSection').style.display = 'block';
        displayPredictions(predictions);
    }

    var multiVehicle = data.multi_vehicle_routes || null;
    if (multiVehicle && multiVehicle.routes && multiVehicle.routes.length > 0) {
        document.getElementById('vehicleRoutes').style.display = 'block';
        displayVehicleRoutes(multiVehicle);
    }
}

function displayPredictions(predictions) {
    var container = document.getElementById('predictionChart');
    var html = '';
    var maxCongestion = Math.max(...predictions.map(p => p.congestion), 0.1);
    predictions.slice(0, 24).forEach(function(pred) {
        var height = (pred.congestion / maxCongestion) * 100;
        var color = pred.congestion < 0.3 ? '#4CAF50' : pred.congestion < 0.6 ? '#FFC107' : '#F44336';
        html += '<div class="prediction-bar-container">' +
            '<div class="prediction-bar" style="height:' + Math.max(height, 5) + 'px;background:' + color + ';"></div>' +
            '<div class="prediction-label">' + pred.hour + 'h</div>' +
            '</div>';
    });
    container.innerHTML = html;
}

function displayVehicleRoutes(routes) {
    var container = document.getElementById('routesDisplay');
    var html = '<div style="color:#888;font-size:12px;margin-bottom:8px;">Total Vehicles: ' + routes.num_vehicles + '</div>';
    routes.routes.forEach(function(route, index) {
        html += '<div class="vehicle-route">' +
            '<span class="vehicle-label">🚗 Vehicle ' + (index + 1) + '</span>' +
            '<div class="route-path">' + route.join(' → ') + '</div>' +
            '</div>';
    });
    container.innerHTML = html;
}

function setStatus(text, loading) {
    document.getElementById('statusText').textContent = text;
    var dot = document.getElementById('statusDot');
    dot.className = 'status-dot';
    if (loading) dot.classList.add('loading');
}

// Quick City Selection Function
function quickCity(cityName) {
    document.getElementById('citySearchInput').value = cityName;
    document.getElementById('searchCityBtn').click();
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('goToCityBtn').addEventListener('click', function() {
        var input = document.getElementById('citySearchInput');
        if (input.value.trim()) {
            // Use the search function to find the city
            document.getElementById('searchCityBtn').click();
        } else {
            alert('Please search for a city first');
        }
    });

    document.getElementById('searchCityBtn').addEventListener('click', function() {
        var input = document.getElementById('citySearchInput');
        if (!input.value.trim()) { alert('Please enter a city name'); return; }
        var geocoder = new google.maps.Geocoder();
        geocoder.geocode({ address: input.value }, function(results, status) {
            if (status === 'OK') {
                var lat = results[0].geometry.location.lat();
                var lng = results[0].geometry.location.lng();
                var name = results[0].formatted_address || input.value;
                goToCity(lat, lng, name);
            } else {
                alert('City not found. Please try again.');
            }
        });
    });

    document.getElementById('citySearchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') document.getElementById('searchCityBtn').click();
    });

    document.getElementById('clearRoutesBtn').addEventListener('click', function() {
        clearRoutes();
        setStatus('Routes cleared', false);
        document.getElementById('placeholder').style.display = 'flex';
    });

    document.getElementById('multiVehicle').addEventListener('change', function() {
        var badge = document.getElementById('mvBadge');
        badge.textContent = this.checked ? 'Multi-Vehicle' : 'Multi-Vehicle OFF';
        badge.className = 'feature-badge ' + (this.checked ? 'active' : 'inactive');
    });

    document.getElementById('usePrediction').addEventListener('change', function() {
        var badge = document.getElementById('predBadge');
        badge.textContent = this.checked ? 'ML Prediction' : 'Prediction OFF';
        badge.className = 'feature-badge ' + (this.checked ? 'active' : 'inactive');
    });

    document.getElementById('runBtn').addEventListener('click', function() {
        if (window.isRunning) return;
        window.isRunning = true;
        var btn = this;
        btn.disabled = true;
        btn.textContent = '⏳ Running...';
        setStatus('Optimizing...', true);
        document.getElementById('loadingOverlay').classList.add('show');
        document.getElementById('loadingStatus').textContent = 'Processing real-time traffic data...';

        var payload = {
            city: document.getElementById('currentCityDisplay').textContent,
            lat: window.currentLat || 31.5204,
            lng: window.currentLng || 74.3587,
            use_multi_vehicle: document.getElementById('multiVehicle').checked,
            num_vehicles: parseInt(document.getElementById('numVehicles').value) || 3,
            use_prediction: document.getElementById('usePrediction').checked,
            hours_ahead: parseInt(document.getElementById('hoursAhead').value) || 24
        };

        console.log('Sending payload:', payload);

        fetch('/api/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(res => res.json())
            .then(data => {
                console.log('Received data:', data);
                if (data.error) {
                    alert('Error: ' + data.error);
                    setStatus('Error', false);
                    return;
                }
                displayResults(data);
                setStatus('✅ Done - Quantum Optimized!', false);
                document.getElementById('loadingStatus').textContent = 'Optimization complete!';
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Error: ' + err.message);
                setStatus('Error', false);
            })
            .finally(function() {
                window.isRunning = false;
                btn.disabled = false;
                btn.textContent = '⚡ Run Quantum';
                setTimeout(() => document.getElementById('loadingOverlay').classList.remove('show'), 500);
            });
    });

    document.getElementById('resetBtn').addEventListener('click', function() {
        fetch('/api/reset', { method: 'POST' })
            .then(() => { clearRoutes();
                setStatus('Ready', false); });
    });

    fetch('/api/health')
        .then(() => setStatus('✅ Connected', false))
        .catch(() => setStatus('Offline', false));

    window.currentLat = 31.5204;
    window.currentLng = 74.3587;
    window.currentCityName = 'Lahore';
    window.isRunning = false;
});
