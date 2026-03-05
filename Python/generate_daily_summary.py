#!/usr/bin/env python3
"""
Daily Commit Summary Generator
Extracts today's commits from the dev branch and generates a focused daily summary
"""

import subprocess
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import re

# Configuration
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_PATH = SCRIPT_DIR / "TudoNum-WebApp-Dev"
BRANCH = "dev"
# Write files to the repo directory (within workspace)
OUTPUT_FILE = REPO_PATH / "daily_commits.json"
SUMMARY_FILE_MD = REPO_PATH / "daily_summary.md"
SUMMARY_FILE_RTF = REPO_PATH / "daily_summary.rtf"
SUMMARY_FILE_TXT = REPO_PATH / "daily_summary.txt"


def run_git_command(args: List[str], repo_path: Path = REPO_PATH) -> str:
    """Run a git command and return the output"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {' '.join(args)}")
        print(f"Error: {e.stderr}")
        return ""


def get_today_commits() -> List[Dict]:
    """Get all commits from today on the dev branch"""
    # Get today's date range
    today = datetime.now()
    start_date = today.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d 00:00:00")
    
    # Use a separator that's unlikely to appear in commit messages
    separator = "|||COMMIT_SEPARATOR|||"
    
    # Format for git log with separator between commits
    format_str = (
        f"%H{separator}%an{separator}%ae{separator}%ad{separator}%s{separator}%b{separator}END_COMMIT"
    )
    
    cmd = [
        "log",
        "dev",
        f"--pretty=format:{format_str}",
        "--date=iso",
        f"--since={start_date}",
        "--no-merges",
        "--all"
    ]
    
    output = run_git_command(cmd)
    
    commits = []
    if output:
        # Split by commit separator
        commit_blocks = output.split("END_COMMIT")
        
        for block in commit_blocks:
            block = block.strip()
            if not block:
                continue
            
            # Split the block by separator
            parts = block.split(separator)
            if len(parts) >= 6:
                commit = {
                    "hash": parts[0].strip(),
                    "author": parts[1].strip(),
                    "email": parts[2].strip(),
                    "date": parts[3].strip(),
                    "subject": parts[4].strip(),
                    "body": parts[5].strip() if len(parts) > 5 else "",
                    "full_message": (parts[4].strip() + "\n" + parts[5].strip()).strip() if len(parts) > 5 and parts[5].strip() else parts[4].strip()
                }
                commits.append(commit)
    
    return commits


def save_commits_to_file(commits: List[Dict]):
    """Save commits to JSON file"""
    data = {
        "date": datetime.now().isoformat(),
        "branch": BRANCH,
        "total_commits": len(commits),
        "commits": commits
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(commits)} commits to {OUTPUT_FILE}")


def extract_functionality_keywords(message: str) -> List[str]:
    """Extract functionality-related keywords from commit message"""
    keywords = []
    message_lower = message.lower()
    
    # Feature indicators
    feature_patterns = [
        r"add(?:ed|ing)?\s+(\w+(?:\s+\w+){0,3})",
        r"implement(?:ed|ing)?\s+(\w+(?:\s+\w+){0,3})",
        r"create(?:d|ing)?\s+(\w+(?:\s+\w+){0,3})",
        r"new\s+(\w+(?:\s+\w+){0,3})",
        r"feature[:\s]+(\w+(?:\s+\w+){0,3})",
    ]
    
    for pattern in feature_patterns:
        matches = re.findall(pattern, message_lower)
        keywords.extend(matches)
    
    return list(set(keywords))


def extract_bug_keywords(message: str) -> List[str]:
    """Extract bug-related keywords from commit message"""
    keywords = []
    message_lower = message.lower()
    
    bug_indicators = [
        r"fix(?:ed|ing)?\s+(\w+(?:\s+\w+){0,3})",
        r"bug[:\s]+(\w+(?:\s+\w+){0,3})",
        r"issue[:\s]+(\w+(?:\s+\w+){0,3})",
        r"resolve(?:d|ing)?\s+(\w+(?:\s+\w+){0,3})",
        r"error[:\s]+(\w+(?:\s+\w+){0,3})",
        r"correct(?:ed|ing)?\s+(\w+(?:\s+\w+){0,3})",
    ]
    
    for pattern in bug_indicators:
        matches = re.findall(pattern, message_lower)
        keywords.extend(matches)
    
    return list(set(keywords))


def categorize_commits(commits: List[Dict]) -> Dict:
    """Categorize commits by type"""
    categories = {
        "features": [],
        "bug_fixes": [],
        "improvements": [],
        "refactoring": [],
        "other": []
    }
    
    for commit in commits:
        message = commit["full_message"].lower()
        subject = commit["subject"].lower()
        
        # More precise categorization
        # Bug fixes: explicitly mentions fix, bug, issue, error, resolve, correct, guard
        if any(word in subject for word in ["fix", "bug", "issue", "error", "resolve", "correct", "guard"]):
            categories["bug_fixes"].append(commit)
        # Features: new functionality (dispute, payment confirmation, extension cancellation, currency conversion)
        elif any(word in subject for word in ["add", "new", "implement", "create", "feature", "dispute", "confirmation", "cancellation", "currency conversion"]):
            # Currency conversion and payment features should be features, not bugs
            if any(word in subject for word in ["currency", "conversion", "payment"]):
                categories["features"].append(commit)
            elif "add" in subject or "new" in subject or "implement" in subject:
                categories["features"].append(commit)
            else:
                categories["improvements"].append(commit)
        # Improvements: enhance, improve, refine, simplify (but not new features)
        elif any(word in subject for word in ["improve", "enhance", "optimize", "upgrade", "refine", "simplify"]):
            categories["improvements"].append(commit)
        # Refactoring: code structure changes
        elif any(word in subject for word in ["refactor", "restructure", "reorganize"]):
            categories["refactoring"].append(commit)
        # Updates that are more like improvements
        elif "update" in subject:
            categories["improvements"].append(commit)
        # Remove/cleanup are usually improvements unless they're just cleanup
        elif any(word in subject for word in ["remove", "cleanup", "clean up"]):
            if len(subject.split()) < 5:  # Simple cleanup
                categories["other"].append(commit)
            else:
                categories["improvements"].append(commit)
        else:
            categories["other"].append(commit)
    
    return categories


def clean_description(text: str) -> str:
    """Clean commit description to remove technical jargon and focus on functionality"""
    # Remove technical implementation details
    text = re.sub(r'\b(adds|added|introduces|implements|add)\s+(API\s+)?(route|endpoint|hook|method|function|component)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(React\s+)?hook[s]?\s+(use\w+)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bAPI\s+(route|endpoint|method)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(UI\s+)?component[s]?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(schema|Zod schema|schemas)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(Redux|state management)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(prop[s]?|props)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(type safety|types?)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(refactor|refactored|refactoring)\b', 'improved', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(and|also)\s+(adds?|introduces?|implements?|includes?)\b', 'and', text, flags=re.IGNORECASE)
    
    # Remove hook names and technical identifiers
    text = re.sub(r'\buse\w+\s+(hook)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(including|includes?)\s+use\w+[,\s]*', '', text, flags=re.IGNORECASE)
    
    # Remove phrases that don't add value
    text = re.sub(r'\b(updates?|updated)\s+(to|the)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(and|,)\s+(updates?|updated)\s+', ' and ', text, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and commas
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r',\s*,+', ',', text)
    text = text.strip()
    
    # Remove leading/trailing commas and extra punctuation
    text = re.sub(r'^[,\s]+', '', text)
    text = re.sub(r'[,\s]+$', '', text)
    text = re.sub(r'^\s*and\s+', '', text, flags=re.IGNORECASE)
    
    # Fix double spaces after periods
    text = re.sub(r'\.\s{2,}', '. ', text)
    
    return text


def extract_functionality_description(commit: Dict) -> str:
    """Extract a clean, functionality-focused description from commit"""
    subject = commit["subject"].strip()
    body = commit["body"].strip() if commit.get("body") else ""
    
    # Extract natural description from subject
    subject_lower = subject.lower()
    
    # Create a natural description from the subject
    # Remove action words and make it more descriptive
    action_replacements = {
        'add': '',
        'adds': '',
        'added': '',
        'fix': 'Fixed issue with',
        'fixes': 'Fixed issue with',
        'fixed': 'Fixed issue with',
        'refactor': 'Improved',
        'refactored': 'Improved',
        'implement': 'Implemented',
        'implements': 'Implemented',
        'implemented': 'Implemented',
        'create': 'Created',
        'creates': 'Created',
        'created': 'Created',
        'update': 'Updated',
        'updates': 'Updated',
        'updated': 'Updated',
        'remove': 'Removed',
        'removes': 'Removed',
        'removed': 'Removed',
        'improve': 'Improved',
        'improves': 'Improved',
        'improved': 'Improved',
        'simplify': 'Simplified',
        'simplifies': 'Simplified',
        'simplified': 'Simplified',
    }
    
    # Try to find and replace action word
    subject_clean = subject
    for action, replacement in action_replacements.items():
        if subject_lower.startswith(action + ' '):
            remaining = subject[len(action):].strip()
            if remaining:
                # Capitalize first letter
                remaining = remaining[0].upper() + remaining[1:] if len(remaining) > 1 else remaining.upper()
                if replacement:
                    subject_clean = f"{replacement} {remaining}"
                else:
                    # For "Add", make it more natural
                    if 'for' in remaining.lower():
                        subject_clean = f"Enabled {remaining}"
                    else:
                        subject_clean = f"Enabled {remaining}"
            break
    
    # Clean technical terms but preserve meaning
    subject_clean = clean_description(subject_clean)
    
    # Fix common issues
    subject_clean = re.sub(r'\s+for\s+to\s+', ' for ', subject_clean, flags=re.IGNORECASE)
    subject_clean = re.sub(r'\s+for\s+$', '', subject_clean)
    
    # If body exists, try to extract a meaningful business description
    if body:
        # First, try to find user-facing descriptions
        # Look for "enables users/vendors to" patterns
        user_patterns = [
            r'(enables?|allows?|lets?)\s+(users?|vendors?|customers?)\s+to\s+([^.]+)',
            r'(users?|vendors?|customers?)\s+(can|will|now)\s+([^.]+)',
            r'(introduces?|adds?|implements?)\s+(the\s+)?(ability|feature|functionality|option)\s+for\s+(users?|vendors?|customers?)\s+to\s+([^.]+)',
        ]
        
        for pattern in user_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Get the actual action part (usually the last group)
                action_desc = groups[-1] if groups else None
                if action_desc and len(action_desc.strip()) > 15:
                    cleaned = clean_description(action_desc.strip())
                    if len(cleaned) > 15:
                        return f"{subject_clean}. {cleaned.capitalize()}"
        
        # Fallback: find first sentence that describes what was done (not how)
        sentences = body.split('.')
        for sentence in sentences[:2]:
            sentence = sentence.strip()
            if len(sentence) > 30:
                # Remove technical implementation details but keep functionality
                # Replace technical phrases with more natural ones
                sentence = re.sub(r'\b(adds?|introduces?|implements?)\s+(the\s+)?(ability|feature|functionality)\s+for\s+', 'enables ', sentence, flags=re.IGNORECASE)
                sentence = re.sub(r'\b(adds?|introduces?)\s+(a\s+)?new\s+', '', sentence, flags=re.IGNORECASE)
                
                cleaned = clean_description(sentence)
                # Check if it's meaningful (not just technical)
                if len(cleaned) > 25 and any(word in cleaned.lower() for word in ['user', 'vendor', 'order', 'payment', 'booking', 'dispute', 'transaction', 'wallet']):
                    return f"{subject_clean}. {cleaned[:200]}"
    
    return subject_clean


def convert_markdown_to_rtf(markdown: str) -> str:
    """Convert markdown summary to RTF format"""
    rtf = "{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}\\f0\\fs24 "
    
    lines = markdown.split('\n')
    for line in lines:
        # Headers
        if line.startswith('# '):
            text = line[2:].strip()
            rtf += f"\\par\\b\\fs32 {text}\\b0\\fs24\\par "
        elif line.startswith('## '):
            text = line[3:].strip()
            # Remove emojis for RTF
            text = re.sub(r'[✨🐛📈🔧📝🚀]', '', text).strip()
            rtf += f"\\par\\b\\fs28 {text}\\b0\\fs24\\par "
        elif line.startswith('### '):
            text = line[4:].strip()
            rtf += f"\\par\\b\\fs26 {text}\\b0\\fs24\\par "
        # Bold
        elif '**' in line:
            text = re.sub(r'\*\*(.+?)\*\*', r'\\b \1\\b0 ', line)
            rtf += f"\\par {text}\\par "
        # Bullet points
        elif line.startswith('- '):
            text = line[2:].strip()
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'\\b \1\\b0 ', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            rtf += f"\\par\\bullet {text}\\par "
        # Horizontal rule
        elif line.startswith('---'):
            rtf += "\\par\\brdrb\\brdrs\\brdrw10\\par "
        # Empty lines
        elif not line.strip():
            rtf += "\\par "
        # Regular text
        else:
            text = line.strip()
            if text:
                text = re.sub(r'\*\*(.+?)\*\*', r'\\b \1\\b0 ', text)
                text = re.sub(r'`(.+?)`', r'\1', text)
                rtf += f"{text}\\par "
    
    rtf += "}"
    return rtf


def convert_markdown_to_html(markdown: str) -> str:
    """Convert markdown summary to HTML format"""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Daily Development Summary</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
        h3 { color: #777; }
        ul { list-style-type: disc; padding-left: 30px; }
        li { margin: 8px 0; }
        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        strong { color: #333; }
        hr { border: none; border-top: 2px solid #ddd; margin: 20px 0; }
        .footer { color: #888; font-size: 0.9em; margin-top: 30px; font-style: italic; }
    </style>
</head>
<body>
"""
    
    lines = markdown.split('\n')
    for line in lines:
        # Headers
        if line.startswith('# '):
            text = line[2:].strip()
            html += f"<h1>{text}</h1>\n"
        elif line.startswith('## '):
            text = line[3:].strip()
            html += f"<h2>{text}</h2>\n"
        elif line.startswith('### '):
            text = line[4:].strip()
            html += f"<h3>{text}</h3>\n"
        # Bold
        elif '**' in line:
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html += f"<p>{text}</p>\n"
        # Code inline
        elif '`' in line and not line.startswith('-'):
            text = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
            html += f"<p>{text}</p>\n"
        # Bullet points
        elif line.startswith('- '):
            if html.count('<ul>') == html.count('</ul>'):
                html += "<ul>\n"
            text = line[2:].strip()
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
            text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
            html += f"<li>{text}</li>\n"
        # Horizontal rule
        elif line.startswith('---'):
            # Close any open ul
            if html.count('<ul>') > html.count('</ul>'):
                html += "</ul>\n"
            html += "<hr>\n"
        # Empty lines
        elif not line.strip():
            # Close ul if open
            if html.count('<ul>') > html.count('</ul>'):
                html += "</ul>\n"
            html += "\n"
        # Regular text
        else:
            text = line.strip()
            if text:
                text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
                text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
                html += f"<p>{text}</p>\n"
    
    # Close any open ul
    if html.count('<ul>') > html.count('</ul>'):
        html += "</ul>\n"
    
    html += """</body>
</html>"""
    return html


