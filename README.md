# Maven Dinner

An interactive web app for curated dinner events that helps attendees discover meaningful connections. Features include:

- **Connection Map** (`index.html`) - Interactive D3.js graph visualization showing relationship strengths between attendees
- **Guess Who Game** (`game.html`) - Fun icebreaker game where attendees guess each other based on obscure facts
- **Phone View** (`phone.html`) - Mobile-friendly interface for browsing personalized connection recommendations

## Project Overview

This project processes LinkedIn profile data and dinner registration information to:
1. Generate AI-powered connection insights between all attendee pairs (synergies, collaboration opportunities, why they should meet)
2. Extract obscure/fun facts from each attendee's profile for the guessing game
3. Display everything in a beautiful, interactive web interface

## Prerequisites

- Python 3.8+
- OpenAI API key (for running the data generation scripts)
- A modern web browser

## Installation

1. Clone this repository
2. Install Python dependencies:

```bash
pip install openai pandas jupyter
```

3. Set your OpenAI API key:

```bash
# Windows
set OPENAI_API_KEY=your-api-key-here

# macOS/Linux
export OPENAI_API_KEY=your-api-key-here
```

## Data Preparation

### Input Files Required

1. **LinkedIn Profiles** - JSON file with LinkedIn profile data for each attendee
   - Use `mock_dataset_linkedin_profiles.json` as a template/example
   - Rename or copy to `dataset_linkedin_profiles.json`

   **Scraping LinkedIn Profiles:** You can use the [LinkedIn Profile Full Sections Scraper](https://apify.com/apimaestro/linkedin-profile-full-sections-scraper) on Apify to extract profile data in a compatible format. The scraper returns data with the same structure as `mock_dataset_linkedin_profiles.json` including:
   - `basic_info` (name, headline, location, about, etc.)
   - `experience` (work history with title, company, duration, description)
   - `education` (schools, degrees, activities)
   - `projects` (personal/professional projects)
   - `recommendations` (received and given)
   
   Simply provide LinkedIn profile usernames or URLs and export the results as JSON.

2. **Dinner Registration CSV** (optional) - `dinner_list_reg.csv` with columns:
   - `name` - Attendee name
   - `A one liner on what you're building or working on right now.`
   - `If this dinner is wildly successful, you walk away having met someone who ______`

### Running the Pipeline

Execute these steps in order:

#### Step 1: Process Profiles

Run the Jupyter notebook to merge LinkedIn profiles with dinner registration data:

```bash
jupyter notebook process_profiles.ipynb
```

Run cells 1-4 to generate `scoped_profiles.json`.

#### Step 2: Generate Link Data

Generate AI-powered connection data for all attendee pairs:

```bash
python generate_link_data.py
```

This creates `link_data.json` with synergies and collaboration opportunities for each pair.

**Note:** For N attendees, this generates N*(N-1)/2 API calls (e.g., 231 calls for 22 people).

#### Step 3: Generate Game Data

Extract obscure facts for the guessing game:

```bash
python generate_game_data.py
```

This creates `game_data.json` with hints and fun facts for each attendee.

#### Step 4: Build Final Dataset

Return to the notebook and run cells 5-7 to merge everything into `final_data.json`.

#### Step 5: Create Exclusions File

Create an `exclusions.json` file to track who has already met:

```json
[
  {"name": "Alex Chen", "alreadyMet": []},
  {"name": "Jordan Patel", "alreadyMet": []},
  {"name": "Maria Santos", "alreadyMet": []},
  {"name": "David Kim", "alreadyMet": []},
  {"name": "Emma Johnson", "alreadyMet": []}
]
```

## Running the Web App

Start a local Python server:

```bash
# Python 3
python -m http.server 8000
```

Then open your browser to:
- **Connection Map:** http://localhost:8000/index.html
- **Guess Who Game:** http://localhost:8000/game.html
- **Phone View:** http://localhost:8000/phone.html

## File Structure

```
maven-dinner/
├── index.html                      # Connection map visualization
├── game.html                       # Guess Who game
├── phone.html                      # Mobile-friendly connection browser
├── styles.css                      # Shared CSS styles
├── process_profiles.ipynb          # Jupyter notebook for data processing
├── generate_link_data.py           # Script to generate connection data
├── generate_game_data.py           # Script to generate game hints/facts
├── mock_dataset_linkedin_profiles.json  # Example LinkedIn profile data
├── README.md                       # This file
│
├── # Generated files (gitignored):
├── dataset_linkedin_profiles.json  # Your actual LinkedIn data
├── dinner_list_reg.csv             # Your dinner registration data
├── scoped_profiles.json            # Processed profiles (intermediate)
├── link_data.json                  # AI-generated connection data
├── game_data.json                  # AI-generated game data
├── final_data.json                 # Final merged dataset
└── exclusions.json                 # Who has already met whom
```

## Using the Mock Dataset

To test the app without real data:

1. Copy the mock dataset:
   ```bash
   cp mock_dataset_linkedin_profiles.json dataset_linkedin_profiles.json
   ```

2. Run the pipeline as described above

3. The mock dataset includes 5 generic profiles you can use to test the full workflow

## Customization

### Adjusting Connection Scoring

Edit the prompts in `generate_link_data.py` to adjust how connections are scored and described.

### Modifying Game Hints

Edit the prompts in `generate_game_data.py` to change what kinds of facts are extracted for the guessing game.

### Styling

All visual styles are in `styles.css`. The app uses a dark theme with green accents.

## API Usage Notes

The data generation scripts use OpenAI's API. Costs depend on:
- Number of attendees (N profiles = N game API calls + N*(N-1)/2 link API calls)
- Model used (configured in the Python scripts)
- Profile length (longer profiles = more tokens)

For 22 attendees: ~22 game calls + ~231 link calls = ~253 API calls total.

## License

MIT
