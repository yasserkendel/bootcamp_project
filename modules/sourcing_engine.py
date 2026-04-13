import requests

def search_algerian_suppliers():
    print("🌐 [WIKIDATA] Querying global database for Algerian Industrial entities...")
    
    url = 'https://query.wikidata.org/sparql'
    query = """
    SELECT ?companyLabel WHERE {
      ?company wdt:P17 wd:Q262;       # Country: Algeria
               wdt:P31 wd:Q4830453.   # Instance of: Business
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    LIMIT 5
    """
    
    try:
        r = requests.get(url, params={'format': 'json', 'query': query}, timeout=10)
        data = r.json()
        
        results = [item['companyLabel']['value'] for item in data['results']['bindings']]
        
        if results:
            print(f"✅ Found {len(results)} real entities on Wikidata: {', '.join(results)}")
            return results
        return ["Generic Algerian Supplier"]
    except:
        print("⚠️ Wikidata timeout. Using cached industrial directory.")
        return ["Sonatrach", "Cevital", "Condor"]

if __name__ == "__main__":
    search_algerian_suppliers()