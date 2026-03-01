from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import math

app = Flask(__name__)
CORS(app)

API_KEY = 'AIzaSyA5ZgfCAleSG9recc2XwpR59Kaw4oJExFY'

def execute_mcdm_ranking(hospitals, triage_level, category):
    n = len(hospitals)
    if n == 0: return []
    if n == 1:
        hospitals[0]['mcdm_score'] = 1.0
        return hospitals

    # 🚨 PURE DISTANCE OVERRIDE
    if triage_level == 'Nearest' or triage_level == 'Level 1':
        hospitals.sort(key=lambda x: x['duration_sec'])
        for i, h in enumerate(hospitals):
            h['mcdm_score'] = 1.0 - (i * 0.05) 
        return hospitals[:5]

    # 🟠 & 🟢 LEVEL 2 & 3: ENTROPY + CONTEXT WEIGHTING
    max_t = max(h['duration_sec'] for h in hospitals)
    min_t = min(h['duration_sec'] for h in hospitals)

    for h in hospitals:
        h['x_time'] = (max_t - h['duration_sec']) / (max_t - min_t) if max_t != min_t else 1.0
        h['x_spec'] = h['specialty_match']
        h['x_rat'] = h['rating'] / 5.0

    k = 1.0 / math.log(n)
    entropy = {'time': 0, 'spec': 0, 'rat': 0}
    
    for crit in ['time', 'spec', 'rat']:
        x_key = f'x_{crit}'
        sum_x = sum(h[x_key] for h in hospitals)
        if sum_x == 0: continue
            
        e_j = 0
        for h in hospitals:
            p_ij = h[x_key] / sum_x
            if p_ij > 0: e_j += p_ij * math.log(p_ij)
        entropy[crit] = -k * e_j

    d = {crit: 1 - entropy[crit] for crit in ['time', 'spec', 'rat']}
    sum_d = sum(d.values()) if sum(d.values()) > 0 else 1
    w_entropy = {crit: d[crit] / sum_d for crit in ['time', 'spec', 'rat']}

    f_scale = {'time': 1.0, 'spec': 1.0, 'rat': 1.0}
    if triage_level == 'Level 2': 
        f_scale = {'time': 2.0, 'spec': 1.5, 'rat': 1.0} 
    elif triage_level == 'Level 3': 
        f_scale = {'time': 0.1, 'spec': 3.5, 'rat': 2.5} 

    w_unnorm = {crit: w_entropy[crit] * f_scale[crit] for crit in ['time', 'spec', 'rat']}
    sum_w = sum(w_unnorm.values())
    w_final = {crit: w_unnorm[crit] / sum_w for crit in ['time', 'spec', 'rat']}

    for h in hospitals:
        h['mcdm_score'] = (w_final['time'] * h['x_time']) + (w_final['spec'] * h['x_spec']) + (w_final['rat'] * h['x_rat'])

    hospitals.sort(key=lambda x: x['mcdm_score'], reverse=True)
    return hospitals[:5]


