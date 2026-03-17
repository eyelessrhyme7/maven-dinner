#!/usr/bin/env python3
"""
Generate Link Data Script

For each unique pair of attendees (n*(n-1)/2 = 231 pairs for 22 people),
calls GPT-5.2 to generate synergy/connection data.

Input: scoped_profiles.json
Output: link_data.json
"""

import json
import itertools
from pathlib import Path
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

# JSON Schema for structured output
LINK_SCHEMA = {
    "type": "object",
    "properties": {
        "person_a_name": {"type": "string"},
        "person_b_name": {"type": "string"},
        "synergies": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3
        },
        "collaboration_opportunities": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3
        },
        "why_a_should_meet_b": {"type": "string"},
        "why_b_should_meet_a": {"type": "string"},
        "one_liner_both": {"type": "string"},
        "link_strength_score": {"type": "integer", "minimum": 0, "maximum": 100}
    },
    "required": [
        "person_a_name", "person_b_name", "synergies",
        "collaboration_opportunities", "why_a_should_meet_b",
        "why_b_should_meet_a", "one_liner_both", "link_strength_score"
    ],
    "additionalProperties": False
}

SYSTEM_PROMPT = """You are analyzing two attendee profiles for an exclusive founder/advisor dinner event. This dinner is designed to facilitate meaningful, high-value introductions between founders, advisors, investors, and operators. The goal is to spark collaborations, mentorships, partnerships, and serendipitous connections that create lasting professional value.

CONTEXT ABOUT THE DINNER:
- This is a curated gathering of ~22 exceptional individuals
- Each attendee submitted what they're building/working on (one_liner)
- Each attendee specified who they want to meet (who_they_want_to_meet)
- The dinner aims to create connections with real synergies, not just surface-level networking
- We want to help people discover non-obvious but valuable connections

YOUR TASK:
Analyze Person A and Person B's full profiles and determine how they should connect.

ANALYSIS GUIDELINES:

1. SYNERGIES (exactly 3 points, non-verbose):
   - Look for shared domains, complementary skills, overlapping networks
   - Consider their current projects, past experiences, education overlap
   - Identify mutual interests that could spark conversation
   - Keep each point to 5-10 words max

2. COLLABORATION OPPORTUNITIES (exactly 3 points, non-verbose):
   - Concrete ways they could work together or help each other
   - Consider: advisory, investment, partnership, customer/vendor, co-building
   - Keep each point to 5-10 words max

3. WHY A SHOULD MEET B (from A's perspective):
   - Consider A's current role, what A is building, A's career stage
   - Consider what A explicitly said they want from this dinner
   - Consider A's likely unstated needs based on their profile
   - Account for seniority differences - if B is more senior, A might seek guidance
   - 1-2 sentences max

4. WHY B SHOULD MEET A (from B's perspective):
   - Same analysis but from B's perspective
   - Account for seniority differences - if A is more junior but has fresh perspective/skills
   - 1-2 sentences max

5. ONE-LINER FOR BOTH:
   - A single compelling sentence explaining why these two should meet
   - This appears in the UI as the primary reason for the connection
   - Should capture the essence of the mutual value
   - NOT "A should meet B because..." - instead focus on the shared opportunity

6. LINK STRENGTH SCORE (0-100):
   - 80-100: Exceptional match - clear mutual benefit, strong synergies, obvious collaboration potential
   - 60-80: Good match - notable synergies, meaningful connection opportunity
   - 40-60: Moderate match - some common ground, worth an introduction
   - 20-40: Weak match - tangential connection, low priority
   - 0-20: Minimal overlap - unlikely to find value in meeting

SPECIAL CASES:
- CO-FOUNDERS: If A and B appear to be co-founders (same company, overlapping timelines), still give them a link score and synergies, but make the one_liner_both comically funny (e.g., "You should ideally be meeting every day. That's literally your co-founder.")
- SAME COMPANY: If they work at the same company but different roles, acknowledge this and focus on cross-functional collaboration"""


def format_profile_for_prompt(profile):
    """Format a profile into a readable string for the prompt."""
    basic_info = profile.get('basic_info', {})
    
    lines = []
    lines.append(f"Name: {basic_info.get('fullname', 'Unknown')}")
    lines.append(f"Headline: {basic_info.get('headline', '')}")
    lines.append(f"Current Company: {basic_info.get('current_company', '')}")
    lines.append(f"Location: {basic_info.get('location', {}).get('full', '')}")
    
    if basic_info.get('about'):
        lines.append(f"About: {basic_info.get('about')}")
    
    lines.append(f"One-liner (what they're building): {profile.get('one_liner', '')}")
    lines.append(f"Who they want to meet: {profile.get('who_they_want_to_meet', '')}")
    
    # Experience
    experience = profile.get('experience', [])
    if experience:
        lines.append("\nExperience:")
        for exp in experience[:5]:  # Limit to recent 5
            title = exp.get('title', '')
            company = exp.get('company', '')
            duration = exp.get('duration', '')
            desc = exp.get('description', '')
            lines.append(f"  - {title} at {company} ({duration})")
            if desc:
                lines.append(f"    {desc[:200]}...")
    
    # Education
    education = profile.get('education', [])
    if education:
        lines.append("\nEducation:")
        for edu in education[:3]:
            school = edu.get('school', '')
            degree = edu.get('degree', '')
            activities = edu.get('activities', '')
            lines.append(f"  - {degree} from {school}")
            if activities:
                lines.append(f"    Activities: {activities}")
    
    # Projects
    projects = profile.get('projects', [])
    if projects:
        lines.append("\nProjects:")
        for proj in projects[:3]:
            name = proj.get('name', '')
            desc = proj.get('description', '')[:150] if proj.get('description') else ''
            lines.append(f"  - {name}: {desc}")
    
    # Recommendations (brief)
    recommendations = profile.get('recommendations', {})
    received = recommendations.get('received_recommendations', [])
    if received:
        lines.append("\nNotable recommendation excerpts:")
        for rec in received[:2]:
            text = rec.get('recommendation_text', '')[:200]
            lines.append(f"  - \"{text}...\"")
    
    return '\n'.join(lines)