def generate_summary(commits: List[Dict]) -> str:
    """Generate a human-readable daily summary"""
    if not commits:
        return "# Daily Summary\n\nNo commits found for today.\n"
    
    categories = categorize_commits(commits)
    today = datetime.now().strftime("%B %d, %Y")
    
    summary = f"# Daily Development Summary - {today}\n\n"
    summary += f"**Branch:** `{BRANCH}`  \n"
    summary += f"**Total Commits:** {len(commits)}\n\n"
    summary += "---\n\n"
    
    # Features Section
    if categories["features"]:
        summary += "## ✨ New Functionality & Features\n\n"
        seen_features = set()
        for commit in categories["features"]:
            desc = extract_functionality_description(commit)
            if desc and desc not in seen_features and len(desc) > 10:
                summary += f"- {desc}\n"
                seen_features.add(desc)
        summary += "\n"
    
    # Bug Fixes Section
    if categories["bug_fixes"]:
        summary += "## 🐛 Bug Fixes & Issues Resolved\n\n"
        seen_fixes = set()
        for commit in categories["bug_fixes"]:
            desc = extract_functionality_description(commit)
            if desc and desc not in seen_fixes and len(desc) > 10:
                summary += f"- {desc}\n"
                seen_fixes.add(desc)
        summary += "\n"
    
    # Improvements Section
    if categories["improvements"]:
        summary += "## 📈 Improvements & Enhancements\n\n"
        seen_improvements = set()
        for commit in categories["improvements"]:
            desc = extract_functionality_description(commit)
            if desc and desc not in seen_improvements and len(desc) > 10:
                summary += f"- {desc}\n"
                seen_improvements.add(desc)
        summary += "\n"
    
    # Refactoring Section (only if there are meaningful refactoring commits)
    meaningful_refactors = [c for c in categories["refactoring"] if "remove" not in c["subject"].lower() or "cleanup" in c["subject"].lower()]
    if meaningful_refactors:
        summary += "## 🔧 Code Quality Improvements\n\n"
        seen_refactors = set()
        for commit in meaningful_refactors:
            desc = extract_functionality_description(commit)
            if desc and desc not in seen_refactors and len(desc) > 10:
                summary += f"- {desc}\n"
                seen_refactors.add(desc)
        summary += "\n"
    
    # Other commits (skip if empty or just cleanup)
    meaningful_other = [c for c in categories["other"] if len(extract_functionality_description(c)) > 15]
    if meaningful_other:
        summary += "## 📝 Other Updates\n\n"
        seen_other = set()
        for commit in meaningful_other:
            desc = extract_functionality_description(commit)
            if desc and desc not in seen_other and len(desc) > 10:
                summary += f"- {desc}\n"
                seen_other.add(desc)
        summary += "\n"
    
    # Next Steps / Forward Movement
    summary += "---\n\n"
    summary += "## 🚀 Forward Movement\n\n"
    summary += "Based on today's work, the following areas show progress:\n\n"
    
    # Analyze forward movement based on commit patterns
    all_messages = " ".join([c["full_message"].lower() for c in commits])
    
    forward_points = []
    if "feature" in all_messages or "add" in all_messages or "implement" in all_messages:
        forward_points.append("- Continued feature development and implementation")
    if "fix" in all_messages or "bug" in all_messages or "issue" in all_messages:
        forward_points.append("- Resolved critical issues improving system stability")
    if "improve" in all_messages or "enhance" in all_messages:
        forward_points.append("- Enhanced existing functionality for better user experience")
    if "refactor" in all_messages or "cleanup" in all_messages:
        forward_points.append("- Improved code quality and maintainability")
    
    if forward_points:
        summary += "\n".join(forward_points) + "\n\n"
    else:
        summary += "- Steady progress on development tasks\n\n"
    
    summary += f"\n---\n\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return summary


