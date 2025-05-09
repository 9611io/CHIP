import streamlit as st
import time
import uuid
import openai
import os
import re
import json
import random
import logging
import datetime
# import requests # No longer needed for Edge Function
import gspread # Added for Google Sheets
from google.oauth2.service_account import Credentials # Added for Google Sheets auth
import pandas as pd # Added for data handling
import plotly.express as px # Added for chart generation
# from supabase import create_client, Client # No longer needed

# --- Basic Logging Setup ---
log_filename = f"chip_app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

class SessionIdFilter(logging.Filter):
    def filter(self, record):
        # Ensure session_id is always present on the record
        if not hasattr(record, 'session_id'):
            try:
                # Attempt to get session_id only if session_state is available and has the necessary keys
                if hasattr(st, 'session_state') and 'key_prefix' in st.session_state and f"{st.session_state.key_prefix}_session_id" in st.session_state:
                    record.session_id = st.session_state.get(f"{st.session_state.key_prefix}_session_id", "N/A_Filter_Fallback")
                else:
                    record.session_id = "N/A_Filter_NoPrefixOrSS" # Default if session_state or keys are missing
            except Exception:
                record.session_id = "N/A_Filter_Exception" # Default on any error accessing session_state
        return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - SessionID:%(session_id)s - Name:%(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

root_logger = logging.getLogger()
# Ensure the filter is added only once to the root logger
if not any(isinstance(f, SessionIdFilter) for f in root_logger.filters):
    root_logger.addFilter(SessionIdFilter())


class SessionLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        session_id = "N/A_Adapter" # Default
        try:
            # Check if st.session_state exists and has the key_prefix
            if hasattr(st, 'session_state') and st.session_state.get('key_prefix'):
                prefix = st.session_state.key_prefix
                session_id = st.session_state.get(f"{prefix}_session_id", "N/A_Adapter_NoSessionID")
            # If st.session_state is not available or key_prefix is missing, session_id remains "N/A_Adapter"
        except Exception:
            # In case of any error accessing session_state, session_id remains "N/A_Adapter"
            pass

        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra']['session_id'] = session_id
        return msg, kwargs

logger_raw = logging.getLogger(__name__) # Use the app's module name
logger = SessionLogAdapter(logger_raw, {}) # Initialize the adapter
logger.info("--- Application Started ---") # This will use the adapter


# --- REMOVED: Supabase Connection Function ---

# --- REMOVED: Function to Initialize Feedback Table (init_feedback_table) ---
# Table creation is now handled manually.

# --- Moved Helper Function Definition Earlier ---
def init_session_state_key(key, default_value):
    """Initializes session state key with prefix if not present."""
    full_key = f"{st.session_state.key_prefix}_{key}"
    if full_key not in st.session_state:
        st.session_state[full_key] = default_value

# --- Session State Initialization ---
# This section now runs AFTER init_session_state_key is defined.
if 'key_prefix' not in st.session_state:
    st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    init_session_state_key('session_id', str(uuid.uuid4())) # Now defined
    logger.info(f"Initialized new session with prefix: {st.session_state.key_prefix} and SessionID: {st.session_state.get(f'{st.session_state.key_prefix}_session_id')}")
elif f"{st.session_state.key_prefix}_session_id" not in st.session_state:
     init_session_state_key('session_id', str(uuid.uuid4())) # Now defined
     logger.info(f"Re-initialized SessionID for existing prefix {st.session_state.key_prefix}: {st.session_state.get(f'{st.session_state.key_prefix}_session_id')}")

# --- Updated Skill List ---
SKILLS = ["Clarifying", "Hypothesis", "Frameworks", "Analysis", "Recommendation"]
# --- End Update ---

init_session_state_key('selected_skill', SKILLS[0]) # Now defined
init_session_state_key('run_count', 0) # Now defined
# init_session_state_key('show_donation_dialog', False) # REMOVED - No longer needed


# --- Page Config ---
st.set_page_config(
    page_title="CHIP", # Restored title
    page_icon="🤖",
    layout="centered", # Keep centered layout for main content
    initial_sidebar_state="expanded" # Keep sidebar open initially
)

# --- Custom CSS ---
# [ CSS remains unchanged ]
st.markdown("""
<style>
    /* --- Overall Theme --- */
    /* Using Streamlit defaults, add targeted styles below */
    .main .block-container {
         padding-top: 2rem;
         padding-bottom: 2rem;
    }

    /* --- Headers & Titles --- */
    h1 { /* Main Title: CHIP... */
        text-align: center;
        font-weight: bold;
        font-size: 2.5em;
        margin-bottom: 20px; /* Add more space below title */
    }
    /* Removed skill-focus-badge */
     h2 { /* Section Headers: Case Prompt, Ask... */
        /* color: #E0E0E0; */ /* Use default theme color */
        border-bottom: 1px solid #DDDDDD; /* Lighter border for light theme */
        padding-bottom: 8px;
        margin-top: 40px;
        margin-bottom: 20px;
        font-size: 1.5em;
    }
     h3 { /* Subheader for Rating */
        /* color: #FAFAFA; */ /* Use default theme color */
        margin-top: 25px;
        margin-bottom: 10px;
        font-size: 1.2em;
     }

    /* --- Containers & Cards --- */
    .stContainer, .stBlock {
        border-radius: 8px;
    }
    hr { /* Divider */
        border-top: 1px solid #DDDDDD; /* Lighter divider */
        margin-top: 30px;
        margin-bottom: 30px;
    }

    /* --- Custom Card for Case Prompt --- */
    /* Reverting to st.info, so removing card styles */
    /* .case-prompt-card { ... } */


    /* --- Chat Area --- */
    /* Container for chat history - use default styling */
    /* div[data-testid="stVerticalBlock"] ... { ... } */

    /* --- REMOVED ALL CUSTOM CHAT MESSAGE/ICON CSS --- */
    /* Let st.chat_message use its defaults for the active theme */


    /* --- Buttons --- */
    div[data-testid="stButton"] > button {
        border-radius: 8px;
        padding: 10px 24px;
        border: 1px solid #CCCCCC; /* Default border */
        background-color: #F0F0F0; /* Default background */
        color: #31333F; /* Default text */
        font-weight: bold;
        transition: background-color 0.2s ease-in-out, transform 0.1s ease-in-out, border-color 0.2s ease-in-out;
        margin-top: 15px; /* Default top margin */
        width: 100%; /* Make buttons fill column width */
    }
    /* Style for primary buttons (selected skill, main actions) */
    div[data-testid="stButton"] > button[kind="primary"] {
         background-color: #FF4B4B; /* Streamlit primary color */
         border-color: #FF4B4B;
         color: white;
         font-weight: bold;
    }
    /* Style for secondary buttons (inactive skill selection) */
    div[data-testid="stButton"] > button:not([kind="primary"]) {
         background-color: #FFFFFF; /* White background for inactive */
         color: #31333F; /* Default text color */
         border: 1px solid #CCCCCC;
         font-weight: normal; /* Normal weight for inactive */
    }

    div[data-testid="stButton"] > button:hover {
        border-color: #FF4B4B;
        color: #FF4B4B;
        transform: scale(1.02);
    }
    /* Hover for secondary buttons */
    div[data-testid="stButton"] > button:not([kind="primary"]):hover {
         border-color: #FF4B4B;
         color: #FF4B4B;
         background-color: #FFFFFF; /* Keep background white on hover */
    }

     div[data-testid="stButton"] > button:active {
        transform: scale(0.98);
     }
     div[data-testid="stButton"] > button * {
        background-color: transparent !important;
        color: inherit !important;
     }
     /* Style star buttons */
     div[data-testid="stButton"] > button[key*="star_"] {
        font-size: 1.8em; padding: 0px 5px; color: #ffc107; border: none; background: none !important;
        box-shadow: none; margin-top: 5px; transition: transform 0.1s ease-in-out;
     }
      div[data-testid="stButton"] > button[key*="star_"]:hover { background: none !important; transform: scale(1.1); }
      div[data-testid="stButton"] > button[key*="star_"]:active { transform: scale(0.95); }
      div[data-testid="stButton"] > button[key*="star_"] * { background-color: transparent !important; color: inherit !important; }

     /* Style for "Maybe later" button in dialog */
     div[data-testid="stButton"] > button[key*="maybe_later_btn"] { /* Match any maybe later btn */
         background: none !important;
         border: none !important;
         color: #31333F !important; /* Default text color */
         font-weight: normal !important;
         box-shadow: none !important;
         text-decoration: underline !important; /* Make it look like a link */
         margin-top: 5px !important;
         padding: 10px 24px !important;
         width: 100% !important;
     }
     div[data-testid="stButton"] > button[key*="maybe_later_btn"]:hover {
         background: none !important;
         color: #FF4B4B !important; /* Primary color on hover */
         text-decoration: underline !important;
         transform: none !important; /* No scaling */
     }
     div[data-testid="stButton"] > button[key*="maybe_later_btn"]:active {
          background: none !important;
          transform: none !important; /* No scaling */
          box-shadow: none !important;
          border: none !important;
     }

     /* --- Style for Donation Link Button (Now in Sidebar) --- */
     /* Target link buttons within the sidebar */
     [data-testid="stSidebar"] a[data-testid="stLinkButton"] {
        background-color: #28a745 !important; /* Green background */
        border-color: #28a745 !important; /* Green border */
        color: white !important; /* White text */
        transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out;
        width: 100%; /* Make button fill sidebar width */
        text-align: center; /* Center text */
        margin-top: 10px; /* Add some space above */
        display: inline-block; /* Needed for width/padding */
        padding: 10px 0px !important; /* Adjust padding */
        border-radius: 8px;
        text-decoration: none; /* Remove underline */
     }
     [data-testid="stSidebar"] a[data-testid="stLinkButton"]:hover {
         background-color: #218838 !important; /* Darker green on hover */
         border-color: #1e7e34 !important;
         color: white !important;
         text-decoration: none; /* Remove underline */
     }


    /* --- Text Area & Chat Input --- */
    div[data-testid="stTextArea"] textarea { /* Style for feedback comment box */
        border: 1px solid #D0D0D0;
        border-radius: 8px;
    }
     /* Default stChatInput styling */
     div[data-testid="stChatInput"] { /* Keep this even if not using st.chat_input now, might be used later */
         border-top: 1px solid #DDDDDD;
         padding-top: 15px;
     }
      div[data-testid="stChatInput"] textarea {
          border: 1px solid #CCCCCC;
          border-radius: 8px;
      }
     /* Style for the replacement st.text_input */
     div[data-testid="stTextInput"] textarea {
         border: 1px solid #CCCCCC;
         border-radius: 8px;
         padding: 0.5rem; /* Adjust padding as needed */
     }
     /* Ensure form elements are aligned */
     form[data-testid="stForm"] {
         /* border-top: 1px solid #DDDDDD; */ /* Optional: Add border like chat_input */
         padding-top: 10px; /* Add some padding above the form */
     }


    /* --- Other Elements --- */
    /* Using default alert box styling */

</style>
""", unsafe_allow_html=True)
# --- End of Restored Section ---


# --- Configuration (OpenAI, Prompts) ---
# [ Remains the same ]
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=openai.api_key)
    logger.info("Using API Key from Streamlit secrets.")
