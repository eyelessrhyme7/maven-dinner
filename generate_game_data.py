#!/usr/bin/env python3
"""
Generate Game Data Script

For each person, extracts 5 obscure facts (for hints) + 2 fun facts 
from their LinkedIn profile for the guessing game.

Input: scoped_profiles.json
Output: game_data.json
"""

import json
from pathlib import Path
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

# JSON Schema for structured output
GAME_SCHEMA = {
    "type": "object",
    "properties": {
        "person_name": {"type": "string"},
        "obscure_facts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5
        },
        "fun_facts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 2
        }
    },
    "required": ["person_name", "obscure_facts", "fun_facts"],
    "additionalProperties": False
}

SYSTEM_PROMPT = """You are creating content for a "Guess Who?" minigame at an exclusive founder/advisor dinner event. The game shows obscure hints about a person, and other attendees try to guess who it is.

CONTEXT ABOUT THE DINNER & GAME:
- This dinner brings together ~22 founders, advisors, and operators
- The guessing game is an icebreaker to help people discover surprising things about each other
- Players see hints one at a time (Hint #1, then reveal Hint #2, then Hint #3)
- The goal is to find facts that are SURPRISING and OBSCURE relative to how this person is typically perceived
- When guessed correctly, a fun fact is revealed to spark conversation
- This creates memorable moments and gives people conversation starters for the dinner

YOUR TASK:
Analyze this person's full LinkedIn profile and extract:
- 5 obscure facts (ranked from most to least obscure) for use as hints
- 2 fun facts to display when the person is guessed correctly

WHAT MAKES A GOOD OBSCURE FACT:
- It should NOT be obviously related to their current domain/expertise
- It should surprise someone who only knows their professional headline
- Good sources: education activities, clubs, old jobs, volunteer work, quirky projects, unexpected skills, recommendations that mention personal traits, hobbies mentioned in about section
- The fact should be genuinely unexpected given their current professional identity
- It should make other attendees think "I never would have guessed that about them!"

EXAMPLES OF GOOD OBSCURE FACTS:
- "This person was president of the Drama Club in high school" (for a tech founder)
- "This person once worked as a professional DJ" (for a finance person)
- "This person built a game about time-traveling dinosaurs" (for an AI researcher)
- "This person received a recommendation praising their 'infectious enthusiasm for karaoke'"
- "This person studied classical piano for 12 years"
- "This person volunteered teaching coding to refugees"
- "This person was part of a comedy club during university"
- "This person interned at a company in Beijing"

EXAMPLES OF BAD OBSCURE FACTS (DO NOT USE THESE):
- "Is a founder of a tech startup" (too obvious/domain-related)
- "Works in AI/ML" (their main domain)
- "Has experience in software engineering" (professional identity)
- "Graduated from a top university with a CS degree" (expected background)
- "Is passionate about technology" (generic and domain-related)
- "Has worked at multiple startups" (expected for a founder)
- "Is based in Singapore" (too basic)

IMPORTANT CONSTRAINTS:
- All 5 obscure facts MUST be NON-OVERLAPPING (different topics/areas of their life)
- They should NEVER reveal or strongly hint at the person's main domain/company/role
- Each fact should be a single sentence, phrased as a hint (e.g., "This person once...")
- Rank from most obscure (Hint #1 - hardest to guess) to least obscure (Hint #5)
- All 7 facts total (5 hints + 2 fun facts) should ideally be non-overlapping if possible
- Look deep into their profile - activities, old jobs, recommendations, projects, volunteer work

FUN FACTS:
- These are revealed AFTER the guess, so they can be more personal/interesting
- Good for sparking conversation at the dinner
- Can include personality traits from recommendations, interesting projects, unique perspectives
- Should make people want to talk to this person about it

If the profile doesn't have enough obscure information, be creative in finding angles that would surprise others (e.g., specific project names that sound unusual, combinations of interests that are unexpected, etc.)."""