def generate_link_data(profile_a, profile_b):
    """Generate link data for a pair of profiles using GPT-5.2."""
    name_a = profile_a.get('basic_info', {}).get('fullname', 'Person A')
    name_b = profile_b.get('basic_info', {}).get('fullname', 'Person B')
    
    user_prompt = f"""PERSON A PROFILE:
{format_profile_for_prompt(profile_a)}

PERSON B PROFILE:
{format_profile_for_prompt(profile_b)}

Analyze these two profiles and generate the connection data."""
    
    try:
        result = client.responses.create(
            model="gpt-5.2",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            reasoning={"effort": "none"},
            text={
                "format": {
                    "type": "json_schema",
                    "strict": True,
                    "name": "link_data",
                    "schema": LINK_SCHEMA
                },
                "verbosity": "low"
            }
        )
        
        # Parse the response
        response_text = result.output_text
        link_entry = json.loads(response_text)
        
        # Ensure names are correct
        link_entry['person_a_name'] = name_a
        link_entry['person_b_name'] = name_b
        
        return link_entry
        
    except Exception as e:
        print(f"Error generating link data for {name_a} <-> {name_b}: {e}")
        # Return a fallback entry
        return {
            "person_a_name": name_a,
            "person_b_name": name_b,
            "synergies": ["Shared interest in innovation", "Both building startups", "Singapore-based founders"],
            "collaboration_opportunities": ["Knowledge exchange", "Network sharing", "Potential partnership"],
            "why_a_should_meet_b": f"{name_a} could benefit from connecting with {name_b}.",
            "why_b_should_meet_a": f"{name_b} could benefit from connecting with {name_a}.",
            "one_liner_both": "Two founders who could learn from each other's journeys.",
            "link_strength_score": 50
        }


def main():
    """Main function to generate link data for all pairs."""
    # Load profiles
    profiles_path = Path('scoped_profiles.json')
    if not profiles_path.exists():
        print("Error: scoped_profiles.json not found. Run the notebook first to generate it.")
        return
    
    with open(profiles_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    
    n = len(profiles)
    total_pairs = n * (n - 1) // 2
    print(f"Loaded {n} profiles")
    print(f"Generating link data for {total_pairs} pairs...")
    
    # Generate all unique pairs
    link_data = []
    pairs = list(itertools.combinations(range(n), 2))
    
    for i, (idx_a, idx_b) in enumerate(pairs, 1):
        profile_a = profiles[idx_a]
        profile_b = profiles[idx_b]
        
        name_a = profile_a.get('basic_info', {}).get('fullname', 'Unknown')
        name_b = profile_b.get('basic_info', {}).get('fullname', 'Unknown')
        
        print(f"[{i}/{total_pairs}] Processing: {name_a} <-> {name_b}")
        
        link_entry = generate_link_data(profile_a, profile_b)
        link_data.append(link_entry)
        
        # Save progress every 10 pairs
        if i % 10 == 0:
            with open('link_data.json', 'w', encoding='utf-8') as f:
                json.dump(link_data, f, indent=2, ensure_ascii=False)
            print(f"  Progress saved ({i}/{total_pairs})")
    
    # Final save
    with open('link_data.json', 'w', encoding='utf-8') as f:
        json.dump(link_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nDone! Generated {len(link_data)} link entries.")
    print(f"Output saved to link_data.json")
    
    # Summary statistics
    scores = [entry['link_strength_score'] for entry in link_data]
    print(f"\nLink strength statistics:")
    print(f"  Average: {sum(scores) / len(scores):.1f}")
    print(f"  Min: {min(scores)}")
    print(f"  Max: {max(scores)}")
    print(f"  80-100 (exceptional): {sum(1 for s in scores if s >= 80)}")
    print(f"  60-79 (good): {sum(1 for s in scores if 60 <= s < 80)}")
    print(f"  40-59 (moderate): {sum(1 for s in scores if 40 <= s < 60)}")
    print(f"  <40 (weak): {sum(1 for s in scores if s < 40)}")


if __name__ == "__main__":
    main()