except KeyError:
    logger.warning("API Key not found in Streamlit secrets, checking environment variable.")
    api_key_env = os.environ.get("OPENAI_API_KEY")
    if api_key_env:
        openai.api_key = api_key_env
        client = openai.OpenAI(api_key=openai.api_key)
        logger.info("Using API Key from environment variable.")
    else:
        logger.error("OpenAI API key not found in secrets or environment variable.")
        st.error("OpenAI API key not found. Please set it in Streamlit secrets (secrets.toml) or as an environment variable OPENAI_API_KEY.")
        st.stop()
except Exception as e:
    logger.exception(f"Error initializing OpenAI client: {e}")
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()

# --- Load Prompts ---
# [ Remains the same ]
PROMPTS_FILE = "prompts.json"
ALL_PROMPTS = []
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_path = os.path.join(script_dir, PROMPTS_FILE)
    if not os.path.exists(prompts_path):
         logger.warning(f"Prompts file not found at {prompts_path}, trying current directory.")
         prompts_path = PROMPTS_FILE

    logger.info(f"Attempting to load prompts from: {os.path.abspath(prompts_path)}")
    with open(prompts_path, 'r', encoding='utf-8') as f:
        ALL_PROMPTS = json.load(f)
    if not isinstance(ALL_PROMPTS, list) or not all(isinstance(p, dict) and 'id' in p and 'prompt_text' in p for p in ALL_PROMPTS):
         raise ValueError("Prompts JSON must be a list of dictionaries, each with 'id' and 'prompt_text' keys.")
    ALL_PROMPT_IDS = [p['id'] for p in ALL_PROMPTS]
    if not ALL_PROMPT_IDS:
        logger.error("No prompts found in prompts.json!")
        st.error("Error: No prompts found in prompts.json!")
        ALL_PROMPTS = [{"id": "default_error", "title": "Default Prompt (Error Loading File)", "prompt_text": "Error: Could not load prompts correctly from prompts.json."}]
        ALL_PROMPT_IDS = ["default_error"]
    logger.info(f"Loaded {len(ALL_PROMPTS)} prompts successfully.")
except FileNotFoundError:
    logger.error(f"{PROMPTS_FILE} not found!")
    st.error(f"Error: {PROMPTS_FILE} not found! Ensure it's in the same directory as the script or provide the correct path.")
    ALL_PROMPTS = [{"id": "default_notfound", "title": "Default Prompt (File Not Found)", "prompt_text": f"Error: {PROMPTS_FILE} file was not found."}]
    ALL_PROMPT_IDS = ["default_notfound"]
except (json.JSONDecodeError, ValueError) as e:
     logger.error(f"Error parsing {PROMPTS_FILE}: {e}")
     st.error(f"Error parsing {PROMPTS_FILE}: {e}. Please ensure it's valid JSON.")
     ALL_PROMPTS = [{"id": "default_parse_error", "title": "Default Prompt (Parse Error)", "prompt_text": f"Error: Could not parse {PROMPTS_FILE}."}]
     ALL_PROMPT_IDS = ["default_parse_error"]
except Exception as e:
    logger.exception(f"An unexpected error occurred loading prompts: {e}")
    st.error(f"An unexpected error occurred loading prompts: {e}")
    ALL_PROMPTS = [{"id": "default_unknown_error", "title": "Default Prompt (Unknown Error)", "prompt_text": "Error: Unknown error loading prompts."}]
    ALL_PROMPT_IDS = ["default_unknown_error"]


# --- Helper Functions ---
# [ reset_skill_state definition remains here, added hypothesis_count and exhibit_index ]
def reset_skill_state():
    """Resets state variables specific to a practice run within a skill."""
    prefix = st.session_state.key_prefix
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "Unknown")
    logger.info(f"Resetting state for skill change to: {selected_skill}")

    keys_to_reset = [
        'current_prompt_id', 'conversation', 'done_asking',
        'feedback_submitted', 'user_feedback', 'interaction_start_time',
        'total_time', 'is_typing', 'feedback',
        'show_comment_box', 'feedback_rating_value',
        'hypothesis_count',
        'analysis_input',
        'current_exhibit_index', # Added for Analysis skill
        'recommendation_input' # Added for Recommendation skill
    ]
    logger.info(f"Resetting state keys: {keys_to_reset}")
    for key in keys_to_reset:
        full_key = f"{prefix}_{key}"
        if full_key in st.session_state:
            try:
                del st.session_state[full_key]
            except KeyError:
                pass

    # Re-initialize essential keys
    init_session_state_key('conversation', [])
    init_session_state_key('done_asking', False)
    init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False)
    init_session_state_key('feedback', None)
    init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None)
    init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0)
    init_session_state_key('user_feedback', None)
    init_session_state_key('current_prompt_id', None)
    init_session_state_key('hypothesis_count', 0)
    init_session_state_key('analysis_input', "")
    init_session_state_key('current_exhibit_index', 0)
    init_session_state_key('recommendation_input', "") # Added for Recommendation skill


# --- UPDATED: Function to Save User Feedback via Google Sheets ---
def save_user_feedback(feedback_data):
    """
    Saves the user feedback to the configured Google Sheet.
    Uses Sheet ID for robustness.
    """
    prefix = st.session_state.key_prefix
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = feedback_data.get("prompt_id", "N/A")
    rating = feedback_data.get("rating")
    comment = feedback_data.get("comment", "")
    timestamp = datetime.datetime.fromtimestamp(feedback_data.get("timestamp", time.time())).isoformat()

    log_message = (
        f"Attempting to save USER_FEEDBACK via Google Sheets :: Skill: {selected_skill}, "
        f"PromptID: {prompt_id}, Rating: {rating}, Comment: '{comment}'"
    )
    logger.info(log_message)

    try:
        # Get Google Sheet credentials and sheet ID from secrets
        creds_dict = st.secrets["google_credentials"]
        sheet_id = st.secrets["GSHEET_ID"] # Use Sheet ID now
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)

        # Open the spreadsheet by its unique ID
        spreadsheet = gc.open_by_key(sheet_id)
        logger.info(f"Opened Google Sheet with ID: {sheet_id}")
        # Assume data goes into the first worksheet
        worksheet = spreadsheet.get_worksheet(0)

        # Prepare data row - ORDER MATTERS, must match your sheet columns
        # Example order: Timestamp, SessionID, Skill, PromptID, Rating, Comment
        row_to_insert = [
            timestamp,
            session_id,
            selected_skill,
            prompt_id,
            rating if rating is not None else "", # Handle potential None rating
            comment
        ]

        # Append the row
        worksheet.append_row(row_to_insert, value_input_option='USER_ENTERED')

        logger.info(f"Successfully saved feedback to Google Sheet ID '{sheet_id}' for SessionID: {session_id}")
        return True

    except KeyError as e:
        logger.error(f"Missing required Google Sheets configuration in Streamlit secrets: {e}")
        st.error(f"Configuration error: Missing Google Sheets setting '{e}' in secrets. Check GSHEET_ID and google_credentials.")
        return False
    except gspread.exceptions.APIError as e:
         logger.exception(f"Google API error: {e}")
         # Try to parse the error response for more details
         try:
             error_details = e.response.json()
             st.error(f"Google API Error saving feedback: {error_details.get('error', {}).get('message', str(e))}")
         except: # If parsing fails, show the raw error
             st.error(f"Google API Error saving feedback: {e}")
         return False
    except gspread.exceptions.SpreadsheetNotFound:
        # This error might still occur if the ID is wrong or sharing is incorrect
        logger.error(f"Google Sheet with ID '{st.secrets.get('GSHEET_ID', 'MISSING_ID')}' not found or not shared correctly.")
        st.error(f"Error saving feedback: Spreadsheet not found. Ensure the GSHEET_ID in secrets is correct and the sheet is shared with the service account email.")
        return False
    except Exception as e:
        logger.exception(f"Error saving feedback to Google Sheets: {e}")
        st.error(f"Error saving feedback to Google Sheets: {e}")
        return False


# --- Other Helper Functions (select_new_prompt, get_prompt_details, parse_interviewer_response, send_question, generate_final_feedback) ---
def select_new_prompt():
    """Selects a new random prompt for the current skill, avoiding session repeats if possible."""
    prefix = st.session_state.key_prefix
    used_ids_key = f"{prefix}_used_prompt_ids"
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", SKILLS[0])

    init_session_state_key('used_prompt_ids', []) # Ensure it exists

    # Filter prompts by the currently selected skill
    skill_prompts = [p for p in ALL_PROMPTS if p.get('skill_type') == selected_skill]
    if not skill_prompts:
        logger.error(f"No prompts found for skill: {selected_skill}")
        st.error(f"Error: No prompts found for the selected skill '{selected_skill}'. Please check prompts.json.")
        return None

    skill_prompt_ids = [p['id'] for p in skill_prompts]
    available_prompt_ids = [pid for pid in skill_prompt_ids if pid not in st.session_state[used_ids_key]]

    if not available_prompt_ids:
        logger.warning(f"All prompts for skill '{selected_skill}' seen in this session, allowing repeats.")
        st.info("You've seen all available prompts for this skill in this session! Allowing repeats now.")
        # Reset used IDs *only* for this skill's prompts to allow repeats
        st.session_state[used_ids_key] = [pid for pid in st.session_state[used_ids_key] if pid not in skill_prompt_ids]
        available_prompt_ids = skill_prompt_ids
        if not available_prompt_ids: # Should not happen if skill_prompts was not empty
            logger.error(f"Cannot select prompt - prompt list for skill '{selected_skill}' is empty even after reset.")
            st.error(f"Cannot select prompt - prompt list for skill '{selected_skill}' is empty.")
            return None

    selected_id = random.choice(available_prompt_ids)
    st.session_state[used_ids_key].append(selected_id)
    st.session_state[current_prompt_id_key] = selected_id
    logger.info(f"Selected Prompt ID: {selected_id} for skill {selected_skill}")
    return selected_id

