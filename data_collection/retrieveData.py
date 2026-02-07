import requests
import json
import os
from datetime import datetime, timedelta

# More specific endpoint for award spending data
ENDPOINT = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, "spending_data.json")

def get_existing_data():
    """Reads the existing data from the output file."""
    if not os.path.exists(OUTPUT_FILE):
        return []
    with open(OUTPUT_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    """Saves the data to the output file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def fetch_all_data():
    """
    Fetches all award data from the API.
    This is a simplified example and may need adjustment for very large datasets.
    """
    print("Performing a full data download...")
    all_results = []
    page = 1
    has_next_page = True

    payload = {
        "filters": {
            "time_period": [{"start_date": "2007-10-01", "end_date": datetime.now().strftime('%Y-%m-%d')}],
            "award_type_codes": ["A", "B", "C", "D"]
        },
        "fields": ["Award ID", "Recipient Name", "Start Date", "End Date", "Award Amount", "action_date"],
        "sort": "Award Amount",
        "order": "desc",
        "page": page,
        "limit": 100
    }

    while has_next_page:
        print(f"Fetching page {page}...")
        payload["page"] = page
        response = requests.post(ENDPOINT, json=payload)
        if response.status_code == 200:
            data = response.json()
            all_results.extend(data.get("results", []))
            has_next_page = data.get("page_metadata", {}).get("hasNext", False)
            page += 1
        else:
            print(f"Error fetching data: {response.status_code}")
            print(response.text)
            break
    
    save_data(all_results)
    print(f"Full data download complete. {len(all_results)} records saved to {OUTPUT_FILE}")

def update_data():
    """
    Fetches only new data based on the latest action_date in the existing data.
    """
    print("Performing an update...")
    existing_data = get_existing_data()
    if not existing_data:
        print("No existing data found. Performing a full download instead.")
        fetch_all_data()
        return

    latest_action_date_str = max(item.get('action_date', '1970-01-01T00:00:00') for item in existing_data)
    latest_action_date = datetime.fromisoformat(latest_action_date_str)
    
    # Start looking for new data from the day after the latest record
    start_date = (latest_action_date + timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    print(f"Fetching new data from {start_date} to {end_date}...")

    new_results = []
    page = 1
    has_next_page = True

    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"]
        },
        "fields": ["Award ID", "Recipient Name", "Start Date", "End Date", "Award Amount", "action_date"],
        "sort": "action_date",
        "order": "asc",
        "page": page,
        "limit": 100
    }

    while has_next_page:
        print(f"Fetching page {page}...")
        payload["page"] = page
        response = requests.post(ENDPOINT, json=payload)
        if response.status_code == 200:
            data = response.json()
            new_results.extend(data.get("results", []))
            has_next_page = data.get("page_metadata", {}).get("hasNext", False)
            page += 1
        else:
            print(f"Error fetching data: {response.status_code}")
            print(response.text)
            break

    if new_results:
        updated_data = existing_data + new_results
        save_data(updated_data)
        print(f"Update complete. {len(new_results)} new records added.")
    else:
        print("No new data found.")

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_FILE):
        fetch_all_data()
    else:
        update_data()