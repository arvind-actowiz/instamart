import requests
import json
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Any
import time

# Constants
ALLOWED_CATEGORIES = [
    'grocery & kitchen',
    'snacks & drinks',
    'beauty & wellness',
    'household & lifestyle'
]

BASE_API_URL = 'https://www.swiggy.com/api/instamart/home/v2'
CATEGORY_LISTING_URL = 'https://www.swiggy.com/api/instamart/category-listing'

HOME_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'if-none-match': 'W/"a589-ZCzqPVdWbYRUOHpIEDw8vGp6ICM"',
    'matcher': 'ccc8b8ebegegdgcd9ddfdcd',
    'priority': 'u=1, i',
    'referer': 'https://www.swiggy.com/instamart',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'x-build-version': '2.273.0',
}

CATEGORY_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'if-none-match': 'W/"1d5dd-f9kriMioFfFJlLB25K7MNTsyQMs"',
    'matcher': '9d9ge8ebeggd9ffddcg9fa7',
    'priority': 'u=1, i',
    'referer': 'https://www.swiggy.com/stores/instamart/category-listing',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'x-build-version': '2.273.0',
}

BASE_PARAMS = {
    'layoutId': '2671',
    'storeId': '1383570',
    'primaryStoreId': '1383570',
    'secondaryStoreId': '',
    'clientId': 'INSTAMART-APP',
}

def make_home_request(offset: int, session: requests.Session) -> Dict[str, Any]:
    """Make an API request to Swiggy Instamart home with the given offset."""
    params = BASE_PARAMS.copy()
    params['offset'] = str(offset)
    
    session.cookies.clear()
    response = session.get(
        BASE_API_URL,
        params=params,
        headers=HOME_HEADERS
    )
    response.raise_for_status()
    return response.json()

def make_category_request(category_name: str, category_taxonomy: str, session: requests.Session) -> Dict[str, Any]:
    """Make an API request to fetch category details."""
    params = {
        'categoryName': category_name,
        'storeId': '1383570',
        'offset': '0',
        'filterName': '',
        'primaryStoreId': '1383570',
        'secondaryStoreId': '',
        'taxonomyType': category_taxonomy,
    }
    
    session.cookies.clear()
    response = session.get(
        CATEGORY_LISTING_URL,
        params=params,
        headers=CATEGORY_HEADERS
    )
    response.raise_for_status()
    return response.json()

def save_to_json(data: Any, filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, 'w') as file:
        json.dump(data, file, indent=2)

def extract_taxonomy_types(link: str) -> str:
    """Extract taxonomy type from a Swiggy URL."""
    url = link.replace("swiggy://", "https://")
    query = urlparse(url).query
    params = parse_qs(query)
    return params.get("taxonomyType", [""])[0]

def parse_home_categories(response_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse categories data from home API response."""
    categories = []
    for outer_card in response_json.get('data', {}).get('cards', []):
        try:
            category_name = outer_card['card']['card']['header']['title']
            normalized_name = category_name.lower().strip()

            if normalized_name not in ALLOWED_CATEGORIES:
                print(f"Skipping: {normalized_name}")
                continue
        
            print(f"Parsing: {normalized_name}")
            
            subcategories = outer_card['card']['card']['gridElements']['infoWithStyle']['info']
            print(f"Total subcategories: {len(subcategories)}")

            categories.extend(
                {
                    "id": subcat['id'],
                    "name": subcat['description'],
                    "link": subcat['action']['link'],
                    "taxonomy_type": extract_taxonomy_types(subcat['action']['link'])
                }
                for subcat in subcategories
            )
            
        except (KeyError, TypeError) as e:
            print(f"Error parsing category: {e}")
            continue
    
    return categories

def parse_category_details(response_json: Dict[str, Any], parent_category: str, taxonomy_type: str) -> List[Dict[str, Any]]:
    """Parse subcategories from category listing API response."""
    subcategories = []
    for subcat in response_json['data']['filters']:
        subcategories.append({
            "parentCategory": parent_category,
            "name": subcat['name'],
            "id": subcat['id'],
            "productCount": subcat['productCount'],
            "taxonomyType": taxonomy_type
        })
    return subcategories

def get_next_offset(response_json: Dict[str, Any]) -> Optional[int]:
    """Get the next offset for pagination."""
    try:
        return int(response_json['data']['pageOffset']['nextOffset'])
    except (KeyError, TypeError, ValueError):
        return None

def scrape_home_categories() -> List[Dict[str, Any]]:
    """Scrape all categories from the home page."""
    session = requests.Session()
    offset = 1
    parsed_categories = []

    while True:
        try:
            response_json = make_home_request(offset, session)
            categories = parse_home_categories(response_json)
            parsed_categories.extend(categories)
            
            offset = get_next_offset(response_json)
            if not offset:
                break
        
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Failed to decode response: {e}")
            break
    
    return parsed_categories

def scrape_category_details(categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scrape details for all categories."""
    session = requests.Session()
    all_subcategories = []
    
    for category in categories:
        try:
            print(f"Processing category: {category['name']}")
            response_json = make_category_request(
                category['name'], 
                category['taxonomy_type'], 
                session
            )

            subcategories = parse_category_details(
                response_json,
                category['name'],
                category['taxonomy_type']
            )

            all_subcategories.extend(subcategories)
            print(f"Found {len(subcategories)} subcategories for {category['name']}")

            time.sleep(1)  # Be polite with delays between requests
        
        except Exception as e:
            print(f"Error processing category '{category['name']}': {e}")
    
    return all_subcategories

def main():
    """Main execution flow."""
    # Step 1: Scrape main categories from home page
    print("Starting home categories scrape...")
    categories = scrape_home_categories()
    print(f"\nFound {len(categories)} categories")

    # Step 2: Scrape subcategory details for each category
    print("\nStarting category details scrape...")
    combined_data = scrape_category_details(categories)
    save_to_json(combined_data, 'output/categories.json')
    print(f"\nSuccess! Saved {len(combined_data)} total subcategories")

if __name__ == '__main__':
    main()