def get_prompt_details(prompt_id):
    """Retrieves prompt details from the loaded list using its ID."""
    if not prompt_id: return None
    for prompt in ALL_PROMPTS:
        if prompt.get('id') == prompt_id:
            return prompt
    logger.warning(f"Prompt ID '{prompt_id}' not found in loaded prompts.")
    return None

def parse_interviewer_response(response_text, skill):
    """
    Parses the LLM response based on the skill.
    """
    # Default values
    answer = response_text.strip() if response_text else "[Empty Response]"
    assessment = None

    # Use new skill names for checks
    # Recommendation feedback should also be structured
    if skill in ["Clarifying", "Frameworks", "Analysis", "Recommendation"]:
        answer_match = re.search(r"###ANSWER###\s*(.*?)\s*###ASSESSMENT###", response_text, re.DOTALL | re.IGNORECASE)
        assessment_match = re.search(r"###ASSESSMENT###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if answer_match: answer = answer_match.group(1).strip()
        if assessment_match: assessment = assessment_match.group(1).strip()
        # Simplified logging for brevity during debug
        if not answer_match and not assessment_match and response_text: answer = response_text.strip(); assessment = "[Assessment not extracted]"
        elif answer_match and not assessment_match: assessment = "[Assessment delimiter missing]"
        elif not answer_match and assessment_match: answer = "[Answer delimiter missing]"
        elif not response_text or not response_text.strip(): answer = "[LLM empty response]"; assessment = "[LLM empty response]"

    elif skill == "Hypothesis":
        # For hypothesis interaction, return the whole response as the "answer"
        # Remove potential delimiters if the LLM accidentally includes them
        answer = re.sub(r"###ANSWER###", "", answer, flags=re.IGNORECASE)
        answer = re.sub(r"###ASSESSMENT###", "", answer, flags=re.IGNORECASE).strip()
        assessment = None # No assessment during hypothesis interaction
        if not answer:
            logger.warning("LLM returned empty response for Hypothesis Formulation interaction.")
            answer = "[CHIP did not provide further information]"

    else:
        logger.warning(f"Parsing response for unknown or unhandled skill: {skill}. Returning raw text.")
        # Keep raw text as answer, assessment remains None

    return answer, assessment


def send_question(question, current_case_prompt_text, exhibit_context=None):
    """
    Sends user question/input to LLM, gets response based on skill, updates conversation state.
    Includes optional exhibit_context for Analysis skill.
    NOTE: This function is NO LONGER used for the main interaction loop of Analysis or Recommendation.
          It's kept for Clarifying Questions and Hypothesis Formulation.
    """
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    is_typing_key = f"{prefix}_is_typing"
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")
    hypothesis_count_key = f"{prefix}_hypothesis_count" # Key for hypothesis counter
    done_key = f"{prefix}_done_asking" # Key to end session

    if not question or not question.strip(): st.warning("Please enter your input."); logger.warning("User attempted to send empty input."); return
    if not current_case_prompt_text: st.error("Internal Error: No case prompt context."); logger.error("Internal Error: send_question called without case_prompt_text."); return

    st.session_state[is_typing_key] = True
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - User Input: '{question}'")
    # Store user message
    st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": question})

    # Increment hypothesis count if this is the relevant skill
    current_hypothesis_count = 0
    if selected_skill == "Hypothesis": # Use new skill name
        current_hypothesis_count = st.session_state.get(hypothesis_count_key, 0) + 1
        st.session_state[hypothesis_count_key] = current_hypothesis_count
        logger.info(f"Hypothesis count incremented to: {current_hypothesis_count}")


    try:
        history_for_prompt = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.get(conv_key, [])[:-1]]) # History *before* current input
        latest_input = question # The user's latest question or hypothesis

        # --- Define LLM Prompt based on Skill ---
        prompt_for_llm = ""
        system_message = ""
        max_tokens = 350 # Default
        temperature = 0.5 # Default

        if selected_skill == "Clarifying": # Use new skill name
            prompt_for_llm = f"""
            You are a **strict** case interviewer simulator focusing ONLY on the clarifying questions phase. Evaluate questions **rigorously**.

            Current Case Prompt Context:
            {current_case_prompt_text}

            Conversation History So Far:
            {history_for_prompt}

            Interviewee's Latest Question:
            {latest_input}

            Your Task:
            1. Provide a concise, helpful answer... [rest of Task 1 remains the same - plausible answers etc.] ...**Crucially, maintain consistency with any previous answers you've given in this conversation.**
            2. Assess the quality of *this specific question* **rigorously** based on the following categories of effective clarifying questions:
                * **Objective Clarification:** Does it clarify the case goal/problem statement?
                * **Company Understanding:** Does it seek relevant info about the client/company structure, situation, or industry context?
                * **Term Definition:** Does it clarify specific jargon or unfamiliar terms used in the case or prior answers?
                * **Information Repetition/Confirmation:** Does it concisely ask to repeat or confirm specific crucial information potentially missed?
                * **Question Quality:** Is the question concise, targeted, and NOT compound (asking multiple things at once)?
               **Critically evaluate:** If the question is extremely vague (e.g., single words like 'why?', 'what?', 'how?'), generic, irrelevant to the case context, compound, or doesn't clearly fit the positive categories above, **assess it as Poor (1/5)** and state *why* it's poor (e.g., 'Too vague, doesn't specify what information is needed'). Otherwise, rate from 2-5 based on how well it fits the categories and quality criteria. Be brief but justify the assessment clearly.
            3. Use the following exact format, including the delimiters on separate lines:

            ###ANSWER###
            [Your plausible answer here]
            ###ASSESSMENT###
            [Your brief but rigorous assessment of the question's quality based on the criteria above]
            """
            system_message = "You are a strict case interview simulator for clarifying questions. Evaluate questions rigorously based on specific categories (Objective, Company, Terms, Repetition, Quality). Provide plausible answers if needed. Use the specified response format."
            # --- End of Reverted Prompt ---
            max_tokens = 350
            temperature = 0.5

        elif selected_skill == "Hypothesis": # Use new skill name
            # --- Refined Interaction Prompt v4 (Hypothesis) ---
            prompt_for_llm = f"""
            You are playing the role of a case interviewer providing data/information in response to a candidate's hypothesis.
            The candidate is trying to diagnose an issue based on the case prompt.

            **Your Task:** Respond to the "Candidate's Latest Hypothesis/Area to Investigate" below.

            * **IF** the candidate's input ("{latest_input}") is a reasonable, testable hypothesis related to the case context ("{current_case_prompt_text}"):
                * Provide a concise (1-2 sentences) piece of plausible, new information that *contradicts* their current line of thinking or suggests it's not the primary driver of the issue.
                * This information should be consistent with any previous information you've provided.
                * Sound like a neutral source of data.
                * **Example of good contradictory info:** If hypothesis is "the issue is rising material costs", you could say "Recent supplier contracts indicate material costs have actually decreased by 5% this quarter."
            * **ELSE IF** the candidate's input is clearly nonsensical, irrelevant, or too vague to be a testable hypothesis:
                * **DO NOT provide contradictory case information.**
                * Politely state that the input isn't a testable hypothesis for this case and ask them to provide a clearer one.
                * Example responses: "I don't have data related to that. Could you propose a specific hypothesis about the potential cause of the issue described in the case?" OR "Could you clarify what specific area you'd like to investigate based on the case details?" OR "Please state a testable hypothesis related to the case."

            **CRITICAL INSTRUCTIONS:**
            - Prioritize providing contradictory information if the input is a reasonable hypothesis.
            - Only resort to asking for a clearer hypothesis if the input is truly not a hypothesis.
            - Do NOT assess the quality of the hypothesis (e.g., don't say "Good idea" or "That's incorrect").
            - Do NOT use ###ANSWER### or ###ASSESSMENT### tags in your response.
            - Do NOT ask clarifying questions back to the candidate.
            - Do NOT solve the case or reveal the true cause.
            - Your entire response must be ONLY the direct text of the contradictory information OR the polite redirection.

            Conversation History (Previous hypotheses and info provided):
            {history_for_prompt}

            Candidate's Latest Hypothesis/Area to Investigate:
            {latest_input}

            Your Response:
            """
            system_message = "You are a case interviewer. If the user provides a reasonable hypothesis, give concise contradictory info. If the input is not a reasonable hypothesis (e.g., nonsensical, vague, irrelevant), politely ask for a clearer, relevant hypothesis. Be neutral, do not assess, do not use special formatting."
            # --- End of Refined Prompt v4 ---
            max_tokens = 150
            temperature = 0.3

        # Analysis, Framework Dev, Recommendation now handle interaction outside send_question
        elif selected_skill in ["Frameworks", "Analysis", "Recommendation"]:
             logger.error(f"send_question called unexpectedly for skill: {selected_skill}")
             interviewer_answer = f"Error: Unexpected interaction for {selected_skill}."
             interviewer_assessment = None
             st.session_state.setdefault(conv_key, []).append({"role": "interviewer", "content": interviewer_answer, "assessment": interviewer_assessment})
             st.session_state[is_typing_key] = False
             st.rerun()
             return

        else:
            # Handle other potential skills or errors
            logger.error(f"Attempted to send question for unhandled skill: {selected_skill}")
            st.error(f"Interaction logic for '{selected_skill}' is not yet implemented.")
            st.session_state.setdefault(conv_key, []).append({"role": "interviewer", "content": f"Sorry, the interaction for '{selected_skill}' is not ready yet.", "assessment": None})
            st.session_state[is_typing_key] = False
            st.rerun()
            return

        # Call LLM API
        # logger.debug(f"LLM Prompt:\n{prompt_for_llm}")
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt_for_llm}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        full_response = ""
        with st.spinner(f"CHIP is processing..."):
             for chunk in response:
                 if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                     full_response += chunk.choices[0].delta.content

        # Parse response based on expected format (skill specific)
        interviewer_answer, interviewer_assessment = parse_interviewer_response(full_response, selected_skill)

        logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - LLM Response: '{interviewer_answer[:100]}...'")
        if interviewer_assessment:
             logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - LLM Assessment: '{interviewer_assessment[:100]}...'")

        # Store the response
        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer",
            "content": interviewer_answer,
            "assessment": interviewer_assessment
        })

        # Check if Hypothesis Formulation limit is reached
        if selected_skill == "Hypothesis" and current_hypothesis_count >= 3: # Use new skill name
            logger.info("Hypothesis limit reached (3). Ending session.")
            st.session_state[done_key] = True
            st.session_state.setdefault(conv_key, []).append({ "role": "interviewer", "content": "(Maximum hypotheses reached. Moving to feedback.)", "assessment": None })

        # Analysis skill ending is handled in its UI function

    except Exception as e:
        logger.exception(f"Error generating LLM response: {e}")
        st.error(f"Error generating response: {e}")
        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer", "content": f"Sorry, an error occurred... ({type(e).__name__})", "assessment": None
        })
    finally:
        st.session_state[is_typing_key] = False
        st.rerun() # Rerun to display new message and potentially the feedback section if done_key was set

