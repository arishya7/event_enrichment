try:
    from transformers import pipeline
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    classifier = None
    print(classifier)

# Define categories
CATEGORIES = [
    "indoor playground",
    "outdoor playground",
    "kids attractions",
    "malls",
    "kids dining"
]

CATEGORY_HINTS = {
    "indoor playground": [
        "indoor play", "soft play", "ball pit", "indoor playground", "indoor play area", "indoor play space",
        "playground", "play area", "play space", "play zone", "kids play", "children play", "toddler play",
        "lego", "legoland", "trampoline", "trampoline park", "jumping", "bounce", "bouncy castle",
        "climbing", "climbing frame", "play structure", "play equipment", "playground equipment",
        "indoor activities", "indoor fun", "play centre", "play center", "fun zone", "activity centre",
        "soft play area", "ball pool", "playroom", "play room", "kids zone", "children zone"
    ],
    "outdoor playground": [
        "park", "outdoor playground", "outdoor play", "outdoor play area", "outdoor play space",
        "playground", "play park", "adventure playground", "nature playground", "community playground",
        "slide", "swing", "swings", "seesaw", "sandbox", "sand pit", "sand play", "water play",
        "splash pad", "water park", "splash park", "garden play", "outdoor activities", "outdoor fun",
        "playground equipment", "play structure", "climbing frame", "outdoor gym", "fitness park",
        "skate park", "bike park", "outdoor sports", "sports park", "recreation park", "neighborhood", 
        "neighbourhood", "shaded", "inclusive playground"
    ],
    "kids attractions": [
        "zoo", "zoological", "wildlife park", "safari", "aquarium", "theme park", "amusement park",
        "museum", "science centre", "science center", "science museum", "art museum", "art gallery",
        "adventure", "adventure park", "adventure centre", "escape room", "escape game", "carnival",
        "art workshop", "exhibition", "exhibit", "show", "performance", "theatre", "theater",
        "attraction", "tourist attraction", "family attraction", "kids attraction", "children attraction",
         "educational", "learning centre", "discovery centre", "planetarium",
        "botanical garden", "garden", "nature reserve", "heritage", "cultural centre", "cultural center",
        "festival", "fair", "event", "showcase", "display", "demonstration", "nature", "farm", "experience"
    ],
    "malls": [
        "mall", "shopping mall", "shopping centre", "shopping center", "shopping complex", "shopping plaza",
        "plaza", "retail", "retail centre", "retail center", "department store", "supermarket",
        "retail park", "outlet", "outlet mall", "factory outlet", "shopping hub", "retail hub",
        "shopping arcade", "shopping precinct", "retail precinct", "shopping area", "retail area", "mascot", 
        "meet and greet", "pop-up", "mall show", "mall event"
    ],
    "kids dining": [
        "restaurant", "restaurants", "cafe", "café", "coffee shop", "coffee house", "breakfast",
        "brunch", "dining", "dine", "food", "eatery", "eateries", "bistro", "diner", "food court",
        "kids menu", "children menu", "family menu", "family-friendly", "family friendly", "kid-friendly",
        "kid friendly", "child-friendly", "child friendly", "buffet", "all-you-can-eat", "all you can eat",
        "baby chair", "high chair", "highchair", "high tea", "afternoon tea", "kids dining",
        "meal", "meals", "eating", "menu", "lunch", "dinner", "foodie", "culinary",
        "cuisine", "food establishment", "food outlet", "food place", "dining establishment",
        "family restaurant", "casual dining", "fast food", "quick service", "food service",
        "catering", "catered", "food and beverage", "f&b", "food & beverage", "kids dine free", 
        "stroller parking", "play area"
    ]

}

# Minimum confidence threshold - increased to filter out borderline cases like "charted race"
RELEVANCE_THRESHOLD = 0.60


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split()).strip()


# Exclusion patterns that should automatically mark events as irrelevant
EXCLUSION_KEYWORDS = [
    'tuition', 'enrichment class', 'enrichment program', 'regular class',
    'trial class', 'open house', 'openhouse', 'preschool', 'primary school',
    'secondary school', 'university', 'baby fair', 'maternity fair',
    'maternity expo', 'lgbtq', 'consultation', 'regular weekly', 'ongoing class',
    'course enrollment', 'university application', 'school enrollment'
]

