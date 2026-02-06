import requests

ENDPOINT = "https://api.usaspending.gov/api/v2/spending/"

results = requests.get(ENDPOINT)
print(results)
