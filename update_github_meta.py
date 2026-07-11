import os
import requests

def update_repo(repo_name, description, topics):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.")
        return

    # Assuming repos are owned by the authenticated user
    # If they are under an organization, replace this logic
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # First get username
    user_resp = requests.get("https://api.github.com/user", headers=headers)
    if user_resp.status_code != 200:
        print(f"Failed to fetch user data: {user_resp.status_code}")
        return
        
    username = user_resp.json().get("login")
    if not username:
        print("Failed to get username from token.")
        return

    url = f"https://api.github.com/repos/{username}/{repo_name}"
    
    # Update description
    data = {"description": description}
    resp = requests.patch(url, headers=headers, json=data)
    if resp.status_code == 200:
        print(f"[{repo_name}] Successfully updated description.")
    else:
        print(f"[{repo_name}] Failed to update description: {resp.text}")

    # Update topics
    topics_url = f"{url}/topics"
    topics_data = {"names": topics}
    resp_topics = requests.put(topics_url, headers=headers, json=topics_data)
    if resp_topics.status_code == 200:
        print(f"[{repo_name}] Successfully updated topics.")
    else:
        print(f"[{repo_name}] Failed to update topics: {resp_topics.text}")

if __name__ == "__main__":
    repos = [
        {
            "name": "eval-harness",
            "desc": "A production-style eval harness that catches regressions in LLM agents by running a golden test suite against them.",
            "topics": ["llm", "evaluation", "regression-testing", "agents", "python"]
        },
        {
            "name": "autonomous-research-agent",
            "desc": "An autonomous research agent utilizing tool calling, RAG, and memory for executing deep research.",
            "topics": ["llm", "agents", "research", "langchain-alternative", "rag"]
        },
        {
            "name": "Cerebro-API",
            "desc": "The central nervous system for autonomous agents, providing RESTful endpoints for agent interactions.",
            "topics": ["llm", "api", "fastapi", "agents", "backend"]
        }
    ]

    print("Updating GitHub Repository Metadata...")
    for repo in repos:
        update_repo(repo["name"], repo["desc"], repo["topics"])