def generate_final_feedback(current_case_prompt_text):
    """
    Generates overall feedback markdown based on the conversation history.
    """
    prefix = st.session_state.key_prefix; conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A") # Corrected key
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - Attempting to generate final feedback.")
    existing_feedback = st.session_state.get(feedback_key)
    feedback_submitted = st.session_state.get(feedback_submitted_key, False)
    if feedback_submitted: logger.info("Skipping feedback gen: Feedback already submitted by user."); return existing_feedback
    if existing_feedback is not None: logger.info("Skipping feedback gen: Feedback key exists and is not None."); return existing_feedback

    # Format history based on skill
    history_string = ""
    exhibit_context_for_feedback = "" # For Analysis and Recommendation
    conversation_history = st.session_state.get(conv_key, [])

    if not conversation_history:
        logger.warning("Skipping feedback gen: No conversation history found.")
        return "[Could not generate feedback: No interaction history found]"
    if not isinstance(conversation_history, list):
        logger.error(f"Internal Error: Conversation history format issue. Type: {type(conversation_history)}")
        st.error("Internal Error: Conversation history format issue.")
        st.session_state[feedback_key] = "Error: Could not generate feedback due to history format."
        return st.session_state[feedback_key]

    # Format history differently depending on the skill for the feedback prompt
    formatted_history_parts = []
    if selected_skill == "Frameworks": # Use new skill name
        if conversation_history and conversation_history[0].get("role") == "interviewee":
             history_string = f"Candidate's Submitted Framework:\n{conversation_history[0].get('content', '[Framework not found]')}"
        else:
             logger.warning("Frameworks: Could not extract framework from conversation state.")
             return "[Could not generate feedback: Framework submission not found in state]"
    elif selected_skill == "Hypothesis": # Use new skill name
         for i, msg in enumerate(conversation_history):
            role = msg.get("role"); content = msg.get("content", "[missing content]")
            if role == 'interviewee':
                h_num = (i // 2) + 1
                formatted_history_parts.append(f"Candidate Hypothesis {h_num}: {content}")
            elif role == 'interviewer':
                h_num = (i // 2) + 1
                if "(Maximum hypotheses reached. Moving to feedback.)" not in content:
                    formatted_history_parts.append(f"Interviewer Info Provided after H{h_num}: {content}")
         history_string = "\n\n".join(formatted_history_parts)
    elif selected_skill == "Analysis": # Use new skill name
        analysis_parts = []
        current_prompt_details = get_prompt_details(st.session_state.get(f"{prefix}_current_prompt_id")) # Use full key
        exhibits_data_for_llm = []
        if current_prompt_details and current_prompt_details.get("exhibits"):
            for idx, ex in enumerate(current_prompt_details["exhibits"]):
                ex_title = ex.get("exhibit_title", f"Exhibit {idx+1}")
                ex_desc = ex.get("description", "")
                ex_data_summary = ""
                if ex.get("data"):
                    try:
                        df = pd.DataFrame(ex.get("data"))
                        ex_data_summary = f"Data for {ex_title}:\n{df.to_string(index=False)}\n"
                    except Exception as e:
                        ex_data_summary = f"Data for {ex_title}: Error processing data.\n"
                elif ex.get("summary_text"):
                    ex_data_summary = f"Summary Text for {ex_title}:\n{ex.get('summary_text')}\n"
                exhibits_data_for_llm.append(f"{ex_title}\n{ex_desc}\n{ex_data_summary}")
        exhibit_context_for_feedback = "\n\n".join(exhibits_data_for_llm)

        for i, msg in enumerate(conversation_history):
             if msg.get("role") == "interviewee":
                 analysis_parts.append(f"Candidate's Analysis for Exhibit {len(analysis_parts) + 1}:\n{msg.get('content', '[Analysis not found]')}")
        history_string = "\n\n---\n\n".join(analysis_parts)
        if not history_string:
             logger.warning("Analysis: Could not extract analysis from conversation state.")
             return "[Could not generate feedback: Analysis not found in state]"
    elif selected_skill == "Recommendation": # Use new skill name
        current_prompt_details = get_prompt_details(st.session_state.get(f"{prefix}_current_prompt_id")) # Use full key
        exhibits_data_for_llm = []
        if current_prompt_details and current_prompt_details.get("exhibits"):
            for idx, ex in enumerate(current_prompt_details["exhibits"]):
                ex_title = ex.get("exhibit_title", f"Exhibit {idx+1}")
                ex_desc = ex.get("description", "")
                ex_data_summary = ""
                if ex.get("data"):
                    try:
                        df = pd.DataFrame(ex.get("data"))
                        ex_data_summary = f"Data for {ex_title}:\n{df.to_string(index=False)}\n"
                    except Exception as e:
                        ex_data_summary = f"Data for {ex_title}: Error processing data.\n"
                elif ex.get("summary_text"):
                     summary_text_content = ex.get("summary_text")
                     if isinstance(summary_text_content, list):
                         ex_data_summary = f"Summary Text for {ex_title}:\n" + "\n".join([f"- {item}" for item in summary_text_content]) + "\n"
                     else:
                         ex_data_summary = f"Summary Text for {ex_title}:\n{summary_text_content}\n"
                exhibits_data_for_llm.append(f"{ex_title}\n{ex_desc}\n{ex_data_summary}")
        exhibit_context_for_feedback = "\n\n".join(exhibits_data_for_llm)

        if conversation_history and conversation_history[0].get("role") == "interviewee":
             history_string = f"Candidate's Submitted Recommendation:\n{conversation_history[0].get('content', '[Recommendation not found]')}"
        else:
             logger.warning("Recommendation: Could not extract recommendation from conversation state.")
             return "[Could not generate feedback: Recommendation submission not found in state]"
    else: # For Clarifying Questions
        for i, msg in enumerate(conversation_history):
            role = msg.get("role"); content = msg.get("content", "[missing content]"); q_num = (i // 2) + 1
            if role == 'interviewee': formatted_history_parts.append(f"Interviewee Input {q_num}: {content}")
            elif role == 'interviewer':
                formatted_history_parts.append(f"Interviewer Response to Input {q_num}: {content}")
                assessment = msg.get('assessment')
                if assessment: formatted_history_parts.append(f" -> Interviewer's Assessment of Input {q_num}: {assessment}")
        history_string = "\n\n".join(formatted_history_parts)

    if not history_string:
         logger.warning("Skipping feedback gen: Formatted history string is empty.")
         return "[Could not generate feedback: Formatted history is empty]"

    logger.debug(f"Generating feedback for {selected_skill}. History string:\n{history_string}")
    if exhibit_context_for_feedback:
        logger.debug(f"Exhibit context for feedback:\n{exhibit_context_for_feedback}")


    with st.spinner(f"Generating Final Feedback for {selected_skill}..."):
        try:
            # --- Define Feedback Prompt based on Skill ---
            feedback_prompt = ""
            system_message_feedback = ""
            max_tokens_feedback = 800 # Default

            if selected_skill == "Clarifying": # Use new skill name
                # --- Refined Clarifying Feedback Prompt v2 ---
                feedback_prompt = f"""
                You are an experienced case interview coach providing feedback on the clarifying questions phase ONLY.
                The candidate has finished asking questions. You must now provide overall feedback.

                Case Prompt Context for this Session:
                {current_case_prompt_text}

                Interview Interaction History (User questions, your answers as INTERVIEWER, and your per-question assessments):
                {history_string}

                Your Task:
                Provide detailed, professional, and direct feedback on the interviewee's clarifying questions phase based *only* on the interaction history provided. Use markdown formatting effectively, including paragraph breaks for readability.

                **IMPORTANT: Your response MUST start *directly* with the "## Overall Rating:" heading on the first line. Do not include any introductory phrases like "Sure, here's the feedback..." or any text before this heading. Your entire response must strictly follow the specified markdown structure.**

                Structure your feedback precisely as follows using Markdown:

                ## Overall Rating: [1-5]/5
                *(Provide a brief justification for the rating here, referencing the conversation specifics or assessments. Be very critical and use the full range of scores based on the criteria below. Critically consider the number and quality of questions asked in relation to the case complexity and the information already provided in the case prompt or prior answers.)*

                ---

                1.  **Overall Summary:** Briefly summarize the interviewee's performance in asking clarifying questions for *this specific case context*.

                2.  **Strengths:** Identify 1-2 specific strengths demonstrated (e.g., good initial questions, logical flow, conciseness). Refer to specific question numbers or assessments if possible.

                3.  **Areas for Improvement:** Identify 1-2 key areas where the interviewee could improve (e.g., question relevance, depth, avoiding compound questions, structure, digging deeper based on answers, asking redundant questions). Refer to specific question numbers or assessments.

                4.  **Actionable Next Steps:** Provide at least two concrete, actionable steps the interviewee can take to improve their clarifying questions skills *for future cases*.

                5.  **Example Questions:** For *each* actionable next step that relates to the *content* or *quality* of the questions asked, provide 1-2 specific *alternative* example questions the interviewee *could have asked* in *this case* to demonstrate improvement in that area.

                **Rating Criteria Reference (Apply Strictly):**
                    * 1: **Must use this score** if questions were predominantly vague (like single words), irrelevant, unclear, compound, or demonstrated a fundamental lack of understanding of how to clarify effectively. Added little to no value. Insufficient number of questions for the case complexity, or questions were mostly redundant.
                    * 2: Significant issues remain. Many questions were poor, with only occasional relevant ones, or showed a consistent lack of focus/structure. May have asked too few questions or many redundant ones.
                    * 3: A mixed bag. Some decent questions fitting the ideal categories (Objective, Company, Terms, Repetition) but also notable lapses in quality, relevance, or efficiency. Number of questions might be borderline or some redundancy.
                    * 4: Generally strong performance. Most questions were relevant, clear, targeted, and fit the ideal categories. Good progress made in clarifying the case, with only minor areas for refinement. Sufficient number of quality questions.
                    * 5: Excellent. Consistently high-quality questions that were relevant, concise, targeted, and demonstrated a strong grasp of the ideal clarifying categories. Effectively and efficiently clarified key aspects of the case prompt. Comprehensive and insightful questioning.
                   *(Remember to consider the per-question assessments provided in the history when assigning the overall rating.)*

                Ensure your response does **not** start with any other title. Start directly with the '## Overall Rating:' heading. Use paragraph breaks between sections.
                """
                system_message_feedback = "You are an expert case interview coach providing structured feedback on clarifying questions. IMPORTANT: Start your response *directly* with the '## Overall Rating:' heading. Evaluate critically based on history and assessments, including the number and quality of questions. Use markdown effectively for readability."
                # --- End of Refined Clarifying Feedback Prompt v2 ---
                max_tokens_feedback = 800

            elif selected_skill == "Frameworks": # Use new skill name
                 # --- Refined Framework Feedback Prompt v2 ---
                 feedback_prompt = f"""
                 You are an experienced case interview coach providing final summary feedback on the framework development phase based on a single framework submission.

                 Case Prompt Context for this Session:
                 {current_case_prompt_text}

                 Candidate's Submitted Framework:
                 {history_string}

                 Your Task:
                 Provide detailed, professional, final feedback on the candidate's submitted framework. Use markdown formatting effectively.

                 **IMPORTANT: Your response MUST start *directly* with the "## Overall Framework Rating:" heading on the first line. Do not include any introductory phrases like "Sure, here's the feedback..." or any text before this heading. Your entire response must strictly follow the specified markdown structure.**

                 Structure your feedback precisely as follows using Markdown, starting DIRECTLY with the rating heading:

                 ## Overall Framework Rating: [1-5]/5
                 *(Provide a brief justification for the rating here, considering the quality of the submitted framework based on MECE, Relevance, Prioritization, Actionability, and Clarity criteria below)*

                 ---

                 1.  **Overall Summary:** Summarize the effectiveness and quality of the proposed framework for tackling *this specific case*. Did the candidate create a solid structure?

                 2.  **Strengths:** Identify 1-2 specific strengths of the submitted framework (e.g., good structure, relevant buckets, clear logic).

                 3.  **Areas for Improvement:** Identify 1-2 key weaknesses or areas for development based on the submitted framework (e.g., not MECE, missing key drivers from the prompt, poor prioritization, too generic, structure unclear).

                 4.  **Actionable Next Steps:** Provide at least two concrete, actionable steps the candidate can take to improve their framework development skills *for future cases*.

                 5.  **Example Refinement / Alternative:** Suggest one specific, significant refinement to the submitted framework *or* propose a concise alternative structure that might have been more effective for *this case*, explaining why briefly.


                 **Rating Criteria Reference:**
                 * 1: **Fundamentally flawed.** Not MECE, irrelevant to the case, unclear structure, unusable for analysis. Little understanding shown.
                 * 2: **Major issues.** Significant gaps or overlaps (not MECE), poor structure, lacks relevance to key case issues, unclear or difficult to follow.
                 * 3: **Partially effective.** Some relevant components, but structure could be significantly improved (e.g., not fully MECE, poor prioritization, some irrelevant buckets). Shows basic understanding but needs refinement.
                 * 4: **Good framework.** Mostly MECE, relevant to the case, actionable, and reasonably prioritized. Structure is clear. Only minor refinements possible.
                 * 5: **Excellent.** Clear, MECE, highly relevant to the core issues, well-prioritized, actionable, and tailored effectively to the case specifics. Demonstrates strong strategic thinking.

                 Ensure your response does **not** start with any other title besides "## Overall Framework Rating:". Use paragraph breaks between sections.
                 """
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on framework development based on a single submission. IMPORTANT: Start your response *directly* with the '## Overall Framework Rating:' heading. Evaluate critically based on the submitted framework. Use markdown effectively."
                 # --- End of Refined Framework Feedback Prompt v2 ---
                 max_tokens_feedback = 700

            elif selected_skill == "Hypothesis": # Use new skill name
                 # --- Refined Hypothesis Feedback Prompt ---
                 feedback_prompt = f"""
                 You are an experienced case interview coach providing final summary feedback on the hypothesis formulation phase.
                 The candidate attempted to form hypotheses, and you (as the interviewer) provided contradictory information after each attempt.

                 Case Prompt Context for this Session:
                 {current_case_prompt_text}

                 Interaction History (Candidate hypotheses and info provided by interviewer):
                 {history_string}

                 Your Task:
                 Provide detailed, professional, final feedback on the candidate's overall performance during the hypothesis formulation process based *only* on the interaction history. Use markdown formatting effectively.

                 **IMPORTANT: Your response MUST start *directly* with the "## Overall Hypothesis Formulation Rating:" heading on the first line. Do not include any introductory phrases like "Sure, here's the feedback..." or any text before this heading. Your entire response must strictly follow the specified markdown structure.**

                 Structure your feedback precisely as follows using Markdown, starting DIRECTLY with the rating heading:

                 ## Overall Hypothesis Formulation Rating: [1-5]/5
                 *(Provide a brief justification for the rating here, considering the quality, logic, and relevance of the hypotheses, and how well the candidate adapted to the new information provided. Use the criteria below)*

                 ---

                 1.  **Overall Summary:** Briefly summarize the candidate's approach to formulating and refining hypotheses in response to the information provided.

                 2.  **Strengths:** Identify 1-2 specific strengths demonstrated (e.g., logical initial hypothesis, good adaptation to new data, clear articulation, relevant focus areas). Refer to specific hypothesis numbers (H1, H2, H3).

                 3.  **Areas for Improvement:** Identify 1-2 key weaknesses (e.g., initial hypothesis too broad/narrow, poor adaptation to contradictory info, illogical jumps, sticking too long to a disproven path, unclear articulation). Refer to specific hypothesis numbers.

                 4.  **Actionable Next Steps:** Provide at least two concrete, actionable steps the candidate can take to improve their hypothesis generation and testing skills *for future cases*.


                 **Rating Criteria Reference:**
                 * 1: Poor. Hypotheses were illogical, irrelevant, or candidate failed completely to adapt to new information.
                 * 2: Weak. Significant issues with hypothesis logic/relevance, or very slow/poor adaptation to contradictory data.
                 * 3: Fair. Some logical hypotheses but notable weaknesses in structure, relevance, or adaptation. Mixed performance.
                 * 4: Good. Generally logical and relevant hypotheses, demonstrated reasonable adaptation to new information with only minor areas for improvement.
                 * 5: Excellent. Consistently logical, relevant, well-articulated hypotheses. Showed strong ability to adapt and pivot based on new information effectively.

                 Ensure your response does **not** start with any other title besides "## Overall Hypothesis Formulation Rating:". Use paragraph breaks between sections.
                 """
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on hypothesis formulation. IMPORTANT: Start your response *directly* with the '## Overall Hypothesis Formulation Rating:' heading. Evaluate critically based on the interaction history. Use markdown effectively."
                 # --- End of Refined Hypothesis Feedback Prompt ---
                 max_tokens_feedback = 700

            elif selected_skill == "Analysis": # Use new skill name
                 feedback_prompt = f"""... [Analysis Feedback Prompt as before - Rating First] ..."""
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on exhibit analysis..."
                 max_tokens_feedback = 800

            elif selected_skill == "Recommendation": # Use new skill name
                 # --- Refined Recommendation Final Feedback Prompt ---
                 feedback_prompt = f"""
                 You are an experienced case interview coach providing final summary feedback on the Recommendation phase.
                 The candidate was presented with a case prompt and summary findings/exhibits and submitted their final recommendation.

                 Case Prompt Context for this Session:
                 {current_case_prompt_text}

                 Summary of Exhibits/Key Findings Provided to Candidate:
                 {exhibit_context_for_feedback}

                 Candidate's Submitted Recommendation:
                 {history_string}

                 Your Task:
                 Provide detailed, professional, final feedback on the candidate's submitted recommendation. Evaluate the structure (Pyramid Principle), synthesis of information (from case prompt and provided exhibits/findings), clarity, and inclusion of risks and next steps. Use markdown formatting effectively.

                 **IMPORTANT: Your response MUST start *directly* with the "## Overall Recommendation Rating:" heading on the first line. Do not include any introductory phrases like "Sure, here's the feedback..." or any text before this heading. Your entire response must strictly follow the specified markdown structure.**

                 Structure your feedback precisely as follows using Markdown:

                 ## Overall Recommendation Rating: [1-5]/5
                 *(Provide a brief justification for the rating here, considering the quality criteria below based on the candidate's recommendation and the provided case/exhibit context)*

                 ---

                 1.  **Structure (Pyramid Principle):** Did the recommendation start with a clear conclusion/answer to the main case question? Was it followed by logical supporting rationale and evidence (implicitly or explicitly referencing the provided exhibits/findings)?

                 2.  **Synthesis & Logic:** How well did the candidate synthesize the information from the case prompt and provided exhibits/findings to arrive at their recommendation? Was the rationale sound and logical?

                 3.  **Risks & Next Steps:** Did the candidate appropriately identify potential risks associated with their recommendation? Were the proposed next steps relevant and actionable?

                 4.  **Clarity & Conciseness:** Was the recommendation communicated clearly, professionally, and concisely?

                 5.  **Actionable Next Steps (for the candidate):** Provide at least two concrete, actionable steps the candidate can take to improve their recommendation structuring and delivery skills *for future cases*.


                 **Rating Criteria Reference:**
                 * 1: Poor. Recommendation missing or completely off-base. No clear structure, risks/next steps missing. Poor synthesis.
                 * 2: Weak. Unclear conclusion or weak rationale. Poor structure (e.g., no Pyramid Principle). Risks/steps generic or missing. Weak synthesis.
                 * 3: Fair. Recommendation addresses the prompt but structure could be better. Rationale is present but may lack depth or clear link to data. Risks/steps are basic. Adequate synthesis.
                 * 4: Good. Clear recommendation, mostly follows structure. Good synthesis of information. Relevant risks and next steps identified. Generally clear language.
                 * 5: Excellent. Clear, concise, actionable recommendation following Pyramid Principle. Strong synthesis of case facts/exhibits. Insightful risks and concrete next steps. Professional delivery.

                 Ensure your response does **not** start with any other title besides "## Overall Recommendation Rating:". Use paragraph breaks between sections.
                 """
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on a final case recommendation. IMPORTANT: Start your response *directly* with the '## Overall Recommendation Rating:' heading. Evaluate structure, synthesis of provided information, risks, and next steps. Use markdown effectively."
                 # --- End of Refined Recommendation Final Feedback Prompt ---
                 max_tokens_feedback = 800

            else:
                logger.error(f"Cannot generate feedback for unhandled skill: {selected_skill}")
                st.error(f"Feedback generation for '{selected_skill}' is not yet implemented.")
                st.session_state[feedback_key] = f"Error: Feedback generation not implemented for {selected_skill}."
                return st.session_state[feedback_key]

            logger.info("Calling OpenAI API for final feedback...")
            # --- Add Debug Logging ---
            logger.debug(f"Feedback Prompt for {selected_skill}:\n{feedback_prompt}")
            # --- End Debug Logging ---
            feedback_response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_message_feedback}, {"role": "user", "content": feedback_prompt}], max_tokens=max_tokens_feedback, temperature=0.5)
            feedback = feedback_response.choices[0].message.content.strip()
            # --- Add Debug Logging ---
            logger.info(f"Raw feedback received from API (first 500 chars): {feedback[:500]}")
            # --- End Debug Logging ---
            if feedback: st.session_state[feedback_key] = feedback
            else: logger.warning("LLM returned empty feedback."); st.session_state[feedback_key] = "[Feedback generation returned empty]"
            return st.session_state[feedback_key]
        except Exception as e:
            logger.exception(f"Error during feedback generation API call: {e}")
            st.error(f"Could not generate feedback. Error: {e}")
            st.session_state[feedback_key] = f"Error generating feedback: {type(e).__name__}"
            return st.session_state[feedback_key]

