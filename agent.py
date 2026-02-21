import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI
import json
import time

# Set OpenAI API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print(api_key=os.getenv('OPENAI_API_KEY'))
if not client.api_key:
    print("Error: Set OPENAI_API_KEY environment variable.")
    exit(1)

def get_llm_suggestion(html, current_url):
    prompt = f"""
Analyze this HTML page from {current_url}. What is this page (e.g., homepage, user list)?
Suggest ONE next action to explore the app. Examples:
- "click link /users/" (if there's a link to /users/)
- "fill form with name: Test User, email: test@example.com and submit" (if there's a form)
- "click link /users/create/" (if there's a create link)
Be concise and specific. If no actions, say "stop".
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use gpt-4 for better results if available
            messages=[{"role": "user", "content": prompt + "\n\nHTML:\n" + html[:3000]}],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM error: {e}")
        return "stop"

def perform_action(driver, suggestion, collection):
    suggestion = suggestion.lower()
    if "click link" in suggestion:
        # Extract link text or URL
        if "/" in suggestion:
            link_url = suggestion.split("/")[-1].strip().replace('"', '')
            try:
                link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '{link_url}')]"))
                )
                link.click()
                time.sleep(2)  # Wait for load
                # Record as GET request
                collection['item'].append({
                    'name': f'Navigate to {link_url}',
                    'request': {'method': 'GET', 'url': driver.current_url}
                })
                return True
            except:
                print(f"Could not click link: {link_url}")
    elif "fill form" in suggestion and "submit" in suggestion:
        # Simple form filling (assumes standard fields)
        try:
            name_field = driver.find_element(By.NAME, 'name')
            name_field.send_keys('Test User')
            email_field = driver.find_element(By.NAME, 'email')
            email_field.send_keys('test@example.com')
            submit_button = driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
            submit_button.click()
            time.sleep(2)
            # Record as POST request (simplified)
            collection['item'].append({
                'name': 'Submit Form',
                'request': {
                    'method': 'POST',
                    'url': driver.current_url,
                    'body': {
                        'mode': 'urlencoded',
                        'urlencoded': [
                            {'key': 'name', 'value': 'Test User'},
                            {'key': 'email', 'value': 'test@example.com'}
                        ]
                    }
                }
            })
            return True
        except:
            print("Could not fill/submit form")
    return False

def main():
    # allow CLI arguments so that this can be scripted or integrated into other tooling
    import argparse

    parser = argparse.ArgumentParser(
        description="Crawl a web application and build a Postman collection of the visited APIs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("base_url", nargs="?",
                        help="Base URL of the application (e.g. http://127.0.0.1:8000)")
    parser.add_argument("-o", "--output",
                        help="Where to save the collection JSON file",
                        default=os.path.join("data", "output", "collection.json"))
    parser.add_argument("-m", "--max-pages", type=int,
                        help="Maximum number of pages to explore",
                        default=10)

    args = parser.parse_args()

    if args.base_url:
        url = args.base_url.rstrip('/')
    else:
        url = input("Enter the base URL of the application (e.g., http://127.0.0.1:8000): ").strip()

    output_path = args.output
    max_pages = args.max_pages

    # ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    
    # Selenium setup
    options = Options()
    options.add_argument("--headless")  # Run without UI
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    collection = {
        'info': {'name': 'LLM-Explored APIs', 'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
        'item': []
    }
    
    visited = set()
    to_visit = [url]
    max_pages = 10  # Limit exploration
    
    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)
        
        print(f"Visiting: {current_url}")
        driver.get(current_url)
        html = driver.page_source
        
        suggestion = get_llm_suggestion(html, current_url)
        print(f"Suggestion: {suggestion}")
        
        if "stop" in suggestion.lower():
            break
        
        if perform_action(driver, suggestion, collection):
            # Add new URL to visit if changed
            new_url = driver.current_url
            if new_url not in visited and new_url not in to_visit:
                to_visit.append(new_url)
    
    driver.quit()
    
    # Save collection
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2)
    if collection['item']:
        print(f"Collection saved to {output_path} with {len(collection['item'])} requests.")
    else:
        print(f"No requests captured. Empty collection saved to {output_path}.")

if __name__ == "__main__":
    main()