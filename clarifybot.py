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
# from supabase import create_client, Client # No longer needed

# --- Basic Logging Setup ---
# [ Logging setup remains the same ]
log_filename = f"chip_app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - SessionID:%(session_id)s - %(message)s', # Added SessionID to format
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
class SessionLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        session_id = "N/A"
        prefix = st.session_state.get('key_prefix')
        if prefix:
            session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
        kwargs['extra'] = kwargs.get('extra', {})
        kwargs['extra']['session_id'] = session_id
        return msg, kwargs
logger_raw = logging.getLogger(__name__)
logger = SessionLogAdapter(logger_raw, {})
logger.info("--- Application Started ---")


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

SKILLS = ["Clarifying Questions", "Framework Development", "Hypothesis Formulation", "Analysis", "Recommendation"]
init_session_state_key('selected_skill', SKILLS[0]) # Now defined
init_session_state_key('run_count', 0) # Now defined
init_session_state_key('show_donation_dialog', False) # Now defined


# --- Page Config ---
st.set_page_config(
    page_title="CHIP", # Restored title
    page_icon="🤖",
    layout="centered"
)

# --- Custom CSS ---
# --- Restored ---
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

     /* --- Fix #5: Style for Donation Link Button --- */
     /* Target the link button specifically within the dialog/container context */
     /* This might be brittle depending on Streamlit's internal structure */
     div[data-testid="stDialog"] a[data-testid="stLinkButton"],
     div.stAlert a[data-testid="stLinkButton"] /* Target fallback too */
     {
        background-color: #28a745 !important; /* Green background */
        border-color: #28a745 !important; /* Green border */
        color: white !important; /* White text */
        transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out;
     }
     div[data-testid="stDialog"] a[data-testid="stLinkButton"]:hover,
     div.stAlert a[data-testid="stLinkButton"]:hover
     {
         background-color: #218838 !important; /* Darker green on hover */
         border-color: #1e7e34 !important;
         color: white !important;
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
# [ reset_skill_state definition remains here ]
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
        # Add keys specific to the text_input replacement if needed
        # 'cq_text_input_value', # No longer needed with st.form
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
    """Selects a new random prompt, avoiding session repeats if possible."""
    prefix = st.session_state.key_prefix
    used_ids_key = f"{prefix}_used_prompt_ids"
    current_prompt_id_key = f"{prefix}_current_prompt_id"

    init_session_state_key('used_prompt_ids', []) # Ensure it exists

    available_prompt_ids = [pid for pid in ALL_PROMPT_IDS if pid not in st.session_state[used_ids_key]]

    if not available_prompt_ids:
        logger.warning("All prompts seen in this session, allowing repeats.")
        st.info("You've seen all available prompts in this session! Allowing repeats now.")
        st.session_state[used_ids_key] = []
        available_prompt_ids = ALL_PROMPT_IDS
        if not available_prompt_ids:
            logger.error("Cannot select prompt - prompt list is empty.")
            st.error("Cannot select prompt - prompt list is empty.")
            return None

    selected_id = random.choice(available_prompt_ids)
    st.session_state[used_ids_key].append(selected_id)
    st.session_state[current_prompt_id_key] = selected_id
    logger.info(f"Selected Prompt ID: {selected_id}")
    return selected_id

def get_prompt_details(prompt_id):
    """Retrieves prompt details from the loaded list using its ID."""
    if not prompt_id: return None
    for prompt in ALL_PROMPTS:
        if prompt.get('id') == prompt_id:
            return prompt
    logger.warning(f"Prompt ID '{prompt_id}' not found in loaded prompts.")
    return None

def parse_interviewer_response(response_text):
    """Parses the structured ###ANSWER### and ###ASSESSMENT### from LLM response."""
    answer = "Could not parse answer."
    assessment = "No assessment available."
    answer_match = re.search(r"###ANSWER###\s*(.*?)\s*###ASSESSMENT###", response_text, re.DOTALL | re.IGNORECASE)
    assessment_match = re.search(r"###ASSESSMENT###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
    if answer_match: answer = answer_match.group(1).strip()
    if assessment_match: assessment = assessment_match.group(1).strip()
    # Simplified logging for brevity during debug
    if not answer_match and not assessment_match and response_text: answer = response_text.strip(); assessment = "[Assessment not extracted]"
    elif answer_match and not assessment_match: assessment = "[Assessment delimiter missing]"
    elif not answer_match and assessment_match: answer = "[Answer delimiter missing]"
    elif not response_text or not response_text.strip(): answer = "[LLM empty response]"; assessment = "[LLM empty response]"
    return answer, assessment

def send_question(question, current_case_prompt_text):
    """Sends user question to LLM, gets plausible answer & assessment, updates conversation state."""
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    is_typing_key = f"{prefix}_is_typing"
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")

    if not question or not question.strip(): st.warning("Please enter a question."); logger.warning("User attempted to send empty question."); return
    if not current_case_prompt_text: st.error("Internal Error: No case prompt context."); logger.error("Internal Error: send_question called without case_prompt_text."); return

    st.session_state[is_typing_key] = True
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - User Input: '{question}'")
    st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": question})

    try:
        history_for_prompt = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.get(conv_key, [])[:-1]])
        # --- Define LLM Prompt based on Skill ---
        if selected_skill == "Clarifying Questions":
            # --- Reverted Prompt Instructions ---
            prompt_for_llm = f"""
            You are a **strict** case interviewer simulator focusing ONLY on the clarifying questions phase. Evaluate questions **rigorously**.

            Current Case Prompt Context:
            {current_case_prompt_text}

            Conversation History So Far:
            {history_for_prompt}

            Interviewee's Latest Question:
            {question}

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

        elif selected_skill == "Framework Development":
             # This prompt is now primarily used by generate_final_feedback
             # send_question is NOT called directly in the new Framework Dev flow
             # We keep the definition here for consistency / potential future use
             prompt_for_llm = f"""
             You are a case interview coach evaluating a candidate's proposed framework...
             Case Prompt Context:
             {current_case_prompt_text}
             Candidate's Proposed Framework/Approach:
             {question}
             Your Task: ...
             ###ANSWER###
             [Your brief acknowledgement]
             ###ASSESSMENT###
             [Your structured assessment and suggestions]
             """
             system_message = "You are a case interview coach evaluating framework proposals..."

        else:
            logger.error(f"Attempted to send question for unhandled skill: {selected_skill}")
            st.error(f"Interaction logic for '{selected_skill}' is not yet implemented.")
            st.session_state.setdefault(conv_key, []).append({
                "role": "interviewer", "content": f"Sorry, the interaction for '{selected_skill}' is not ready yet.", "assessment": "N/A"
            })
            st.session_state[is_typing_key] = False
            st.rerun()
            return

        # logger.debug(f"LLM Prompt:\n{prompt_for_llm}")
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt_for_llm}],
            max_tokens=350, temperature=0.5, stream=True
        )
        full_response = ""
        with st.spinner(f"CHIP is generating response for {selected_skill}..."):
             for chunk in response:
                 if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                     full_response += chunk.choices[0].delta.content

        interviewer_answer, interviewer_assessment = parse_interviewer_response(full_response)
        logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - LLM Answer: '{interviewer_answer[:100]}...'")
        logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - LLM Assessment: '{interviewer_assessment[:100]}...'")
        st.session_state.setdefault(conv_key, []).append({"role": "interviewer", "content": interviewer_answer, "assessment": interviewer_assessment})

    except Exception as e:
        logger.exception(f"Error generating LLM response: {e}")
        st.error(f"Error generating response: {e}")
        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer", "content": f"Sorry, an error occurred... ({type(e).__name__})", "assessment": "N/A due to error."
        })
    finally:
        st.session_state[is_typing_key] = False
        st.rerun() # Still need rerun to display new message

def generate_final_feedback(current_case_prompt_text):
    """
    Generates overall feedback markdown based on the conversation history.
    For Framework Dev, expects history to contain the single submitted framework.
    """
    prefix = st.session_state.key_prefix; conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - Attempting to generate final feedback.")
    existing_feedback = st.session_state.get(feedback_key)
    feedback_submitted = st.session_state.get(feedback_submitted_key, False)
    if feedback_submitted: logger.info("Skipping feedback gen: Feedback already submitted by user."); return existing_feedback
    if existing_feedback is not None: logger.info("Skipping feedback gen: Feedback key exists and is not None."); return existing_feedback

    # Format history based on skill
    history_string = ""
    conversation_history = st.session_state.get(conv_key, [])

    if not conversation_history:
        logger.warning("Skipping feedback gen: No conversation history found.")
        return "[Could not generate feedback: No interaction history found]"
    if not isinstance(conversation_history, list):
        logger.error(f"Internal Error: Conversation history format issue. Type: {type(conversation_history)}")
        st.error("Internal Error: Conversation history format issue.")
        st.session_state[feedback_key] = "Error: Could not generate feedback due to history format."
        return st.session_state[feedback_key]

    if selected_skill == "Framework Development":
        # Use the single framework submission stored in conversation
        if conversation_history and conversation_history[0].get("role") == "interviewee":
             history_string = f"Candidate's Submitted Framework:\n{conversation_history[0].get('content', '[Framework not found]')}"
        else:
             logger.warning("Framework Dev: Could not extract framework from conversation state.")
             return "[Could not generate feedback: Framework submission not found in state]"
    else: # For Clarifying Questions (and potentially others later)
        formatted_history = []
        for i, msg in enumerate(conversation_history):
            role = msg.get("role"); content = msg.get("content", "[missing content]"); q_num = (i // 2) + 1
            if role == 'interviewee': formatted_history.append(f"Interviewee Input {q_num}: {content}")
            elif role == 'interviewer':
                formatted_history.append(f"Interviewer Response to Input {q_num}: {content}")
                assessment = msg.get('assessment')
                if assessment: formatted_history.append(f" -> Interviewer's Assessment of Input {q_num}: {assessment}")
        history_string = "\n\n".join(formatted_history)

    if not history_string:
         logger.warning("Skipping feedback gen: Formatted history string is empty.")
         return "[Could not generate feedback: Formatted history is empty]"

    with st.spinner(f"Generating Final Feedback for {selected_skill}..."):
        try:
            # --- Define Feedback Prompt based on Skill ---
            if selected_skill == "Clarifying Questions":
                # --- Using the original feedback prompt structure ---
                feedback_prompt = f"""
                You are an experienced case interview coach providing feedback on the clarifying questions phase ONLY.

                Case Prompt Context for this Session:
                {current_case_prompt_text}

                Interview Interaction History (User questions, your answers as INTERVIEWER, and your per-question assessments):
                {history_string}

                Your Task:
                Provide detailed, professional, and direct feedback on the interviewee's clarifying questions phase based *only* on the interaction history provided. Use markdown formatting effectively, including paragraph breaks for readability.

                Structure your feedback precisely as follows using Markdown:

                ## Overall Rating: [1-5]/5
                *(Provide a brief justification for the rating here, referencing the conversation specifics or assessments. Be very critical and use the full range of scores based on the criteria below)*

                ---

                1.  **Overall Summary:** Briefly summarize the interviewee's performance in asking clarifying questions for *this specific case context*.

                2.  **Strengths:** Identify 1-2 specific strengths demonstrated (e.g., good initial questions, logical flow, conciseness). Refer to specific question numbers or assessments if possible.

                3.  **Areas for Improvement:** Identify 1-2 key areas where the interviewee could improve (e.g., question relevance, depth, avoiding compound questions, structure, digging deeper based on answers). Refer to specific question numbers or assessments.

                4.  **Actionable Next Steps:** Provide at least two concrete, actionable steps the interviewee can take to improve their clarifying questions skills *for future cases*.

                5.  **Example Questions:** For *each* actionable next step that relates to the *content* or *quality* of the questions asked, provide 1-2 specific *alternative* example questions the interviewee *could have asked* in *this case* to demonstrate improvement in that area.

                **Rating Criteria Reference:**
                    * 1: **Must use this score** if questions were predominantly vague (like single words), irrelevant, unclear, compound, or demonstrated a fundamental lack of understanding of how to clarify effectively. Added little to no value.
                    * 2: Significant issues remain. Many questions were poor, with only occasional relevant ones, or showed a consistent lack of focus/structure.
                    * 3: A mixed bag. Some decent questions fitting the ideal categories (Objective, Company, Terms, Repetition) but also notable lapses in quality, relevance, or efficiency.
                    * 4: Generally strong performance. Most questions were relevant, clear, targeted, and fit the ideal categories. Good progress made in clarifying the case, with only minor areas for refinement.
                    * 5: Excellent. Consistently high-quality questions that were relevant, concise, targeted, and demonstrated a strong grasp of the ideal clarifying categories. Effectively and efficiently clarified key aspects of the case prompt.
                   *(Remember to consider the per-question assessments provided in the history when assigning the overall rating.)*

                Ensure your response does **not** start with any other title. Start directly with the '## Overall Rating:' heading. Use paragraph breaks between sections.
                """
                system_message_feedback = "You are an expert case interview coach providing structured feedback on clarifying questions. Start directly with the '## Overall Rating:' heading. Evaluate critically based on history and assessments. Use markdown effectively for readability."
                max_tokens_feedback = 800
                # --- End of original feedback prompt ---

            elif selected_skill == "Framework Development":
                 # --- Updated Framework Feedback Prompt (Summary First) ---
                 feedback_prompt = f"""
                 You are an experienced case interview coach providing final summary feedback on the framework development phase based on a single framework submission.

                 Case Prompt Context for this Session:
                 {current_case_prompt_text}

                 {history_string} # This now contains only the submitted framework text with a label

                 Your Task:
                 Provide detailed, professional, final feedback on the candidate's submitted framework. Use markdown formatting effectively.

                 Structure your feedback precisely as follows using Markdown, starting DIRECTLY with the summary:

                 ## Feedback Summary
                 *(Summarize the effectiveness and quality of the proposed framework for tackling *this specific case*. Did the candidate create a solid structure? Follow this summary immediately with the rating on the next line.)*
                 **Overall Rating: [1-5]/5** *(Justify briefly here, considering MECE, Relevance, Prioritization, Actionability, and Clarity criteria below)*

                 ---

                 1.  **Strengths:** Identify 1-2 specific strengths of the submitted framework (e.g., good structure, relevant buckets, clear logic).

                 2.  **Areas for Improvement:** Identify 1-2 key weaknesses or areas for development based on the submitted framework (e.g., not MECE, missing key drivers from the prompt, poor prioritization, too generic, structure unclear).

                 3.  **Actionable Next Steps:** Provide at least two concrete, actionable steps the candidate can take to improve their framework development skills *for future cases*.

                 4.  **Example Refinement / Alternative:** Suggest one specific, significant refinement to the submitted framework *or* propose a concise alternative structure that might have been more effective for *this case*, explaining why briefly.


                 **Rating Criteria Reference:**
                 * 1: **Fundamentally flawed.** Not MECE, irrelevant to the case, unclear structure, unusable for analysis. Little understanding shown.
                 * 2: **Major issues.** Significant gaps or overlaps (not MECE), poor structure, lacks relevance to key case issues, unclear or difficult to follow.
                 * 3: **Partially effective.** Some relevant components, but structure could be significantly improved (e.g., not fully MECE, poor prioritization, some irrelevant buckets). Shows basic understanding but needs refinement.
                 * 4: **Good framework.** Mostly MECE, relevant to the case, actionable, and reasonably prioritized. Structure is clear. Only minor refinements possible.
                 * 5: **Excellent.** Clear, MECE, highly relevant to the core issues, well-prioritized, actionable, and tailored effectively to the case specifics. Demonstrates strong strategic thinking.

                 Ensure your response does **not** start with any other title besides "## Feedback Summary". Use paragraph breaks between sections.
                 """
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on framework development based on a single submission. Start directly with the '## Feedback Summary' heading, followed by the rating. Evaluate critically based on the submitted framework. Use markdown effectively."
                 max_tokens_feedback = 700
                 # --- End of Updated Framework Feedback Prompt ---

            else:
                logger.error(f"Cannot generate feedback for unhandled skill: {selected_skill}")
                st.error(f"Feedback generation for '{selected_skill}' is not yet implemented.")
                st.session_state[feedback_key] = f"Error: Feedback generation not implemented for {selected_skill}."
                return st.session_state[feedback_key]
            logger.info("Calling OpenAI API for final feedback...")
            feedback_response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_message_feedback}, {"role": "user", "content": feedback_prompt}], max_tokens=max_tokens_feedback, temperature=0.5)
            feedback = feedback_response.choices[0].message.content.strip()
            logger.info(f"Feedback received from API (first 100 chars): {feedback[:100]}")
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
    """Main function to control skill selection and display."""
    st.title("CHIP") # Restored title
    logger.info("Main application UI rendered.")
    prefix = st.session_state.key_prefix
    skill_key = f"{prefix}_selected_skill"
    st.write("Select Skill to Practice:")
    cols_row1 = st.columns(3); cols_row2 = st.columns(3)
    current_selection = st.session_state.get(skill_key, SKILLS[0])
    def handle_skill_click(skill_name):
        if skill_name != st.session_state.get(skill_key):
            logger.info(f"Skill selected: {skill_name}")
            st.session_state[skill_key] = skill_name
            reset_skill_state(); st.rerun()
        else: logger.debug(f"Clicked already selected skill: {skill_name}")
    button_map = {SKILLS[0]: cols_row1[0], SKILLS[1]: cols_row1[1], SKILLS[2]: cols_row1[2], SKILLS[3]: cols_row2[0], SKILLS[4]: cols_row2[1]}
    for skill, col in button_map.items():
        with col:
            button_type = "primary" if skill == current_selection else "secondary"
            if st.button(skill, key=f"skill_btn_{skill.replace(' ', '_')}", use_container_width=True, type=button_type): handle_skill_click(skill)
    st.divider()
    selected_skill = st.session_state.get(skill_key, SKILLS[0])
    logger.debug(f"Loading UI for skill: {selected_skill}")
    # --- Routing to Skill UI Functions ---
    if selected_skill == "Clarifying Questions": clarifying_questions_bot_ui()
    elif selected_skill == "Framework Development": framework_development_ui()
    elif selected_skill == "Hypothesis Formulation": st.header("Hypothesis Formulation"); st.info("Under construction..."); logger.info("Displayed 'Under Construction'...")
    elif selected_skill == "Analysis": st.header("Analysis"); st.info("Under construction..."); logger.info("Displayed 'Under Construction'...")
    elif selected_skill == "Recommendation": st.header("Recommendation"); st.info("Under construction..."); logger.info("Displayed 'Under Construction'...")
    else: logger.error(f"Invalid skill selected: {selected_skill}"); st.error("Invalid skill selected.")

# --- Skill-Specific UI Functions (clarifying_questions_bot_ui, framework_development_ui) ---

def clarifying_questions_bot_ui():
    logger.info("Loading Clarifying Questions UI.")
    prefix = st.session_state.key_prefix
    # Define keys
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    show_donation_dialog_key = f"{prefix}_show_donation_dialog"
    # Initialize state
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)
    # text_input_key no longer needed with st.form


    # --- Show Donation Dialog ---
    # --- Restored ---
    if st.session_state.get(show_donation_dialog_key):
        logger.info("Displaying donation dialog.")
        # --- Fix #1: Update Fallback Message ---
        full_donation_message = (
            "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
            "Consider making a small donation (suggested $5) to help cover server and API costs."
        )
        donate_url = "https://buymeacoffee.com/9611"
        # --- End Fix #1 ---

        if hasattr(st, 'dialog'):
            @st.dialog("Support CHIP!")
            def show_donation():
                st.write(full_donation_message) # Use full message
                col1, col2, col3 = st.columns([0.5, 3, 0.5])
                with col2:
                     # --- Fix #5: Update Button Text ---
                     st.link_button("Buy Me a Coffee ☕", donate_url, type="primary", use_container_width=True)
                     # --- End Fix #5 ---
                if st.button("Maybe later", key="maybe_later_btn_cq", use_container_width=True): # Unique key
                    logger.info("User clicked 'Maybe later' on donation dialog.")
                    # st.session_state[show_donation_dialog_key] = False # Flag is reset below anyway
                    st.rerun()
            show_donation()
        else: # Fallback
            with st.container(border=True):
                st.success(full_donation_message) # Use full message
                 # --- Fix #5: Update Button Text ---
                st.link_button("Buy Me a Coffee ☕", donate_url, type="primary")
                 # --- End Fix #5 ---
            # Fallback doesn't have a "Maybe later" button, so we just hide it after showing
            # st.session_state[show_donation_dialog_key] = False # Moved below

        # --- Fix #4: Reset flag after showing dialog/fallback ---
        # This ensures it doesn't reappear immediately on the next rerun unless triggered again
        st.session_state[show_donation_dialog_key] = False
        # --- End Fix #4 ---

    # --- Select and Display Case Prompt ---
    if st.session_state.get(current_prompt_id_key) is None:
        logger.info("No current prompt ID, selecting new one.")
        selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt:
        logger.error(f"Could not load details for prompt ID: {st.session_state.get(current_prompt_id_key)}")
        st.error("Could not load the current case prompt details..."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt: {case_title}")

    # --- Main Interaction Area ---
    if not st.session_state.get(done_key):
        # --- Fix #4: Updated Header and Instructions ---
        st.header("Clarifying Questions") # Changed header text
        # Using markdown for larger font size
        st.markdown("<span style='font-size: 1.1em;'>Ask questions below. Click 'End Clarification Questions' when finished.</span>", unsafe_allow_html=True)
        # --- End of Fix #4 ---

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
                if current_session_run_count == 2 or current_session_run_count == 11:
                     st.session_state[show_donation_dialog_key] = True
                     logger.info(f"Flag set to show donation dialog for achieving run count {current_session_run_count}")
                st.rerun()
        if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Interaction timer started.")
        # Chat history display
        chat_container = st.container()
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role"); display_role = "user" if role == "interviewee" else "assistant"
                     with st.chat_message(display_role): st.markdown(msg.get("content", ""))
        # Typing indicator
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key): typing_placeholder.text("CHIP is thinking...")
        else: typing_placeholder.empty()

        # --- Fix #2 & #3: Input Section Using st.form ---
        with st.form(key=f"{prefix}_cq_input_form", clear_on_submit=True):
             user_question = st.text_input(
                 "Type your question here:",
                 key=f"{prefix}_cq_form_text_input", # Key for the input *inside* the form
                 disabled=st.session_state.get(is_typing_key, False),
                 label_visibility="collapsed",
                 placeholder="Type your question..."
             )
             submitted = st.form_submit_button(
                 "Send",
                 disabled=st.session_state.get(is_typing_key, False) # Only disable if AI is typing
             )
             if submitted and user_question:
                 logger.debug(f"Form submitted with question: '{user_question}'")
                 if st.session_state.get(is_typing_key):
                     typing_placeholder.empty() # Clear indicator if needed
                 send_question(user_question, case_prompt_text)
                 # No explicit rerun needed here, form submission handles it.
                 # No need to clear the input manually, clear_on_submit=True does it.
        # --- End of Fix #2 & #3 ---


    # --- Feedback and Conclusion Area ---
    if st.session_state.get(done_key):
        logger.debug("Entering feedback and conclusion area.")
        final_feedback_content = generate_final_feedback(case_prompt_text)
        feedback_was_generated = final_feedback_content and not str(final_feedback_content).startswith("Error") and not str(final_feedback_content).startswith("[Feedback")

        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()

            # --- Restored Feedback Rating Section ---
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                 # [ Display submitted feedback remains the same ]
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0); st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'): st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                # --- Feedback Input Logic (Calls updated save_user_feedback) ---
                st.markdown("**How helpful was the feedback provided above? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_cq_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"):
                            selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked rating: {selected_rating} stars.")

                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        # --- Fix #1: Modified Rerun Logic ---
                        if save_user_feedback(user_feedback_data):
                            logger.info("User Feedback Auto-Submitted (Rating >= 4) and saved.")
                            st.rerun() # Rerun only on success
                        else:
                            logger.error("User Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                            # Error is displayed within save_user_feedback, no rerun here to let it persist
                        # --- End of Fix #1 ---
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
                            # --- Fix #1: Modified Rerun Logic ---
                            if save_user_feedback(user_feedback_data):
                                logger.info("User Feedback Submitted with Comment and saved.")
                                st.rerun() # Rerun only on success
                            else:
                                logger.error("User Feedback Submitted with Comment but FAILED TO SAVE.")
                                # Error is displayed within save_user_feedback, no rerun here to let it persist
                            # --- End of Fix #1 ---
            # --- End of Restored Feedback Rating Section ---

        # [ Error/Warning display for feedback generation remains the same ]
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable...")

        # [ Conclusion display remains the same ]
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds**...")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_cq_practice_again"):
                logger.info("User clicked 'Practice This Skill Again' for Clarifying Questions.")
                reset_skill_state(); st.rerun()


def framework_development_ui():
    # --- Fix #2: Simplified Framework Feedback Flow ---
    logger.info("Loading Framework Development UI.")
    prefix = st.session_state.key_prefix
    # Define keys
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    show_donation_dialog_key = f"{prefix}_show_donation_dialog"
    # Initialize state
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)

    # --- Show Donation Dialog ---
    if st.session_state.get(show_donation_dialog_key):
        logger.info("Displaying donation dialog (Framework Dev).")
        # --- Fix #1: Update Fallback Message ---
        full_donation_message = (
            "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
            "Consider making a small donation (suggested $5) to help cover server and API costs."
        )
        donate_url = "https://buymeacoffee.com/9611"
        # --- End Fix #1 ---

        if hasattr(st, 'dialog'):
            @st.dialog("Support CHIP!")
            def show_donation():
                st.write(full_donation_message) # Use full message
                col1, col2, col3 = st.columns([0.5, 3, 0.5]);
                with col2:
                    # --- Fix #5: Update Button Text ---
                    st.link_button("Buy Me a Coffee ☕", donate_url, type="primary", use_container_width=True)
                    # --- End Fix #5 ---
                if st.button("Maybe later", key="maybe_later_btn_fw", use_container_width=True):
                    logger.info("User clicked 'Maybe later' on donation dialog (Framework Dev).")
                    # st.session_state[show_donation_dialog_key] = False # Reset below
                    st.rerun()
            show_donation()
        else: # Fallback
             with st.container(border=True):
                 st.success(full_donation_message) # Use full message
                 # --- Fix #5: Update Button Text ---
                 st.link_button("Buy Me a Coffee ☕", donate_url, type="primary")
                 # --- End Fix #5 ---
             # st.session_state[show_donation_dialog_key] = False # Reset below

        # --- Fix #4: Reset flag after showing dialog/fallback ---
        st.session_state[show_donation_dialog_key] = False
        # --- End Fix #4 ---


    # --- Select and Display Case Prompt ---
    if st.session_state.get(current_prompt_id_key) is None:
        logger.info("No current prompt ID (Framework Dev), selecting new one.")
        selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt:
        logger.error(f"Could not load details for prompt ID (Framework Dev): {st.session_state.get(current_prompt_id_key)}")
        st.error("Could not load the current case prompt details..."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt (Framework Dev): {case_title}")

    # --- Main Interaction Area (Framework Development - Simplified Flow) ---
    if not st.session_state.get(done_key):
        st.header("Develop Your Framework"); st.caption("Outline your framework structure below and click 'Submit Framework' to get feedback.")

        # Use a form for single submission
        with st.form(key=f"{prefix}_fw_input_form", clear_on_submit=False): # Keep text on submit initially
             framework_input = st.text_area(
                 "Enter your framework here:",
                 height=200,
                 key=f"{prefix}_fw_form_text_area", # Key for the input *inside* the form
                 disabled=st.session_state.get(is_typing_key, False), # Disable if feedback is generating
                 placeholder="e.g.,\n1. Market Analysis\n   a. Market Size...\n2. Competitive Landscape..."
             )
             submitted = st.form_submit_button(
                 "Submit Framework for Feedback",
                 disabled=st.session_state.get(is_typing_key, False) or not framework_input # Disable if no text or typing
             )
             if submitted and framework_input:
                 logger.info("User submitted framework for final feedback.")
                 # Store the submission minimally for the feedback function
                 st.session_state[conv_key] = [{"role": "interviewee", "content": framework_input}]
                 # Set done flag to trigger feedback display on next run
                 st.session_state[done_key] = True
                 # Calculate time, increment run count, check donation
                 if st.session_state.get(start_time_key) is None: # Start timer if not already started
                    st.session_state[start_time_key] = time.time()
                    logger.info("Framework interaction timer started on submit.")
                 end_time = time.time(); start_time = st.session_state.get(start_time_key)
                 if start_time is not None: st.session_state[time_key] = end_time - start_time
                 else: st.session_state[time_key] = 0.0
                 current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                 st.session_state[run_count_key] = current_session_run_count
                 logger.info(f"Session run count incremented to: {current_session_run_count} (Framework Dev)")
                 if current_session_run_count == 2 or current_session_run_count == 11:
                     st.session_state[show_donation_dialog_key] = True
                     logger.info(f"Flag set to show donation dialog for achieving run count {current_session_run_count} (Framework Dev)")
                 # Rerun to display feedback section
                 st.rerun()

        # Typing indicator (will show while feedback generates on next run)
        typing_placeholder = st.empty()
        # Check done_key as well, indicator should show when feedback is generating
        if st.session_state.get(is_typing_key) or (st.session_state.get(done_key) and not st.session_state.get(feedback_key)):
             typing_placeholder.text("CHIP is analyzing your framework...")
        else:
             typing_placeholder.empty()

        # REMOVED "Get Final Summary Feedback" button and intermediate history display

    # --- Feedback and Conclusion Area (Framework Development) ---
    if st.session_state.get(done_key):
        logger.debug("Entering framework feedback and conclusion area.")

        # --- Fix #3: Remove Python Header ---
        # st.header("Overall Framework Feedback") # Removed this header

        # Generate and display feedback
        final_feedback_content = generate_final_feedback(case_prompt_text) # Uses updated prompt
        feedback_was_generated = final_feedback_content and not str(final_feedback_content).startswith("Error") and not str(final_feedback_content).startswith("[Feedback")

        if feedback_was_generated:
            st.divider()
            st.markdown(final_feedback_content) # Displays feedback starting with "## Feedback Summary"
            st.divider()
            # --- Restored Feedback Rating Section ---
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
                        if st.button('★' * (i + 1), key=f"{prefix}_fw_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"):
                            selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked framework feedback rating: {selected_rating} stars.")
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        # --- Fix #1: Modified Rerun Logic ---
                        if save_user_feedback(user_feedback_data):
                            logger.info("User Framework Feedback Auto-Submitted (Rating >= 4) and saved.")
                            st.rerun() # Rerun only on success
                        else:
                            logger.error("User Framework Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE.")
                        # --- End of Fix #1 ---
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
                            # --- Fix #1: Modified Rerun Logic ---
                            if save_user_feedback(user_feedback_data):
                                logger.info("User Framework Feedback Submitted with Comment and saved.")
                                st.rerun() # Rerun only on success
                            else:
                                logger.error("User Framework Feedback Submitted with Comment but FAILED TO SAVE.")
                            # --- End of Fix #1 ---
            # --- End of Restored Feedback Rating Section ---
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable...")

        # Conclusion Section
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** developing the framework for this case.") # Adjusted text slightly
        logger.info(f"Displayed framework conclusion. Total time: {total_interaction_time:.2f}s")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_fw_practice_again"):
                logger.info("User clicked 'Practice This Skill Again' for Framework Development.")
                reset_skill_state(); st.rerun()

# --- Entry Point ---
if __name__ == "__main__":
    # [ Initialization remains the same ]
    if 'key_prefix' not in st.session_state:
         st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    init_session_state_key('session_id', str(uuid.uuid4()))
    main_app() # Calls the main_app with skill selection
    logger.info("--- Application Script Execution Finished ---")