def check_exclusion_keywords(event: dict) -> bool:
    """Check if event should be excluded based on exclusion keywords.
    
    Returns True if event should be excluded (i.e., matches exclusion patterns).
    """
    text_parts = []
    for field in ['title', 'description', 'blurb', 'venue_name', 'organiser']:
        if event.get(field):
            text_parts.append(str(event[field]).lower())
    
    combined_text = " ".join(text_parts)
    
    # Check for exclusion keywords
    for keyword in EXCLUSION_KEYWORDS:
        if keyword.lower() in combined_text:
            return True
    
    return False


def classify_content(event):
    # FIRST: Check exclusion keywords - if matches, immediately return irrelevant
    if check_exclusion_keywords(event):
        return {
            "category": "irrelevant",
            "confidence": 0.0,
            "is_relevant": False,
            "scores_ranked": {},
            "raw_text": None,
            "excluded_by": "exclusion_keywords"
        }
    
    # Fallback if model not available
    if not CLASSIFIER_AVAILABLE:
        return {
            "category": None,
            "confidence": 0.0,
            "is_relevant": False,
            "scores_ranked": {},
            "raw_text": None
        }

    text_parts = []
    for field, label in [("title", "Title"), ("description", "Description"), ("venue_name", "Venue")]:
        if event.get(field):
            # Skip generic fallback venue names from classification (they don't help)
            if field == "venue_name" and event.get('_venue_name_is_fallback'):
                continue  # Don't include generic "Various Locations" in classification text
            text_parts.append(f"{label}: {event[field]}")

    # Combine and clean text
    raw_text = normalize_text(" ".join(text_parts))

    # If insufficient text, mark irrelevant
    if not raw_text or len(raw_text.split()) < 3:  # edge case: too little content
        return {
            "category": "irrelevant",
            "confidence": 0.0,
            "is_relevant": False,
            "scores_ranked": {},
            "raw_text": raw_text
        }

    try:
        result = classifier(raw_text, CATEGORIES, multi_label=False)

        # Extract top prediction
        top_category = result["labels"][0]
        top_score = result["scores"][0]

        # Sort scores by confidence
        scores_ranked = {
            label: round(score, 4)
            for label, score in sorted(
                zip(result["labels"], result["scores"]),
                key=lambda x: x[1],
                reverse=True
            )
        }
        
        # Apply keyword hints boost - stronger boost when keywords match
        for cat, keywords in CATEGORY_HINTS.items():
            if any(kw in raw_text.lower() for kw in keywords):
                current_score = scores_ranked.get(cat, 0)
                # Count how many keywords match (more matches = stronger signal)
                matching_keywords = sum(1 for kw in keywords if kw in raw_text.lower())
                
                if current_score < 0.7:
                    # Boost based on number of matching keywords
                    if matching_keywords >= 3:
                        # Strong signal - multiple keywords match
                        boost = 0.25
                        max_score = 0.90
                    elif matching_keywords >= 2:
                        # Moderate signal - 2 keywords match
                        boost = 0.20
                        max_score = 0.85
                    else:
                        # Single keyword match
                        boost = 0.15
                        max_score = 0.80
                    
                    scores_ranked[cat] = min(max_score, current_score + boost)

        # Determine relevance - use boosted score if available, otherwise use original top_score
        # Check if top category got boosted
        boosted_top_score = scores_ranked.get(top_category, top_score)
        is_relevant = boosted_top_score >= RELEVANCE_THRESHOLD
        
        # Update top_category if a different category now has highest boosted score
        if scores_ranked:
            best_category = max(scores_ranked.items(), key=lambda x: x[1])[0]
            best_score = scores_ranked[best_category]
            if best_score > boosted_top_score:
                top_category = best_category
                boosted_top_score = best_score
                is_relevant = boosted_top_score >= RELEVANCE_THRESHOLD
        print(f"Scores ranked: {scores_ranked}")

        return {
            "category": top_category if is_relevant else "irrelevant",
            "confidence": round(boosted_top_score, 4),  # Use boosted score for confidence
            "is_relevant": is_relevant,
            "scores_ranked": scores_ranked,
            "raw_text": raw_text
        }

    except Exception as e:
        return {
            "category": "irrelevant",
            "confidence": 0.0,
            "is_relevant": False,
            "scores_ranked": {},
            "raw_text": raw_text,
            "error": str(e)
        }

