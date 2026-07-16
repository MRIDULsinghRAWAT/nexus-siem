import urllib.request
import json
import hashlib
import ipaddress

# Predefined locations for private/local simulator IPs to populate the threat map beautifully
MOCK_LOCATIONS = [
    {"country": "United States", "city": "New York", "lat": 40.7128, "lon": -74.0060},
    {"country": "United Kingdom", "city": "London", "lat": 51.5074, "lon": -0.1278},
    {"country": "Japan", "city": "Tokyo", "lat": 35.6762, "lon": 139.6503},
    {"country": "Germany", "city": "Frankfurt", "lat": 50.1109, "lon": 8.6821},
    {"country": "Australia", "city": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"country": "Brazil", "city": "São Paulo", "lat": -23.5505, "lon": -46.6333},
    {"country": "Singapore", "city": "Singapore", "lat": 1.3521, "lon": 103.8198},
    {"country": "India", "city": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"country": "South Africa", "city": "Cape Town", "lat": -33.9249, "lon": 18.4241},
    {"country": "Canada", "city": "Toronto", "lat": 43.6532, "lon": -79.3832}
]

def is_private_ip(ip_str):
    """Checks if an IP address is a private, loopback, or reserved range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local
    except ValueError:
        return True

def get_ip_location(ip_str):
    """
    Resolves an IP to a location dictionary containing country, city, lat, and lon.
    Queries ip-api.com for public IPs, with a deterministic mock fallback for private IPs.
    """
    if not ip_str or ip_str == "-":
        ip_str = "127.0.0.1"

    if is_private_ip(ip_str):
        # Deterministically map internal IPs using MD5 hash to one of our global mock locations
        h = int(hashlib.md5(ip_str.encode('utf-8')).hexdigest(), 16)
        loc = MOCK_LOCATIONS[h % len(MOCK_LOCATIONS)]
        return {
            "country": loc["country"],
            "city": loc["city"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "type": "private"
        }
    
    # Query free GeoIP public API for public IPs
    try:
        url = f"http://ip-api.com/json/{ip_str}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                return {
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "lat": float(data.get("lat", 0.0)),
                    "lon": float(data.get("lon", 0.0)),
                    "type": "public"
                }
    except Exception as e:
        print(f"[!] GeoIP API lookup failed for {ip_str}, falling back to mock: {e}")
        
    # Fallback in case of API timeout, rate limits, or network errors
    h = int(hashlib.md5(ip_str.encode('utf-8')).hexdigest(), 16)
    loc = MOCK_LOCATIONS[h % len(MOCK_LOCATIONS)]
    return {
        "country": loc["country"],
        "city": loc["city"],
        "lat": loc["lat"],
        "lon": loc["lon"],
        "type": "fallback"
    }
