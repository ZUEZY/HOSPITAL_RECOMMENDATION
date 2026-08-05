CareMCDM

CareMCDM is a real-time emergency hospital recommendation system developed to assist users in identifying the most suitable hospital based on their medical condition, location, and urgency level. The system combines Google Maps services with a Multi-Criteria Decision Making (MCDM) framework to recommend hospitals that best match the user's requirements.

Features

- Real-time hospital search using Google Places API
- Travel time estimation using Google Routes API
- Emergency severity-based recommendation (Nearest, Level 1, Level 2, Level 3)
- Medical specialty matching
- Automatic filtering of irrelevant or closed facilities
- Shannon Entropy-based objective weighting
- Context-aware heuristic weighting
- Hybrid MCDM ranking engine
- Interactive Google Maps interface
- Displays the top 5 recommended hospitals

Technology Stack

Backend
- Python
- Flask
- Google Places API
- Google Routes API

Frontend
- HTML
- CSS
- JavaScript
- Google Maps JavaScript API

Methodology

1. Obtain the user's current location.
2. Retrieve nearby hospitals using Google Places API.
3. Filter duplicate, irrelevant, and unavailable hospitals.
4. Calculate real-time travel duration using Google Routes API.
5. Build a decision matrix using travel time, specialty, and hospital rating.
6. Compute objective criterion weights using Shannon Entropy.
7. Apply emergency-specific heuristic weighting.
8. Generate hybrid weights and rank hospitals using a weighted sum model.
9. Display the top recommendations on the map.

Project Structure

```
CareMCDM/
│
├── app.py
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── requirements.txt
└── README.md
```

Future Improvements

- Live ICU and bed availability
- Emergency department waiting time
- Ambulance tracking
- Electronic Health Record integration
- Predictive analytics using machine learning

Research

This project forms the implementation of the IEEE conference paper:

"A Context-Adaptive MCDM Framework Utilising Shannon Entropy for Real-Time Emergency Hospital Routing (CareMCDM)"

License

This project is intended for academic and research purposes.
