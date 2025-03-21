import requests
import json
import os
from dotenv import load_dotenv
try:
    from colorama import init, Fore, Style
    # Initialize colorama for Windows support
    init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

# Load environment variables from .env file
load_dotenv()

# API endpoint
API_URL = "http://localhost:8000/api/v1"

# Check if running in a terminal that can use colors
USE_COLORS = os.isatty(1) and HAS_COLORAMA

# Color codes using colorama if available
class Colors:
    if USE_COLORS:
        HEADER = Fore.MAGENTA + Style.BRIGHT
        BLUE = Fore.BLUE
        GREEN = Fore.GREEN
        WARNING = Fore.YELLOW
        FAIL = Fore.RED
        RESET = Style.RESET_ALL
        BOLD = Style.BRIGHT
        UNDERLINE = '\033[4m'  # Colorama doesn't have underline, using ANSI
    else:
        HEADER = ''
        BLUE = ''
        GREEN = ''
        WARNING = ''
        FAIL = ''
        RESET = ''
        BOLD = ''
        UNDERLINE = ''

# Example prompt optimization request
request_data = {
    "user_prompt": "Explain quantum computing to a 10-year-old",
    "target_tasks": ["deduction"],
    "target_behaviors": ["step_by_step", "conciseness"],
    "target_model": "gpt-4",
    "domain": "education"
}

def optimize_prompt():
    """Send optimization request to the API"""
    print(f"{Colors.BLUE}Sending optimization request...{Colors.RESET}")
    
    response = requests.post(
        f"{API_URL}/optimize",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Optimized Prompt ==={Colors.RESET}\n")
        print(f"{Colors.GREEN}{result['full_prompt']}{Colors.RESET}")
        
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Rationale ==={Colors.RESET}\n")
        print(result["rationale"])
        
        print(f"\n{Colors.BOLD}Effectiveness Score: {Colors.GREEN}{result['effectiveness_score']:.2f}{Colors.RESET}\n")
        
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Component Structure ==={Colors.RESET}\n")
        for component in result["components"]:
            print(f"{Colors.BLUE}[{component['position']}]{Colors.RESET} {Colors.BOLD}{component['type']}{Colors.RESET}")
    else:
        print(f"{Colors.FAIL}Error: {response.status_code}{Colors.RESET}")
        print(response.text)

def analyze_prompt():
    """Send analysis request to the API"""
    print(f"{Colors.BLUE}Analyzing prompt...{Colors.RESET}")
    
    response = requests.post(
        f"{API_URL}/analyze",
        json={"text": request_data["user_prompt"]},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Prompt Analysis ==={Colors.RESET}\n")
        
        tasks = ', '.join(result['detected_tasks'])
        behaviors = ', '.join(result['detected_behaviors'])
        
        print(f"{Colors.BOLD}Detected Tasks:{Colors.RESET} {Colors.GREEN}{tasks}{Colors.RESET}")
        print(f"{Colors.BOLD}Detected Behaviors:{Colors.RESET} {Colors.GREEN}{behaviors}{Colors.RESET}")
    else:
        print(f"{Colors.FAIL}Error: {response.status_code}{Colors.RESET}")
        print(response.text)

def provide_feedback():
    """Send feedback to the API"""
    feedback_data = {
        "component_type": "instruction",
        "behavior_type": "precision",
        "effectiveness": 0.85
    }
    
    print(f"{Colors.BLUE}Sending feedback...{Colors.RESET}")
    
    response = requests.post(
        f"{API_URL}/feedback",
        json=feedback_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Feedback Result ==={Colors.RESET}\n")
        print(f"{Colors.GREEN}{result['message']}{Colors.RESET}")
    else:
        print(f"{Colors.FAIL}Error: {response.status_code}{Colors.RESET}")
        print(response.text)

def main():
    print(f"\n{Colors.HEADER}{Colors.BOLD}InferPrompt API Client{Colors.RESET}\n")
    print(f"{Colors.BOLD}1.{Colors.RESET} Optimize a prompt")
    print(f"{Colors.BOLD}2.{Colors.RESET} Analyze a prompt")
    print(f"{Colors.BOLD}3.{Colors.RESET} Provide feedback")
    print(f"{Colors.BOLD}4.{Colors.RESET} Exit")
    
    choice = input(f"\n{Colors.BLUE}Enter your choice (1-4):{Colors.RESET} ")
    
    if choice == "1":
        optimize_prompt()
    elif choice == "2":
        analyze_prompt()
    elif choice == "3":
        provide_feedback()
    elif choice == "4":
        print(f"{Colors.GREEN}Exiting...{Colors.RESET}")
        return
    else:
        print(f"{Colors.WARNING}Invalid choice. Please try again.{Colors.RESET}")
    
    input(f"\n{Colors.BLUE}Press Enter to continue...{Colors.RESET}")
    main()

if __name__ == "__main__":
    main()