# --- Main Streamlit Application Function ---
def main_app():
    # [ Code remains unchanged ]
    st.title("CHIP")
    logger.info("Main application UI rendered.")
    prefix = st.session_state.key_prefix
    skill_key = f"{prefix}_selected_skill"
    with st.sidebar:
        st.subheader("Support CHIP!")
        st.markdown("Love CHIP? Your support helps keep this tool free and improving! 🙏\n\nConsider making a small donation to help with server and API costs.")
        donate_url = "https://buymeacoffee.com/9611"
        st.link_button("Buy Me a Coffee ☕", donate_url)
        st.divider()
    st.write("Select Skill to Practice:")
    cols_row1 = st.columns(3); cols_row2 = st.columns(3)
    current_selection = st.session_state.get(skill_key, SKILLS[0])
    def handle_skill_click(skill_name):
        if skill_name != st.session_state.get(skill_key): logger.info(f"Skill selected: {skill_name}"); st.session_state[skill_key] = skill_name; reset_skill_state(); st.rerun()
        else: logger.debug(f"Clicked already selected skill: {skill_name}")
    button_map = {SKILLS[0]: cols_row1[0], SKILLS[1]: cols_row1[1], SKILLS[2]: cols_row1[2], SKILLS[3]: cols_row2[0], SKILLS[4]: cols_row2[1]}
    for skill, col in button_map.items():
        with col:
            button_type = "primary" if skill == current_selection else "secondary"
            if st.button(skill, key=f"skill_btn_{skill.replace(' ', '_')}", use_container_width=True, type=button_type): handle_skill_click(skill)
    st.divider()
    selected_skill = st.session_state.get(skill_key, SKILLS[0])
    logger.debug(f"Loading UI for skill: {selected_skill}")
    if selected_skill == "Clarifying": clarifying_questions_bot_ui()
    elif selected_skill == "Frameworks": framework_development_ui()
    elif selected_skill == "Hypothesis": hypothesis_formulation_ui()
    elif selected_skill == "Analysis": analysis_ui()
    elif selected_skill == "Recommendation": recommendation_ui()
    else: logger.error(f"Invalid skill selected: {selected_skill}"); st.error("Invalid skill selected.")