def main():
    """Main execution function"""
    print("🔍 Fetching today's commits from dev branch...")
    print(f"📁 Repository: {REPO_PATH}")
    print(f"🌿 Branch: {BRANCH}\n")
    
    # Check if repo exists
    if not REPO_PATH.exists():
        print(f"❌ Error: Repository path does not exist: {REPO_PATH}")
        return 1
    
    # Get today's commits
    commits = get_today_commits()
    
    if not commits:
        print("⚠️  No commits found for today.")
        return 0
    
    print(f"✅ Found {len(commits)} commit(s) for today\n")
    
    # Save commits to file
    save_commits_to_file(commits)
    
    # Generate summary
    print("📝 Generating daily summary...")
    summary_md = generate_summary(commits)
    
    # Ask user for format preference
    print("\n" + "=" * 60)
    print("📄 Choose output format:")
    print("  1. Markdown (.md) - Recommended for GitHub, documentation")
    print("  2. Rich Text (.rtf) - Compatible with Word, Pages, etc.")
    print("  3. HTML (.html) - For web viewing, email")
    print("  4. Plain Text (.txt) - Simple text format")
    print("  5. All formats")
    print("=" * 60)
    
    while True:
        choice = input("\nEnter your choice (1-5) [default: 1]: ").strip()
        if not choice:
            choice = "1"
        
        if choice in ["1", "2", "3", "4", "5"]:
            break
        print("❌ Invalid choice. Please enter 1, 2, 3, 4, or 5.")
    
    # Save in selected format(s)
    saved_files = []
    
    if choice in ["1", "5"]:
        # Markdown
        with open(SUMMARY_FILE_MD, "w", encoding="utf-8") as f:
            f.write(summary_md)
        saved_files.append(SUMMARY_FILE_MD)
        print(f"✅ Markdown summary saved to {SUMMARY_FILE_MD}")
    
    if choice in ["2", "5"]:
        # RTF
        rtf_content = convert_markdown_to_rtf(summary_md)
        with open(SUMMARY_FILE_RTF, "w", encoding="utf-8") as f:
            f.write(rtf_content)
        saved_files.append(SUMMARY_FILE_RTF)
        print(f"✅ RTF summary saved to {SUMMARY_FILE_RTF}")
    
    if choice in ["3", "5"]:
        # HTML
        html_content = convert_markdown_to_html(summary_md)
        html_file = REPO_PATH / "daily_summary.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        saved_files.append(html_file)
        print(f"✅ HTML summary saved to {html_file}")
    
    if choice in ["4", "5"]:
        # Plain Text (strip markdown formatting)
        txt_content = summary_md
        # Remove markdown formatting
        txt_content = re.sub(r'#+\s+', '', txt_content)  # Remove headers
        txt_content = re.sub(r'\*\*(.+?)\*\*', r'\1', txt_content)  # Remove bold
        txt_content = re.sub(r'`(.+?)`', r'\1', txt_content)  # Remove code
        txt_content = re.sub(r'^-\s+', '• ', txt_content, flags=re.MULTILINE)  # Convert bullets
        txt_content = re.sub(r'---+', '-' * 40, txt_content)  # Simplify HR
        
        with open(SUMMARY_FILE_TXT, "w", encoding="utf-8") as f:
            f.write(txt_content)
        saved_files.append(SUMMARY_FILE_TXT)
        print(f"✅ Plain text summary saved to {SUMMARY_FILE_TXT}")
    
    print(f"\n📋 Summary saved in {len(saved_files)} file(s)\n")
    print("=" * 60)
    print(summary_md)
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
