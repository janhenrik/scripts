#!/usr/bin/env python3
import requests
import json
import sys
import subprocess
from typing import List, Dict

def get_top_stories() -> List[Dict]:
    """Fetch top stories from HN API"""
    print("Loading stories...")
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()[:10]
    
    stories = []
    for story_id in story_ids:
        story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        story = story_response.json()
        if story and 'title' in story:
            stories.append(story)
    
    return sorted(stories, key=lambda x: x.get('score', 0), reverse=True)

def get_story_comments(story_id: str) -> str:
    """Fetch and extract comments for a story (limited to first 30 comments)"""
    response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
    story = response.json()
    
    comments = []
    comment_count = 0
    processed_ids = set()  # To avoid duplicate comments

    def fetch_comment_thread(comment_id, depth=0, max_depth=2):
        nonlocal comment_count
        if comment_count >= 30 or depth > max_depth or comment_id in processed_ids:
            return
        
        response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json")
        comment = response.json()
        
        if comment and comment.get('text') and comment.get('by'):
            comments.append(f"{comment['by']}: {comment['text']}")
            processed_ids.add(comment_id)
            comment_count += 1
            
            # Process some replies if available
            if 'kids' in comment:
                for kid_id in comment['kids'][:3]:  # Limit replies to top 3
                    fetch_comment_thread(kid_id, depth + 1, max_depth)

    if 'kids' in story:
        for comment_id in story['kids'][:10]:  # Get top 10 root comments
            fetch_comment_thread(comment_id)
    
    return "\n".join(comments)

def main():
    model = "o1-mini"
    if len(sys.argv) > 2 and sys.argv[1] == "-m":
        model = sys.argv[2]

    stories = get_top_stories()
    for i, story in enumerate(stories, 1):
        print(f"{i}. {story['title']} ({story.get('score', 0)} points)")
        print(f"{story.get('url', 'No URL - text post on HN')}")

    while True:
        try:
            selection = int(input("\nWhich story would you like to process? (1-10): "))
            if 1 <= selection <= len(stories):
                break
            print("Please enter a number between 1 and 10")
        except ValueError:
            print("Please enter a valid number")

    selected = stories[selection - 1]
    print(f"\nYou selected: {selected['title']} (ID: {selected['id']})")
    print("\nFetching comments...")

    comments = get_story_comments(selected['id'])
    print(f"\nProcessing {len(comments.split())} words from comments...")

    # Escape special characters in comments
    sanitized_comments = comments.replace('"', '\\"').replace("'", "\\'")
    
    # Stream the LLM response and save to file
    process = subprocess.Popen(
        ["llm", "-m", model, f"Analyze these Hacker News comments and provide a summary of the main discussion themes. Include relevant quotes with author attribution where appropriate: {sanitized_comments}."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    print("\nSummary (streaming):")
    # Stream stdout and collect for file
    all_output = []
    for line in process.stdout:
        print(line, end='', flush=True)
        all_output.append(line)
    
    # Check for any errors
    for line in process.stderr:
        print("Error:", line, end='', flush=True)
    
    # Save to file and show preview
    with open("/tmp/hn_summary.md", "w") as f:
        f.write("".join(all_output))
    
    # Show preview
    subprocess.run(["qlmanage", "-p", "/tmp/hn_summary.md"])

if __name__ == "__main__":
    main()