# --- Skill-Specific UI Functions (clarifying_questions_bot_ui, framework_development_ui, hypothesis_formulation_ui, analysis_ui) ---

def clarifying_questions_bot_ui():
    # [ Code remains unchanged ]
    logger.info("Loading Clarifying Questions UI.")
    prefix = st.session_state.key_prefix
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)
    st.markdown("Read the prompt below, then enter your clarifying questions one at a time in the chat field at the bottom of the page. Press \"Send\" to submit a clarifying question. When you are satisfied with your questions, press the \"End Clarification Questions\" button.")
    st.divider()
    if st.session_state.get(current_prompt_id_key) is None: logger.info("No current prompt ID, selecting new one."); selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt: logger.error(f"Could not load details for prompt ID: {st.session_state.get(current_prompt_id_key)}"); st.error("Could not load the current case prompt details..."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt: {case_title}")
    if not st.session_state.get(done_key):
        st.header("Clarifying Questions")
        chat_container = st.container()
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role"); display_role = "user" if role == "interviewee" else "assistant"
                     with st.chat_message(display_role): st.markdown(msg.get("content", ""))
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key): typing_placeholder.text("CHIP is thinking...")
        else: typing_placeholder.empty()
        with st.form(key=f"{prefix}_cq_input_form", clear_on_submit=True):
             user_question = st.text_input("Type your question here:", key=f"{prefix}_cq_form_text_input", disabled=st.session_state.get(is_typing_key, False), label_visibility="collapsed", placeholder="Type your question...")
             submitted = st.form_submit_button("Send", disabled=st.session_state.get(is_typing_key, False))
             if submitted and user_question: logger.debug(f"Form submitted with question: '{user_question}'"); send_question(user_question, case_prompt_text)
        st.write(" ")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            if st.button("End Clarification Questions", use_container_width=True):
                logger.info("User clicked 'End Clarification Questions'.")
                end_time = time.time(); start_time = st.session_state.get(start_time_key)
                if start_time is not None: st.session_state[time_key] = end_time - start_time
                else: st.session_state[time_key] = 0.0
                st.session_state[done_key] = True
                current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                st.session_state[run_count_key] = current_session_run_count
                logger.info(f"Session run count incremented to: {current_session_run_count}")
                st.rerun()
        if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Interaction timer started.")
    if st.session_state.get(done_key):
        logger.debug("Entering feedback and conclusion area.")
        final_feedback_content = generate_final_feedback(case_prompt_text)
        # --- FIX: Check for specific Clarifying feedback heading ---
        feedback_was_generated = final_feedback_content and isinstance(final_feedback_content, str) and final_feedback_content.strip().startswith("## Overall Rating:")
        logger.debug(f"Clarifying feedback content: {final_feedback_content}")
        logger.debug(f"Clarifying feedback_was_generated: {feedback_was_generated}")
        # --- End FIX ---
        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0); st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'): st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                st.markdown("**How helpful was the feedback provided above? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_cq_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"): selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked rating: {selected_rating} stars.")
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        if save_user_feedback(user_feedback_data): logger.info("User Feedback Auto-Submitted (Rating >= 4) and saved."); st.rerun()
                        else: logger.error("User Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                    else: st.session_state[show_comment_key] = True
                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(f"Comment for your {rating_display} rating:", key=f"{prefix}_cq_feedback_comment_input", placeholder="...")
                    if st.button("Submit Rating and Comment", key=f"{prefix}_cq_submit_feedback_button"):
                        if not feedback_comment.strip(): st.error("Comment cannot be empty...")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0: st.error("Invalid rating selected...")
                        else:
                            user_feedback_data = {"rating": current_rating_value, "comment": feedback_comment.strip(), "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                            st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                            if save_user_feedback(user_feedback_data): logger.info("User Feedback Submitted with Comment and saved."); st.rerun()
                            else: logger.error("User Feedback Submitted with Comment but FAILED TO SAVE.")
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable or was not generated correctly."); logger.warning(f"Clarifying feedback was not displayed. Content: {final_feedback_content}")
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds**...")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_cq_practice_again"): logger.info("User clicked 'Practice This Skill Again' for Clarifying Questions."); reset_skill_state(); st.rerun()


def framework_development_ui():
    # [ Code remains unchanged ]
    logger.info("Loading Framework Development UI.")
    prefix = st.session_state.key_prefix
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)
    st.markdown("Read the case prompt below. Take some time to think, then outline your framework and proposed approach in the framework area below. When you are satisfied with your framework, press \"Submit Framework for Feedback\".")
    st.divider()
    if st.session_state.get(current_prompt_id_key) is None: logger.info("No current prompt ID (Framework Dev), selecting new one."); selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt: logger.error(f"Could not load details for prompt ID (Framework Dev): {st.session_state.get(current_prompt_id_key)}"); st.error("Could not load the current case prompt details..."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt (Framework Dev): {case_title}")
    if not st.session_state.get(done_key):
        st.header("Develop Your Framework");
        with st.form(key=f"{prefix}_fw_input_form", clear_on_submit=False):
             framework_input = st.text_area("Enter your framework here:", height=200, key=f"{prefix}_fw_form_text_area", disabled=st.session_state.get(is_typing_key, False), placeholder="e.g.,\n1. Market Analysis...")
             # --- FIX: Corrected disabled logic ---
             submitted = st.form_submit_button("Submit Framework for Feedback", disabled=st.session_state.get(is_typing_key, False))
             # --- End FIX ---
             if submitted and framework_input:
                 logger.info("User submitted framework for final feedback.")
                 st.session_state[conv_key] = [{"role": "interviewee", "content": framework_input}]
                 st.session_state[done_key] = True
                 if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Framework interaction timer started on submit.")
                 end_time = time.time(); start_time = st.session_state.get(start_time_key)
                 if start_time is not None: st.session_state[time_key] = end_time - start_time
                 else: st.session_state[time_key] = 0.0
                 current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                 st.session_state[run_count_key] = current_session_run_count
                 logger.info(f"Session run count incremented to: {current_session_run_count} (Framework Dev)")
                 st.rerun()
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key) or (st.session_state.get(done_key) and not st.session_state.get(feedback_key)): typing_placeholder.text("CHIP is analyzing your framework...")
        else: typing_placeholder.empty()
    if st.session_state.get(done_key):
        logger.debug("Entering framework feedback and conclusion area.")
        st.session_state[is_typing_key] = True
        final_feedback_content = generate_final_feedback(case_prompt_text)
        st.session_state[is_typing_key] = False
        # --- FIX: Check for specific Frameworks feedback heading ---
        feedback_was_generated = final_feedback_content and isinstance(final_feedback_content, str) and final_feedback_content.strip().startswith("## Overall Framework Rating:")
        logger.debug(f"Framework feedback content: {final_feedback_content}")
        logger.debug(f"Framework feedback_was_generated: {feedback_was_generated}")
        # --- End FIX ---
        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0); st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'): st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                st.markdown("**How helpful was the overall framework feedback? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_fw_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"): selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked framework feedback rating: {selected_rating} stars.")
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        if save_user_feedback(user_feedback_data): logger.info("User Framework Feedback Auto-Submitted (Rating >= 4) and saved."); st.rerun()
                        else: logger.error("User Framework Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                    else: st.session_state[show_comment_key] = True
                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(f"Comment for your {rating_display} rating:", key=f"{prefix}_fw_feedback_comment_input", placeholder="...")
                    if st.button("Submit Rating and Comment", key=f"{prefix}_fw_submit_feedback_button"):
                        if not feedback_comment.strip(): st.error("Comment cannot be empty...")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0: st.error("Invalid rating selected...")
                        else:
                            user_feedback_data = {"rating": current_rating_value, "comment": feedback_comment.strip(), "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                            st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                            if save_user_feedback(user_feedback_data): logger.info("User Framework Feedback Submitted with Comment and saved."); st.rerun()
                            else: logger.error("User Framework Feedback Submitted with Comment but FAILED TO SAVE.")
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable or was not generated correctly."); logger.warning(f"Framework feedback was not displayed. Content: {final_feedback_content}")
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** developing the framework for this case.")
        logger.info(f"Displayed framework conclusion. Total time: {total_interaction_time:.2f}s")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_fw_practice_again"): logger.info("User clicked 'Practice This Skill Again' for Framework Development."); reset_skill_state(); st.rerun()


# --- NEW: Skill-Specific UI Function (Hypothesis Formulation) ---
def hypothesis_formulation_ui():
    # [ Code remains unchanged ]
    logger.info("Loading Hypothesis Formulation UI.")
    prefix = st.session_state.key_prefix
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    hypothesis_count_key = f"{prefix}_hypothesis_count"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)
    init_session_state_key('hypothesis_count', 0)
    st.markdown("Read the case prompt below. Formulate an initial hypothesis about the core issue and state what you'd like to investigate first. Enter it in the text field below and press \"Send\". CHIP will provide information based on your hypothesis. Refine your hypothesis based on the information provided (up to 3 hypotheses total). Click \"End Hypothesis Formulation\" when finished.")
    st.divider()
    if st.session_state.get(current_prompt_id_key) is None: logger.info("No current prompt ID (Hypothesis), selecting new one."); selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt: logger.error(f"Could not load details for prompt ID (Hypothesis): {st.session_state.get(current_prompt_id_key)}"); st.error("Could not load the current case prompt details..."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt (Hypothesis): {case_title}")
    if not st.session_state.get(done_key):
        st.header("Hypothesis Formulation")
        chat_container = st.container()
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role"); display_role = "user" if role == "interviewee" else "assistant"
                     label = "Your Hypothesis" if role == "interviewee" else "Interviewer Information"
                     with st.chat_message(display_role): st.markdown(msg.get("content", ""))
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key): typing_placeholder.text("CHIP is processing...")
        else: typing_placeholder.empty()
        hypothesis_count = st.session_state.get(hypothesis_count_key, 0)
        if hypothesis_count < 3:
            with st.form(key=f"{prefix}_hf_input_form", clear_on_submit=True):
                 user_hypothesis = st.text_area(f"Enter Hypothesis #{hypothesis_count + 1}:", key=f"{prefix}_hf_form_text_area", height=100, disabled=st.session_state.get(is_typing_key, False), label_visibility="visible", placeholder=f"State hypothesis {hypothesis_count + 1} and what you want to investigate...")
                 submitted = st.form_submit_button("Submit Hypothesis", disabled=st.session_state.get(is_typing_key, False))
                 if submitted and user_hypothesis: logger.debug(f"Form submitted with hypothesis {hypothesis_count + 1}: '{user_hypothesis}'"); send_question(user_hypothesis, case_prompt_text)
        else: st.info("Maximum number of hypotheses reached. Click below to get feedback or start over.")
        st.write(" ")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            if st.button("End Hypothesis Formulation", use_container_width=True):
                logger.info("User clicked 'End Hypothesis Formulation'.")
                end_time = time.time(); start_time = st.session_state.get(start_time_key)
                if start_time is not None: st.session_state[time_key] = end_time - start_time
                else: st.session_state[time_key] = 0.0
                st.session_state[done_key] = True
                current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                st.session_state[run_count_key] = current_session_run_count
                logger.info(f"Session run count incremented to: {current_session_run_count} (Hypothesis)")
                st.rerun()
        if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Interaction timer started.")
    if st.session_state.get(done_key):
        logger.debug("Entering hypothesis feedback and conclusion area.")
        st.session_state[is_typing_key] = True
        final_feedback_content = generate_final_feedback(case_prompt_text)
        st.session_state[is_typing_key] = False
        logger.debug(f"Value returned by generate_final_feedback: '{final_feedback_content}'")
        feedback_was_generated = final_feedback_content and isinstance(final_feedback_content, str) and final_feedback_content.strip().startswith("## Overall Hypothesis Formulation Rating:")
        logger.debug(f"Feedback generated flag evaluated as: {feedback_was_generated}")
        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0); st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'): st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                st.markdown("**How helpful was the feedback provided above? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_hf_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"): selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked rating: {selected_rating} stars.")
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        if save_user_feedback(user_feedback_data): logger.info("User Feedback Auto-Submitted (Rating >= 4) and saved."); st.rerun()
                        else: logger.error("User Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                    else: st.session_state[show_comment_key] = True
                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(f"Comment for your {rating_display} rating:", key=f"{prefix}_hf_feedback_comment_input", placeholder="...")
                    if st.button("Submit Rating and Comment", key=f"{prefix}_hf_submit_feedback_button"):
                        if not feedback_comment.strip(): st.error("Comment cannot be empty...")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0: st.error("Invalid rating selected...")
                        else:
                            user_feedback_data = {"rating": current_rating_value, "comment": feedback_comment.strip(), "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                            st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                            if save_user_feedback(user_feedback_data): logger.info("User Feedback Submitted with Comment and saved."); st.rerun()
                            else: logger.error("User Feedback Submitted with Comment but FAILED TO SAVE.")
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}"); logger.error(f"Feedback generation resulted in error message: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable or was not generated correctly."); logger.warning(f"Feedback was not displayed. Content: {final_feedback_content}")
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** in the hypothesis formulation phase.")
        logger.info(f"Displayed hypothesis conclusion. Total time: {total_interaction_time:.2f}s")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_hf_practice_again"): logger.info("User clicked 'Practice This Skill Again' for Hypothesis Formulation."); reset_skill_state(); st.rerun()


# --- NEW: Skill-Specific UI Function (Analysis) ---
def analysis_ui():
    # [ Code remains unchanged ]
    logger.info("Loading Analysis UI.")
    prefix = st.session_state.key_prefix
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count" # Ensure current_prompt_id_key is defined
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    analysis_input_key = f"{prefix}_analysis_input"; current_exhibit_index_key = f"{prefix}_current_exhibit_index"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None) # Ensure current_prompt_id is initialized
    init_session_state_key('analysis_input', ""); init_session_state_key(current_exhibit_index_key, 0)
    st.markdown("Read the case prompt and examine the exhibit(s) below. Analyze the data presented in the exhibit(s) and explain its significance in relation to the case problem. Enter your analysis in the text area below and click \"Submit Analysis\" to get feedback.")
    st.divider()
    if st.session_state.get(current_prompt_id_key) is None: logger.info("No current prompt ID (Analysis), selecting new one."); selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt or current_prompt.get("skill_type") != "Analysis":
        logger.warning(f"Invalid or missing prompt for Analysis skill. Prompt ID: {st.session_state.get(current_prompt_id_key)}. Selecting new.")
        selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
        current_prompt = get_prompt_details(selected_id)
        if not current_prompt or current_prompt.get("skill_type") != "Analysis": logger.error(f"Still could not load a valid Analysis prompt. Last ID: {selected_id}"); st.error("Could not load a valid Analysis prompt. Please try selecting the skill again or check prompts.json."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed Analysis prompt: {case_title}")
    exhibits = current_prompt.get("exhibits", [])
    current_index = st.session_state.get(current_exhibit_index_key, 0)
    total_exhibits = len(exhibits)
    if not exhibits:
        st.warning("No exhibits found for this analysis prompt.")
        if not st.session_state.get(done_key): st.session_state[done_key] = True; st.rerun()
    elif current_index < total_exhibits:
        exhibit = exhibits[current_index]
        st.header(f"Exhibit {current_index + 1} of {total_exhibits}")
        st.subheader(exhibit.get("exhibit_title", f"Exhibit {current_index + 1}"))
        if exhibit.get("description"): st.caption(exhibit.get("description"))
        chart_type = exhibit.get("chart_type", "unknown"); data = exhibit.get("data")
        if data:
            try:
                df = pd.DataFrame(data); fig = None
                if chart_type == "bar":
                    x_col = exhibit.get("x_axis"); y_cols = exhibit.get("y_axis")
                    if x_col and y_cols:
                        if not isinstance(y_cols, list): y_cols = [y_cols]
                        fig = px.bar(df, x=x_col, y=y_cols, title="", barmode='group'); fig.update_layout(legend_title_text='')
                    else: st.warning(f"Exhibit {current_index + 1}: Bar chart data needs 'x_axis' and 'y_axis' keys.")
                elif chart_type == "line":
                    x_col = exhibit.get("x_axis"); y_cols = exhibit.get("y_axis")
                    if x_col and y_cols:
                        if not isinstance(y_cols, list): y_cols = [y_cols]
                        fig = px.line(df, x=x_col, y=y_cols, title=""); fig.update_layout(legend_title_text='')
                    else: st.warning(f"Exhibit {current_index + 1}: Line chart data needs 'x_axis' and 'y_axis' keys.")
                elif chart_type == "pie":
                    names_col = exhibit.get("names"); values_col = exhibit.get("values")
                    if names_col and values_col: fig = px.pie(df, names=names_col, values=values_col, title="")
                    else: st.warning(f"Exhibit {current_index + 1}: Pie chart data needs 'names' and 'values' keys.")
                elif chart_type == "scatter":
                    x_col = exhibit.get("x_axis"); y_col = exhibit.get("y_axis")
                    if x_col and y_col: color_col = exhibit.get("color"); size_col = exhibit.get("size"); fig = px.scatter(df, x=x_col, y=y_col, title="", color=color_col, size=size_col)
                    else: st.warning(f"Exhibit {current_index + 1}: Scatter chart data needs 'x_axis' and 'y_axis' keys.")
                elif chart_type == "table": st.dataframe(df, hide_index=True); fig = None
                else: st.warning(f"Exhibit {current_index + 1}: Unsupported or unspecified chart type '{chart_type}'. Displaying table."); st.dataframe(df, hide_index=True); fig = None
                if fig: fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=400); st.plotly_chart(fig, use_container_width=True)
            except Exception as e: logger.error(f"Error processing exhibit {current_index + 1} data: {e}"); st.error(f"Error displaying exhibit {current_index + 1}.")
        else: st.warning(f"Exhibit {current_index + 1}: No data found.")
        st.header(f"Your Analysis (Exhibit {current_index + 1})")
        with st.form(key=f"{prefix}_an_input_form_{current_index}", clear_on_submit=True):
             analysis_input = st.text_area(f"Enter your analysis for Exhibit {current_index + 1}:", height=200, key=f"{prefix}_an_form_text_area_{current_index}", disabled=st.session_state.get(is_typing_key, False), placeholder="Based on this exhibit, I observe...")
             button_label = "Submit Analysis & Next Exhibit" if current_index < total_exhibits - 1 else "Submit Final Analysis & Get Feedback"
             # --- FIX: Corrected disabled logic ---
             submitted = st.form_submit_button(button_label, disabled=st.session_state.get(is_typing_key, False))
             # --- End FIX ---
             if submitted and analysis_input:
                 logger.info(f"User submitted analysis for exhibit {current_index + 1}.")
                 st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": f"Analysis for Exhibit {current_index + 1}:\n{analysis_input}"})
                 next_index = current_index + 1
                 st.session_state[current_exhibit_index_key] = next_index
                 if next_index >= total_exhibits:
                     logger.info("Last exhibit analysis submitted. Ending session.")
                     st.session_state[done_key] = True
                     if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Analysis interaction timer started on first submit.")
                     end_time = time.time(); start_time = st.session_state.get(start_time_key)
                     if start_time is not None: st.session_state[time_key] = end_time - start_time
                     else: st.session_state[time_key] = 0.0
                     current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                     st.session_state[run_count_key] = current_session_run_count
                     logger.info(f"Session run count incremented to: {current_session_run_count} (Analysis)")
                 else: logger.info(f"Moving to exhibit {next_index + 1}")
                 st.rerun()
        if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Interaction timer started.")
    if st.session_state.get(done_key):
        logger.debug("Entering analysis feedback and conclusion area.")
        st.session_state[is_typing_key] = True
        final_feedback_content = generate_final_feedback(case_prompt_text)
        st.session_state[is_typing_key] = False
        logger.debug(f"Value returned by generate_final_feedback (Analysis): '{final_feedback_content}'")
        feedback_was_generated = final_feedback_content and isinstance(final_feedback_content, str) and final_feedback_content.strip().startswith("## Overall Analysis Rating:")
        logger.debug(f"Feedback generated flag evaluated as: {feedback_was_generated}")
        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0); st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'): st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                st.markdown("**How helpful was the feedback provided above? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_an_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"): selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked rating: {selected_rating} stars.")
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        if save_user_feedback(user_feedback_data): logger.info("User Feedback Auto-Submitted (Rating >= 4) and saved."); st.rerun()
                        else: logger.error("User Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                    else: st.session_state[show_comment_key] = True
                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(f"Comment for your {rating_display} rating:", key=f"{prefix}_an_feedback_comment_input", placeholder="...")
                    if st.button("Submit Rating and Comment", key=f"{prefix}_an_submit_feedback_button"):
                        if not feedback_comment.strip(): st.error("Comment cannot be empty...")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0: st.error("Invalid rating selected...")
                        else:
                            user_feedback_data = {"rating": current_rating_value, "comment": feedback_comment.strip(), "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                            st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                            if save_user_feedback(user_feedback_data): logger.info("User Feedback Submitted with Comment and saved."); st.rerun()
                            else: logger.error("User Feedback Submitted with Comment but FAILED TO SAVE.")
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}"); logger.error(f"Feedback generation resulted in error message: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable or was not generated correctly."); logger.warning(f"Feedback was not displayed. Content: {final_feedback_content}")
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** in the analysis phase.")
        logger.info(f"Displayed analysis conclusion. Total time: {total_interaction_time:.2f}s")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_an_practice_again"): logger.info("User clicked 'Practice This Skill Again' for Analysis."); reset_skill_state(); st.rerun()


# --- NEW: Skill-Specific UI Function (Recommendation) ---
def recommendation_ui():
    # [ Code remains unchanged ]
    logger.info("Loading Recommendation UI.")
    prefix = st.session_state.key_prefix
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    recommendation_input_key = f"{prefix}_recommendation_input"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)
    init_session_state_key(recommendation_input_key, "")
    st.markdown("Review the case prompt and key findings summarized below, then structure your final recommendation including your rationale, potential risks, and next steps. Enter your full recommendation in the text area and click \"Submit Recommendation\" to get feedback.")
    st.divider()
    if st.session_state.get(current_prompt_id_key) is None: logger.info("No current prompt ID (Recommendation), selecting new one."); selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt or current_prompt.get("skill_type") != "Recommendation":
        logger.warning(f"Invalid or missing prompt for Recommendation skill. Prompt ID: {st.session_state.get(current_prompt_id_key)}. Selecting new.")
        selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
        current_prompt = get_prompt_details(selected_id)
        if not current_prompt or current_prompt.get("skill_type") != "Recommendation": logger.error(f"Still could not load a valid Recommendation prompt. Last ID: {selected_id}"); st.error("Could not load a valid Recommendation prompt. Please try selecting the skill again or check prompts.json."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed Recommendation prompt: {case_title}")
    exhibits = current_prompt.get("exhibits", [])
    if not exhibits: st.warning("No exhibits/summary findings found for this recommendation prompt.")
    else:
        for i, exhibit in enumerate(exhibits):
            st.subheader(exhibit.get("exhibit_title", f"Exhibit {i+1} / Key Finding"))
            if exhibit.get("description"): st.caption(exhibit.get("description"))
            data = exhibit.get("data"); summary_text = exhibit.get("summary_text")
            if data:
                try: df = pd.DataFrame(data); st.dataframe(df, use_container_width=True, hide_index=True)
                except Exception as e: logger.error(f"Error processing exhibit {i+1} data for Recommendation: {e}"); st.error(f"Error displaying exhibit {i+1}. Please check data format in prompts.json.")
            elif summary_text:
                 if isinstance(summary_text, list): markdown_summary = "\n".join([f"- {item}  " for item in summary_text]); logger.debug(f"Formatted summary text for Exhibit {i+1}: {markdown_summary}"); st.markdown(markdown_summary, unsafe_allow_html=True)
                 else: st.markdown(summary_text)
            else: st.warning(f"Exhibit {i+1}: No data or summary text found.")
    if not st.session_state.get(done_key):
        st.header("Your Recommendation")
        with st.form(key=f"{prefix}_rec_input_form", clear_on_submit=False):
             recommendation_input = st.text_area("Enter your full recommendation here:", height=300, key=f"{prefix}_rec_form_text_area", disabled=st.session_state.get(is_typing_key, False), placeholder="please enter your recommendation here ")
             submitted = st.form_submit_button("Submit Recommendation", disabled=st.session_state.get(is_typing_key, False))
             if submitted and recommendation_input:
                 logger.info("User submitted recommendation.")
                 st.session_state[conv_key] = [{"role": "interviewee", "content": recommendation_input}]
                 st.session_state[done_key] = True
                 if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Recommendation interaction timer started on submit.")
                 end_time = time.time(); start_time = st.session_state.get(start_time_key)
                 if start_time is not None: st.session_state[time_key] = end_time - start_time
                 else: st.session_state[time_key] = 0.0
                 current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                 st.session_state[run_count_key] = current_session_run_count
                 logger.info(f"Session run count incremented to: {current_session_run_count} (Recommendation)")
                 st.rerun()
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key) or (st.session_state.get(done_key) and not st.session_state.get(feedback_key)): typing_placeholder.text("CHIP is analyzing your recommendation...")
        else: typing_placeholder.empty()
        if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Interaction timer started.")
    if st.session_state.get(done_key):
        logger.debug("Entering recommendation feedback and conclusion area.")
        st.session_state[is_typing_key] = True
        final_feedback_content = generate_final_feedback(case_prompt_text)
        st.session_state[is_typing_key] = False
        logger.debug(f"Value returned by generate_final_feedback (Recommendation): '{final_feedback_content}'")
        feedback_was_generated = final_feedback_content and isinstance(final_feedback_content, str) and final_feedback_content.strip().startswith("## Overall Recommendation Rating:")
        logger.debug(f"Feedback generated flag evaluated as: {feedback_was_generated}")
        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0); st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'): st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                st.markdown("**How helpful was the feedback provided above? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_rec_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"): selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked rating: {selected_rating} stars.")
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        if save_user_feedback(user_feedback_data): logger.info("User Feedback Auto-Submitted (Rating >= 4) and saved."); st.rerun()
                        else: logger.error("User Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                    else: st.session_state[show_comment_key] = True
                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(f"Comment for your {rating_display} rating:", key=f"{prefix}_rec_feedback_comment_input", placeholder="...")
                    if st.button("Submit Rating and Comment", key=f"{prefix}_rec_submit_feedback_button"):
                        if not feedback_comment.strip(): st.error("Comment cannot be empty...")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0: st.error("Invalid rating selected...")
                        else:
                            user_feedback_data = {"rating": current_rating_value, "comment": feedback_comment.strip(), "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                            st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                            if save_user_feedback(user_feedback_data): logger.info("User Feedback Submitted with Comment and saved."); st.rerun()
                            else: logger.error("User Feedback Submitted with Comment but FAILED TO SAVE.")
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}"); logger.error(f"Feedback generation resulted in error message: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable or was not generated correctly."); logger.warning(f"Feedback was not displayed. Content: {final_feedback_content}")
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** in the recommendation phase.")
        logger.info(f"Displayed recommendation conclusion. Total time: {total_interaction_time:.2f}s")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_rec_practice_again"): logger.info("User clicked 'Practice This Skill Again' for Recommendation."); reset_skill_state(); st.rerun()


# --- Entry Point ---
if __name__ == "__main__":
    # [ Initialization remains the same ]
    if 'key_prefix' not in st.session_state:
         st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    init_session_state_key('session_id', str(uuid.uuid4()))
    main_app() # Calls the main_app with skill selection
    logger.info("--- Application Script Execution Finished ---")