@app.route('/rank_hospitals', methods=['POST'])
def rank_hospitals():
    data = request.json
    user_lat, user_lng = data.get('lat'), data.get('lng')
    category = data.get('category', 'Cardiac').split(' ')[0] 
    situation = data.get('situation', 'Level 2')
    ambulance_mode = data.get('ambulance', False)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location,places.rating,places.userRatingCount,places.currentOpeningHours,places.regularOpeningHours,places.types,places.nationalPhoneNumber,places.googleMapsUri"
    }

    raw_places = []
    places_url_nearby = "https://places.googleapis.com/v1/places:searchNearby"
    places_url_text = "https://places.googleapis.com/v1/places:searchText"

    # 🔥 THE FIX: DUAL-API CASCADE FALLBACK FOR EMERGENCY OVERRIDE
    if 'Nearest' in situation:
        # Fetch 1: Grab the 20 absolute physical closest
        payload_nearby = {
            "includedTypes": ["hospital"],
            "locationRestriction": {
                "circle": {"center": {"latitude": user_lat, "longitude": user_lng}, "radius": 20000.0}
            },
            "rankPreference": "DISTANCE",
            "maxResultCount": 20
        }
        try:
            r1 = requests.post(places_url_nearby, json=payload_nearby, headers=headers).json()
            raw_places.extend(r1.get('places', []))
        except: pass

        # Fetch 2: Upper-Level Fallback (Grab 20 prominent legit hospitals nearby)
        payload_text = {
            "textQuery": "Hospital",
            "locationBias": {
                "circle": {"center": {"latitude": user_lat, "longitude": user_lng}, "radius": 20000.0}
            },
            "maxResultCount": 20
        }
        try:
            r2 = requests.post(places_url_text, json=payload_text, headers=headers).json()
            raw_places.extend(r2.get('places', []))
        except: pass

    else:
        # Standard Level 1, 2, 3 Logic
        search_query = f"24 hours Emergency Hospital" if 'Level 1' in situation else (f"24 hours {category} Hospital" if 'Level 2' in situation else f"Best {category} Specialist Hospital")
        radius_meters = 15000.0 if 'Level 1' in situation or 'Level 2' in situation else 25000.0
        payload_text = {
            "textQuery": search_query,
            "locationBias": {
                "circle": {"center": {"latitude": user_lat, "longitude": user_lng}, "radius": radius_meters}
            },
            "maxResultCount": 20
        }
        try:
            r = requests.post(places_url_text, json=payload_text, headers=headers).json()
            raw_places.extend(r.get('places', []))
        except: pass

    # Deduplicate the merged lists
    seen_names = set()
    unique_places = []
    for p in raw_places:
        name = p.get('displayName', {}).get('text', '').lower()
        if name not in seen_names:
            seen_names.add(name)
            unique_places.append(p)
    raw_places = unique_places

    valid_hospitals = []

    for p in raw_places:
        name = p.get('displayName', {}).get('text', '').lower()
        rating = p.get('rating', 0)
        reviews = p.get('userRatingCount', 0)
        
        curr_hours = p.get('currentOpeningHours', {})
        reg_hours = p.get('regularOpeningHours', {})
        
        is_open = curr_hours.get('openNow')
        if is_open is None:
            is_open = reg_hours.get('openNow', None)
            
        types = p.get('types', [])
        phone = p.get('nationalPhoneNumber', 'No Phone Available')
        maps_url = p.get('googleMapsUri', '#')

        if is_open is False: 
            continue 

        # 🚨 THE BASELINE LEGITIMACY FILTER
        if 'Nearest' in situation:
            if reviews < 10: continue
        elif 'Level 1' in situation:
            if is_open is not True or reviews < 10: continue 
        else:
            if is_open is not True or reviews < 30: continue 

        # 🚨 AGGRESSIVE JUNK, PHARMACY & TRANSIT FILTER
        junk_words = [
            "ayurveda", "dental", "clinic", "psychiatry", "block", 
            "blood bank", "office", "quarters", "hostel", "eye", 
            "vision", "scan", "diagnostic", "rehab", "mri", "x-ray",
            "aushadhi", "kendra", "pharmacy", "medical store", "pharma",
            "bus", "stop", "station", "terminal", "transit",
            "store", "stores", "chemist", "dispensary"
        ]
        
        if any(junk in name for junk in junk_words): 
            continue

        specialty_match = 0
        if category.lower() in name or 'specialist' in types or 'specialty' in name:
            specialty_match = 1
        elif 'hospital' in types:
            specialty_match = 0.5

        valid_hospitals.append({
            'name': p.get('displayName', {}).get('text', 'Unknown'),
            'lat': p['location']['latitude'],
            'lng': p['location']['longitude'],
            'rating': rating,
            'reviews': reviews,
            'specialty_match': specialty_match,
            'phone': phone,
            'maps_url': maps_url,
            'is_open': is_open 
        })

    if not valid_hospitals: return jsonify([])

    # Cap at 20 strictly for the Routes API safety limit
    valid_hospitals = valid_hospitals[:20]

    routes_url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    routes_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,condition"
    }

    destinations = [{"waypoint": {"location": {"latLng": {"latitude": h['lat'], "longitude": h['lng']}}}} for h in valid_hospitals]
    routes_payload = {
        "origins": [{"waypoint": {"location": {"latLng": {"latitude": user_lat, "longitude": user_lng}}}}],
        "destinations": destinations,
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    }

    try:
        matrix_response = requests.post(routes_url, json=routes_payload, headers=routes_headers).json()
    except Exception:
        return jsonify([])

    for route in matrix_response:
        dest_index = route.get('destinationIndex')
        duration_str = route.get('duration', '0s').replace('s', '')
        duration_sec = int(float(duration_str))
        
        if ambulance_mode: duration_sec = int(duration_sec / 1.4)
            
        valid_hospitals[dest_index]['duration_sec'] = duration_sec
        valid_hospitals[dest_index]['duration_text'] = f"{duration_sec // 60} mins"

    ranked_results = execute_mcdm_ranking(valid_hospitals, situation, category)
    return jsonify(ranked_results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)