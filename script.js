let map, marker, autocomplete, markersArray = [];

const firstAidTips = {
    "Cardiac": "🫀 <b>FIRST AID (CARDIAC):</b> Have the patient sit down and rest. Loosen tight clothing. If they are prescribed nitroglycerin, help them take it. Chew and swallow an aspirin (unless allergic). If unconscious and not breathing, begin CPR immediately.",
    "Trauma": "🩸 <b>FIRST AID (TRAUMA):</b> Do not move the person unless they are in immediate danger. Apply firm, direct pressure to any bleeding with a clean cloth. Keep the person warm to prevent shock.",
    "Stroke": "🧠 <b>FIRST AID (STROKE):</b> Remember <b>F.A.S.T.</b> - Face drooping, Arm weakness, Speech difficulty, Time to call emergency. Note the exact time symptoms started. Do not give them anything to eat or drink.",
    "Maternity": "👶 <b>FIRST AID (MATERNITY):</b> Keep the mother calm and comfortable. Have her lie on her left side to improve blood flow to the baby. Time the contractions. Do not let her eat heavy food.",
    "General": "🚑 <b>FIRST AID (GENERAL):</b> Stay calm. Keep the patient comfortable and warm. Do not give them food or water unless instructed by a medical professional. Have any current medications ready to show doctors."
};

function initMap() {
    const initialPos = { lat: 12.9797, lng: 77.5912 };
    map = new google.maps.Map(document.getElementById("map"), {
        center: initialPos, zoom: 12, mapTypeControl: false
    });

    // 🔵 CURRENT LOCATION: Distinct Blue Circle
    marker = new google.maps.Marker({
        position: initialPos, map: map, draggable: true,
        animation: google.maps.Animation.DROP,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: '#4285F4',
            fillOpacity: 1,
            strokeColor: 'white',
            strokeWeight: 2,
            scale: 10
        }
    });

    const input = document.getElementById("location-input");
    autocomplete = new google.maps.places.Autocomplete(input, { componentRestrictions: { country: "in" } });
    autocomplete.bindTo("bounds", map);

    autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();
        if (!place.geometry) return;
        updateMapCenter(place.geometry.location.lat(), place.geometry.location.lng());
    });
}

function updateMapCenter(lat, lng) {
    const pos = { lat: lat, lng: lng };
    map.setCenter(pos);
    map.setZoom(14);
    marker.setPosition(pos);
}

document.getElementById('gps-btn').addEventListener('click', () => {
    if (navigator.geolocation) {
        document.getElementById('gps-btn').innerText = "Locating...";
        navigator.geolocation.getCurrentPosition(
            (position) => {
                updateMapCenter(position.coords.latitude, position.coords.longitude);
                document.getElementById('location-input').value = "Current GPS Location";
                document.getElementById('gps-btn').innerText = "📍 Locate Me";
            },
            (error) => {
                alert("GPS Denied. Please type your location.");
                document.getElementById('gps-btn').innerText = "📍 Locate Me";
            }
        );
    } else {
        alert("Geolocation not supported.");
    }
});

function clearMarkers() {
    markersArray.forEach(m => m.setMap(null));
    markersArray = [];
}

async function findHospitals() {
    const findBtn = document.getElementById('find-btn');
    findBtn.innerText = "Executing MCDM Algorithm...";
    clearMarkers();

    const selectedCategory = document.getElementById('emergency-category').value;
    const banner = document.getElementById('first-aid-banner');
    banner.innerHTML = firstAidTips[selectedCategory];
    banner.classList.add('active');

    const payload = {
        lat: marker.getPosition().lat(),
        lng: marker.getPosition().lng(),
        category: selectedCategory,
        situation: document.getElementById('situation-level').value,
        ambulance: document.getElementById('ambulance-mode').checked
    };

    try {
       const response = await fetch('https://hospital-recommendation-w438.onrender.com/rank_hospitals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const hospitals = await response.json();
        
        if (hospitals.error || hospitals.length === 0) {
            alert("No valid hospitals found nearby or API Error.");
            findBtn.innerText = "Execute MCDM Ranking";
            return;
        }

        const bounds = new google.maps.LatLngBounds();
        bounds.extend(marker.getPosition());

        hospitals.forEach((h, index) => {
            // THE FIX: Use hardcoded Hex codes for SVG drawing
            // 🔴 Rank 1 = Red (#FF0000) | 🟢 Ranks 2-5 = Green (#228B22)
            const markerColor = (index === 0) ? '#FF0000' : '#228B22';

            const hMarker = new google.maps.Marker({
                position: { lat: h.lat, lng: h.lng }, 
                map: map,
                icon: {
                    // This creates a circular bubble shape
                    path: "M 0,0 m -12,0 a 12,12 0 1,0 24,0 a 12,12 0 1,0 -24,0",
                    fillColor: markerColor,
                    fillOpacity: 1,
                    strokeColor: '#FFFFFF',
                    strokeWeight: 2,
                    scale: 1.2
                },
                label: {
                    text: (index + 1).toString(),
                    color: "white",
                    fontWeight: "bold",
                    fontSize: "14px"
                }
            });

            let statusBadge = (h.is_open === true) 
                ? '<span style="background-color: #4CAF50; color: white; padding: 4px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 5px;">🟢 Verified Open</span>'
                : '<span style="background-color: #9E9E9E; color: white; padding: 4px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 5px;">⚪ Hours Unknown</span>';

            const info = new google.maps.InfoWindow({
                content: `<div style="color:black; font-family:sans-serif; max-width: 260px;">
                            <h3 style="margin:0 0 5px 0;">
                                <a href="${h.maps_url}" target="_blank" style="color:${index === 0 ? '#d32f2f' : '#1976D2'}; text-decoration: none;">
                                    #${index + 1} ${h.name} ↗
                                </a>
                            </h3>
                            <div style="margin-bottom: 8px;">
                                <a href="tel:${h.phone}" style="background-color: #1976D2; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">
                                    📞 ${h.phone}
                                </a>
                                ${statusBadge}
                            </div>
                            <b>Suitability:</b> ${h.mcdm_score.toFixed(3)}<br>
                            ⏱ <b>Travel Time:</b> ${h.duration_text}<br>
                            ⭐ <b>Rating:</b> ${h.rating} (${h.reviews} revs)<br>
                            🏥 <b>Specialty Match:</b> ${h.specialty_match === 1 ? 'Yes' : 'General Fallback'}
                          </div>`
            });

            hMarker.addListener("click", () => info.open(map, hMarker));
            markersArray.push(hMarker);
            bounds.extend(hMarker.getPosition());
        });

        map.fitBounds(bounds);
        findBtn.innerText = "Execute MCDM Ranking";
    } catch (e) { 
        alert("Server connection failed. Is app.py running?"); 
        findBtn.innerText = "Execute MCDM Ranking"; 
    }
}

window.onload = () => { initMap(); document.getElementById('find-btn').onclick = findHospitals; };