def format_profile_for_prompt(profile):
    """Format a profile into a comprehensive string for analysis."""
    basic_info = profile.get('basic_info', {})
    
    lines = []
    lines.append(f"=== PROFILE: {basic_info.get('fullname', 'Unknown')} ===")
    lines.append(f"Headline: {basic_info.get('headline', '')}")
    lines.append(f"Current Company: {basic_info.get('current_company', '')}")
    lines.append(f"Location: {basic_info.get('location', {}).get('full', '')}")
    
    if basic_info.get('about'):
        lines.append(f"\nAbout:\n{basic_info.get('about')}")
    
    lines.append(f"\nOne-liner (what they're building): {profile.get('one_liner', '')}")
    lines.append(f"Who they want to meet: {profile.get('who_they_want_to_meet', '')}")
    
    # Full Experience
    experience = profile.get('experience', [])
    if experience:
        lines.append("\n=== EXPERIENCE ===")
        for exp in experience:
            title = exp.get('title', '')
            company = exp.get('company', '')
            duration = exp.get('duration', '')
            location = exp.get('location', '')
            desc = exp.get('description', '')
            lines.append(f"\n{title} at {company}")
            lines.append(f"  Duration: {duration}")
            if location:
                lines.append(f"  Location: {location}")
            if desc:
                lines.append(f"  Description: {desc}")
    
    # Full Education
    education = profile.get('education', [])
    if education:
        lines.append("\n=== EDUCATION ===")
        for edu in education:
            school = edu.get('school', '')
            degree = edu.get('degree', '')
            duration = edu.get('duration', '')
            activities = edu.get('activities', '')
            description = edu.get('description', '')
            lines.append(f"\n{degree}")
            lines.append(f"  School: {school}")
            if duration:
                lines.append(f"  Duration: {duration}")
            if activities:
                lines.append(f"  Activities: {activities}")
            if description:
                lines.append(f"  Description: {description}")
    
    # Full Projects
    projects = profile.get('projects', [])
    if projects:
        lines.append("\n=== PROJECTS ===")
        for proj in projects:
            name = proj.get('name', '')
            desc = proj.get('description', '')
            associated = proj.get('associated_company', '')
            dates = f"{proj.get('start_date', '')} - {proj.get('end_date', '')}"
            lines.append(f"\n{name}")
            if associated:
                lines.append(f"  Associated with: {associated}")
            lines.append(f"  Dates: {dates}")
            if desc:
                lines.append(f"  Description: {desc}")
    
    # Full Recommendations (important for finding personality traits)
    recommendations = profile.get('recommendations', {})
    received = recommendations.get('received_recommendations', [])
    given = recommendations.get('given_recommendations', [])
    
    if received:
        lines.append("\n=== RECOMMENDATIONS RECEIVED ===")
        for rec in received:
            name = rec.get('recommender_name', '')
            relationship = rec.get('relationship', '')
            text = rec.get('recommendation_text', '')
            lines.append(f"\nFrom: {name}")
            lines.append(f"Relationship: {relationship}")
            lines.append(f"Text: {text}")
    
    if given:
        lines.append("\n=== RECOMMENDATIONS GIVEN ===")
        for rec in given:
            name = rec.get('recommender_name', '')
            relationship = rec.get('relationship', '')
            text = rec.get('recommendation_text', '')
            lines.append(f"\nTo: {name}")
            lines.append(f"Relationship: {relationship}")
            lines.append(f"Text: {text}")
    
    # Volunteer work
    volunteer = profile.get('volunteer', [])
    if volunteer:
        lines.append("\n=== VOLUNTEER EXPERIENCE ===")
        for vol in volunteer:
            lines.append(f"  - {json.dumps(vol)}")
    
    # Honors
    honors = profile.get('honors', [])
    if honors:
        lines.append("\n=== HONORS & AWARDS ===")
        for honor in honors:
            lines.append(f"  - {json.dumps(honor)}")
    
    # Publications
    publications = profile.get('publications', [])
    if publications:
        lines.append("\n=== PUBLICATIONS ===")
        for pub in publications:
            lines.append(f"  - {json.dumps(pub)}")
    
    # Organizations
    organizations = profile.get('organizations', [])
    if organizations:
        lines.append("\n=== ORGANIZATIONS ===")
        for org in organizations:
            lines.append(f"  - {json.dumps(org)}")
    
    return '\n'.join(lines)


def generate_game_data(profile):
    """Generate game data for a single profile using GPT-5.2."""
    name = profile.get('basic_info', {}).get('fullname', 'Unknown')
    
    user_prompt = f"""Analyze this person's full profile and extract obscure facts for the guessing game.

{format_profile_for_prompt(profile)}

Remember:
- Find 5 truly OBSCURE facts that would surprise someone who only knows their headline
- Each hint should be phrased as "This person..." 
- Rank from most obscure (hardest to guess) to least obscure
- All facts should be NON-OVERLAPPING and unrelated to their main domain
- Also provide 2 fun facts to display after guessing"""
    
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
                    "name": "game_data",
                    "schema": GAME_SCHEMA
                },
                "verbosity": "low"
            }
        )
        
        # Parse the response
        response_text = result.output_text
        game_entry = json.loads(response_text)
        
        # Ensure name is correct
        game_entry['person_name'] = name
        
        return game_entry
        
    except Exception as e:
        print(f"Error generating game data for {name}: {e}")
        # Return a fallback entry
        return {
            "person_name": name,
            "obscure_facts": [
                f"This person has a unique background in their field.",
                f"This person has worked in unexpected industries.",
                f"This person has diverse interests outside of work.",
                f"This person has received praise for unexpected skills.",
                f"This person has an interesting educational journey."
            ],
            "fun_facts": [
                f"{name} brings a unique perspective to the dinner.",
                f"Ask {name} about their journey - it's full of surprises!"
            ]
        }


def main():
    """Main function to generate game data for all profiles."""
    # Load profiles
    profiles_path = Path('scoped_profiles.json')
    if not profiles_path.exists():
        print("Error: scoped_profiles.json not found. Run the notebook first to generate it.")
        return
    
    with open(profiles_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    
    n = len(profiles)
    print(f"Loaded {n} profiles")
    print(f"Generating game data for {n} people...")
    
    # Generate game data for each person
    game_data = []
    
    for i, profile in enumerate(profiles, 1):
        name = profile.get('basic_info', {}).get('fullname', 'Unknown')
        
        print(f"[{i}/{n}] Processing: {name}")
        
        game_entry = generate_game_data(profile)
        game_data.append(game_entry)
        
        # Save progress every 5 entries
        if i % 5 == 0:
            with open('game_data.json', 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2, ensure_ascii=False)
            print(f"  Progress saved ({i}/{n})")
    
    # Final save
    with open('game_data.json', 'w', encoding='utf-8') as f:
        json.dump(game_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nDone! Generated game data for {len(game_data)} people.")
    print(f"Output saved to game_data.json")
    
    # Show sample
    print("\nSample entry:")
    sample = game_data[0]
    print(f"  Person: {sample['person_name']}")
    print(f"  Hint #1: {sample['obscure_facts'][0]}")
    print(f"  Fun fact #1: {sample['fun_facts'][0]}")


if __name__ == "__main__":
    main()
