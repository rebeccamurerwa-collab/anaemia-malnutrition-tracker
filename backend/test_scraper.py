import requests 
from bs4 import BeautifulSoup 
url = "https://pib.gov.in/RssMain.aspx?ModId=6^&Lang=1^&Regid=3" 
resp = requests.get(url, timeout=20) 
soup = BeautifulSoup(resp.text, "xml") 
items = soup.find_all("item") 
print("Total items:", len(items)) 
for item in items[:5]: 
    print(item.find("title").text[:100]) 
    print(item.find("link").text) 
    print("---") 
