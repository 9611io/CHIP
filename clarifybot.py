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
# import psycopg2 # Removed for Supabase
# from psycopg2 import sql # Removed for Supabase
from supabase import create_client, Client # Added for Supabase

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


# --- Supabase Connection Function ---
@st.cache_resource # Cache the Supabase client for efficiency
def get_supabase_client() -> Client | None:
    """Initializes and returns the Supabase client using secrets."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        logger.info("Attempting to create Supabase client.")
        client: Client = create_client(url, key)
        logger.info("Supabase client created successfully.")
        return client
    except KeyError:
        logger.error("SUPABASE_URL or SUPABASE_KEY not found in Streamlit secrets.")
        st.error("Supabase configuration error: URL or Key missing in secrets.")
        return None
    except Exception as e:
        logger.exception(f"Error creating Supabase client: {e}")
        st.error(f"Error creating Supabase client: {e}")
        return None

# --- REMOVED: Function to Initialize Feedback Table (init_feedback_table) ---
# Table creation is now handled manually in the Supabase dashboard via SQL Editor.

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
    page_title="CHIP",
    page_icon="🤖",
    layout="centered"
)

# --- Custom CSS ---
# [Your CSS remains unchanged]
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


    /* --- Text Area & Chat Input --- */
    div[data-testid="stTextArea"] textarea { /* Style for feedback comment box */
        border: 1px solid #D0D0D0;
        border-radius: 8px;
    }
     /* Default stChatInput styling */
     div[data-testid="stChatInput"] {
         border-top: 1px solid #DDDDDD;
         padding-top: 15px;
     }
      div[data-testid="stChatInput"] textarea {
          border: 1px solid #CCCCCC;
          border-radius: 8px;
      }

    /* --- Other Elements --- */
    /* Using default alert box styling */

</style>
""", unsafe_allow_html=True)

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


# --- UPDATED: Function to Save User Feedback to Supabase ---
def save_user_feedback(feedback_data):
    """
    Saves the user feedback to the configured Supabase database.
    Assumes a table named 'user_feedback' exists with matching columns.
    """
    prefix = st.session_state.key_prefix
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = feedback_data.get("prompt_id", "N/A")
    rating = feedback_data.get("rating")
    comment = feedback_data.get("comment", "")
    # Supabase handles timestamp automatically if column default is now()

    log_message = (
        f"Attempting to save USER_FEEDBACK via Supabase :: Skill: {selected_skill}, "
        f"PromptID: {prompt_id}, Rating: {rating}, Comment: '{comment}'"
    )
    logger.info(log_message)

    supabase = get_supabase_client()
    if supabase is None:
        logger.error("Cannot save feedback, Supabase client failed to initialize.")
        st.error("Failed to save feedback due to Supabase connection issue.")
        return False

    success = False
    try:
        # Prepare data payload matching table columns (excluding 'id' and 'timestamp' if auto-generated)
        data_to_insert = {
            "session_id": session_id,
            "skill": selected_skill,
            "prompt_id": prompt_id,
            "rating": rating,
            "comment": comment
            # 'timestamp' is set by default in the database
        }
        # Insert data into the 'user_feedback' table
        response = supabase.table('user_feedback').insert(data_to_insert).execute()

        # Check response (Supabase API v1 might return data in response.data)
        # Check for errors (Supabase client might raise exceptions on failure)
        # Basic check: assume success if no exception is raised
        logger.info(f"Successfully saved feedback to Supabase for SessionID: {session_id}. Response: {response}")
        success = True

    except Exception as e:
        logger.exception(f"Supabase error saving feedback: {e}")
        # Attempt to log more details if available from the exception
        error_details = str(e)
        if hasattr(e, 'details'):
            error_details = f"{e} - Details: {e.details}"
        elif hasattr(e, 'message'):
             error_details = f"{e} - Message: {e.message}"
        st.error(f"Database error saving feedback: {error_details}")

    return success


# --- Other Helper Functions (select_new_prompt, get_prompt_details, parse_interviewer_response, send_question, generate_final_feedback) ---
# [ Remain the same, ensure they use the logger adapter ]
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

    if answer_match:
        answer = answer_match.group(1).strip()
    if assessment_match:
        assessment = assessment_match.group(1).strip()

    if not answer_match and not assessment_match and response_text:
        answer = response_text.strip()
        assessment = "[Assessment not extracted - delimiters missing]"
        logger.warning(f"Could not find delimiters in LLM response: '{response_text[:100]}...'")
    elif answer_match and not assessment_match:
         assessment = "[Assessment delimiter missing]"
         logger.warning("Found ###ANSWER### but not ###ASSESSMENT### in LLM response.")
    elif not answer_match and assessment_match:
         answer = "[Answer delimiter missing]"
         logger.warning("Found ###ASSESSMENT### but not ###ANSWER### in LLM response.")
    elif not response_text or not response_text.strip():
        answer = "[LLM returned empty response]"
        assessment = "[LLM returned empty response]"
        logger.warning("LLM returned an empty or whitespace-only response.")

    return answer, assessment

def send_question(question, current_case_prompt_text):
    """Sends user question to LLM, gets plausible answer & assessment, updates conversation state."""
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    is_typing_key = f"{prefix}_is_typing"
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")

    if not question or not question.strip():
        st.warning("Please enter a question.")
        logger.warning("User attempted to send empty question.")
        return
    if not current_case_prompt_text:
        st.error("Internal Error: Cannot send question without case prompt context.")
        logger.error("Internal Error: send_question called without case_prompt_text.")
        return

    st.session_state[is_typing_key] = True
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - User Input: '{question}'")
    st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": question})

    try:
        history_for_prompt = "\n".join(
            [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.get(conv_key, [])[:-1]]
        )

        # --- Define LLM Prompt based on Skill ---
        if selected_skill == "Clarifying Questions":
            # [ Prompt content remains the same ]
            prompt_for_llm = f"""
            You are a **strict** case interviewer simulator focusing ONLY on the clarifying questions phase...
            Current Case Prompt Context:
            {current_case_prompt_text}
            Conversation History So Far:
            {history_for_prompt}
            Interviewee's Latest Question:
            {question}
            Your Task: ...
            ###ANSWER###
            [Your plausible answer here]
            ###ASSESSMENT###
            [Your brief but rigorous assessment...]
            """
            system_message = "You are a strict case interview simulator for clarifying questions..."

        elif selected_skill == "Framework Development":
             # [ Prompt content remains the same ]
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
        st.rerun()


def generate_final_feedback(current_case_prompt_text):
    """Generates overall feedback markdown based on the conversation history."""
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    feedback_key = f"{prefix}_feedback"
    feedback_submitted_key = f"{prefix}_feedback_submitted"
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")

    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - Attempting to generate final feedback.")
    existing_feedback = st.session_state.get(feedback_key)
    feedback_submitted = st.session_state.get(feedback_submitted_key, False)

    if feedback_submitted:
         logger.info("Skipping feedback gen: Feedback already submitted by user.")
         return existing_feedback
    if existing_feedback is not None:
        logger.info("Skipping feedback gen: Feedback key exists and is not None.")
        return existing_feedback
    if not st.session_state.get(conv_key):
        logger.warning("Skipping feedback gen: No conversation history.")
        return None

    with st.spinner(f"Generating Final Feedback for {selected_skill}..."):
        try:
            formatted_history = []
            conversation_history = st.session_state.get(conv_key, [])
            if not isinstance(conversation_history, list):
                logger.error(f"Internal Error: Conversation history format issue. Type: {type(conversation_history)}")
                st.error("Internal Error: Conversation history format issue.")
                st.session_state[feedback_key] = "Error: Could not generate feedback due to history format."
                return st.session_state[feedback_key]

            for i, msg in enumerate(conversation_history):
                 # [ History formatting remains the same ]
                role = msg.get("role")
                content = msg.get("content", "[missing content]")
                q_num = (i // 2) + 1
                if role == 'interviewee':
                    formatted_history.append(f"Interviewee Input {q_num}: {content}")
                elif role == 'interviewer':
                    formatted_history.append(f"Interviewer Response to Input {q_num}: {content}")
                    assessment = msg.get('assessment')
                    if assessment:
                        formatted_history.append(f" -> Interviewer's Assessment of Input {q_num}: {assessment}")
            history_string = "\n\n".join(formatted_history)

            # --- Define Feedback Prompt based on Skill ---
            if selected_skill == "Clarifying Questions":
                 # [ Prompt content remains the same ]
                feedback_prompt = f"""
                You are an experienced case interview coach providing feedback on the clarifying questions phase ONLY...
                Case Prompt Context for this Session:
                {current_case_prompt_text}
                Interview Interaction History...:
                {history_string}
                Your Task: ...
                ## Overall Rating: [1-5]/5
                ...
                """
                system_message_feedback = "You are an expert case interview coach providing structured feedback on clarifying questions..."
                max_tokens_feedback = 800

            elif selected_skill == "Framework Development":
                 # [ Prompt content remains the same ]
                 feedback_prompt = f"""
                 You are an experienced case interview coach providing feedback on the framework development phase...
                 Case Prompt Context for this Session:
                 {current_case_prompt_text}
                 Interaction History...:
                 {history_string}
                 Your Task: ...
                 ## Overall Framework Rating: [1-5]/5
                 ...
                 """
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on framework development..."
                 max_tokens_feedback = 700

            else:
                logger.error(f"Cannot generate feedback for unhandled skill: {selected_skill}")
                st.error(f"Feedback generation for '{selected_skill}' is not yet implemented.")
                st.session_state[feedback_key] = f"Error: Feedback generation not implemented for {selected_skill}."
                return st.session_state[feedback_key]

            logger.info("Calling OpenAI API for final feedback...")
            feedback_response = client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "system", "content": system_message_feedback}, {"role": "user", "content": feedback_prompt}],
                max_tokens=max_tokens_feedback, temperature=0.5,
            )
            feedback = feedback_response.choices[0].message.content.strip()
            logger.info(f"Feedback received from API (first 100 chars): {feedback[:100]}")

            if feedback:
                 st.session_state[feedback_key] = feedback
            else:
                 logger.warning("LLM returned empty feedback.")
                 st.session_state[feedback_key] = "[Feedback generation returned empty]"
            return st.session_state[feedback_key]

        except Exception as e:
            logger.exception(f"Error during feedback generation API call: {e}")
            st.error(f"Could not generate feedback. Error: {e}")
            st.session_state[feedback_key] = f"Error generating feedback: {type(e).__name__}"
            return st.session_state[feedback_key]


# --- Main Streamlit Application Function ---
def main_app():
    """Main function to control skill selection and display."""
    st.title("CHIP")
    logger.info("Main application UI rendered.")

    prefix = st.session_state.key_prefix
    skill_key = f"{prefix}_selected_skill"

    # --- REMOVED: Database Table Initialization Check ---
    # We assume the table is created manually in Supabase dashboard.
    # If needed, you could add a check here to ensure the client connects,
    # but table existence check via client isn't straightforward.
    # supabase = get_supabase_client()
    # if supabase is None:
    #     st.error("Failed to connect to Supabase. Feedback saving will not work.")
    #     # Optionally stop the app
    #     # st.stop()

    st.write("Select Skill to Practice:")
    # [ Skill selection buttons remain the same ]
    cols_row1 = st.columns(3)
    cols_row2 = st.columns(3)
    current_selection = st.session_state.get(skill_key, SKILLS[0])

    def handle_skill_click(skill_name):
        if skill_name != st.session_state.get(skill_key):
            logger.info(f"Skill selected: {skill_name}")
            st.session_state[skill_key] = skill_name
            reset_skill_state()
            st.rerun()
        else:
            logger.debug(f"Clicked already selected skill: {skill_name}")

    button_map = {
        SKILLS[0]: cols_row1[0], SKILLS[1]: cols_row1[1], SKILLS[2]: cols_row1[2],
        SKILLS[3]: cols_row2[0], SKILLS[4]: cols_row2[1]
    }
    for skill, col in button_map.items():
        with col:
            button_type = "primary" if skill == current_selection else "secondary"
            if st.button(skill, key=f"skill_btn_{skill.replace(' ', '_')}", use_container_width=True, type=button_type):
                handle_skill_click(skill)

    st.divider()
    selected_skill = st.session_state.get(skill_key, SKILLS[0])
    logger.debug(f"Loading UI for skill: {selected_skill}")

    # --- Routing to Skill UI Functions ---
    # [ Remains the same ]
    if selected_skill == "Clarifying Questions":
        clarifying_questions_bot_ui()
    elif selected_skill == "Framework Development":
        framework_development_ui()
    elif selected_skill == "Hypothesis Formulation":
        st.header("Hypothesis Formulation")
        st.info("This module is under construction. Check back later!")
        logger.info("Displayed 'Under Construction' for Hypothesis Formulation.")
    elif selected_skill == "Analysis":
        st.header("Analysis")
        st.info("This module is under construction. Check back later!")
        logger.info("Displayed 'Under Construction' for Analysis.")
    elif selected_skill == "Recommendation":
        st.header("Recommendation")
        st.info("This module is under construction. Check back later!")
        logger.info("Displayed 'Under Construction' for Recommendation.")
    else:
        logger.error(f"Invalid skill selected in main_app: {selected_skill}")
        st.error("Invalid skill selected.")


# --- Skill-Specific UI Functions (clarifying_questions_bot_ui, framework_development_ui) ---
# Ensure these functions call the UPDATED save_user_feedback which now uses Supabase.
# The internal logic of the UI functions remains the same as the previous version,
# only the backend function called for saving feedback has changed.

def clarifying_questions_bot_ui():
    logger.info("Loading Clarifying Questions UI.")
    prefix = st.session_state.key_prefix
    # [ Define keys, initialize state, show donation dialog, select prompt - all same as previous version ]
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    show_donation_dialog_key = f"{prefix}_show_donation_dialog"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)

    # --- Show Donation Dialog ---
    if st.session_state.get(show_donation_dialog_key):
        logger.info("Displaying donation dialog.")
        if hasattr(st, 'dialog'):
            @st.dialog("Support CHIP!")
            def show_donation():
                st.write(
                    "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
                    "Consider making a small donation (suggested $5) to help cover server and API costs."
                )
                col1, col2, col3 = st.columns([0.5, 3, 0.5])
                with col2:
                     st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary", use_container_width=True)
                if st.button("Maybe later", key="maybe_later_btn_cq", use_container_width=True): # Unique key
                    logger.info("User clicked 'Maybe later' on donation dialog.")
                    st.session_state[show_donation_dialog_key] = False
                    st.rerun()
            show_donation()
        else: # Fallback
            with st.container(border=True):
                st.success("Love CHIP? ...")
                st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary")
            st.session_state[show_donation_dialog_key] = False

    # --- Select and Display Case Prompt ---
    if st.session_state.get(current_prompt_id_key) is None:
        logger.info("No current prompt ID, selecting new one.")
        selected_id = select_new_prompt(); st.session_state[current_prompt_id_key] = selected_id
    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt:
        logger.error(f"Could not load details for prompt ID: {st.session_state.get(current_prompt_id_key)}")
        st.error("Could not load the current case prompt details..."); st.stop() # Simplified error handling
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt: {case_title}")

    # --- Main Interaction Area ---
    if not st.session_state.get(done_key):
        # [ Interaction logic remains the same: End button, chat history, chat input ]
        st.header("Ask Clarifying Questions"); st.caption("...")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            if st.button("End Clarification Questions", use_container_width=True):
                logger.info("User clicked 'End Clarification Questions'.")
                # [ Time calculation, run count increment, donation check logic remains the same ]
                end_time = time.time(); start_time = st.session_state.get(start_time_key)
                if start_time is not None: st.session_state[time_key] = end_time - start_time
                else: st.session_state[time_key] = 0.0
                st.session_state[done_key] = True
                current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                st.session_state[run_count_key] = current_session_run_count
                logger.info(f"Session run count incremented to: {current_session_run_count}")
                if current_session_run_count == 2 or current_session_run_count == 11:
                     st.session_state[show_donation_dialog_key] = True
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
        # Chat input
        user_question = st.chat_input("Type your question here...", key=f"{prefix}_chat_input_cq", disabled=st.session_state.get(is_typing_key, False))
        if user_question: send_question(user_question, case_prompt_text)

    # --- Feedback and Conclusion Area ---
    if st.session_state.get(done_key):
        logger.debug("Entering feedback and conclusion area.")
        final_feedback_content = generate_final_feedback(case_prompt_text)
        feedback_was_generated = final_feedback_content and not str(final_feedback_content).startswith("Error") and not str(final_feedback_content).startswith("[Feedback")

        if feedback_was_generated:
            st.divider(); st.markdown(final_feedback_content); st.divider()
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
                        if save_user_feedback(user_feedback_data): logger.info("User Feedback Auto-Submitted (Rating >= 4) and saved.")
                        else: logger.error("User Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE TO DB.")
                        st.rerun()
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
                            if save_user_feedback(user_feedback_data): logger.info("User Feedback Submitted with Comment and saved.")
                            else: logger.error("User Feedback Submitted with Comment but FAILED TO SAVE TO DB.")
                            st.rerun()
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
    logger.info("Loading Framework Development UI.")
    prefix = st.session_state.key_prefix
    # [ Define keys, initialize state, show donation dialog, select prompt - all same as previous version ]
    done_key = f"{prefix}_done_asking"; time_key = f"{prefix}_total_time"; start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"; is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"; run_count_key = f"{prefix}_run_count"
    show_comment_key = f"{prefix}_show_comment_box"; feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    show_donation_dialog_key = f"{prefix}_show_donation_dialog"
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False); init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False); init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None); init_session_state_key('current_prompt_id', None)

    # --- Show Donation Dialog ---
    if st.session_state.get(show_donation_dialog_key):
        logger.info("Displaying donation dialog (Framework Dev).")
        if hasattr(st, 'dialog'):
            @st.dialog("Support CHIP!") # Duplicated dialog function definition
            def show_donation(): # Name collision if not careful, but Streamlit handles scope
                st.write("Love CHIP? ...")
                col1, col2, col3 = st.columns([0.5, 3, 0.5]);
                with col2: st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary", use_container_width=True)
                if st.button("Maybe later", key="maybe_later_btn_fw", use_container_width=True): # Unique key
                    logger.info("User clicked 'Maybe later' on donation dialog (Framework Dev).")
                    st.session_state[show_donation_dialog_key] = False; st.rerun()
            show_donation()
        else: # Fallback
             with st.container(border=True): st.success("Love CHIP? ..."); st.link_button("Donate...", type="primary")
             st.session_state[show_donation_dialog_key] = False

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

    # --- Main Interaction Area (Framework Development) ---
    if not st.session_state.get(done_key):
        # [ Interaction logic remains the same: Text area, Submit button, History, Final Feedback button ]
        st.header("Develop Your Framework"); st.caption("...")
        framework_input = st.text_area("Enter your framework here:", height=200, key=f"{prefix}_framework_input", placeholder="...", disabled=st.session_state.get(is_typing_key, False))
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            if st.button("Submit Framework for Feedback", use_container_width=True, disabled=not framework_input.strip()):
                logger.info("User submitted framework.")
                if st.session_state.get(start_time_key) is None: st.session_state[start_time_key] = time.time(); logger.info("Framework interaction timer started.")
                send_question(framework_input, case_prompt_text) # Gets initial assessment
        # Display Conversation History
        chat_container = st.container()
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role"); display_role = "user" if role == "interviewee" else "assistant"
                     with st.chat_message(display_role):
                         st.markdown(f"**{'Your Framework Submission' if role == 'interviewee' else 'Interviewer Feedback'}**"); st.markdown(msg.get("content", ""))
                         if role == "interviewer" and msg.get("assessment"):
                            with st.expander("View Assessment Details", expanded=False): st.markdown(msg.get("assessment"))
        # Typing indicator
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key): typing_placeholder.text("CHIP is analyzing your framework...")
        else: typing_placeholder.empty()
        # Final Feedback button
        if st.session_state.get(conv_key):
             col_fbtn1, col_fbtn2, col_fbtn3 = st.columns([1, 1.5, 1])
             with col_fbtn2:
                 if st.button("Get Final Summary Feedback", use_container_width=True):
                     logger.info("User requested final framework feedback.")
                     # [ Time calculation, run count increment, donation check logic remains the same ]
                     end_time = time.time(); start_time = st.session_state.get(start_time_key)
                     if start_time is not None: st.session_state[time_key] = end_time - start_time
                     else: st.session_state[time_key] = 0.0
                     st.session_state[done_key] = True
                     current_session_run_count = st.session_state.get(run_count_key, 0) + 1
                     st.session_state[run_count_key] = current_session_run_count
                     logger.info(f"Session run count incremented to: {current_session_run_count} (Framework Dev)")
                     if current_session_run_count == 2 or current_session_run_count == 11: st.session_state[show_donation_dialog_key] = True
                     st.rerun()

    # --- Feedback and Conclusion Area (Framework Development) ---
    if st.session_state.get(done_key):
        logger.debug("Entering framework feedback and conclusion area.")
        final_feedback_content = generate_final_feedback(case_prompt_text)
        feedback_was_generated = final_feedback_content and not str(final_feedback_content).startswith("Error") and not str(final_feedback_content).startswith("[Feedback")

        if feedback_was_generated:
            st.divider(); st.header("Overall Framework Feedback"); st.markdown(final_feedback_content); st.divider()
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
                st.markdown("**How helpful was the overall framework feedback? ...**")
                cols = st.columns(5); selected_rating = 0; rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        if st.button('★' * (i + 1), key=f"{prefix}_fw_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"): # Unique key
                            selected_rating = i + 1; rating_clicked = True; logger.info(f"User clicked framework feedback rating: {selected_rating} stars.")

                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {"rating": selected_rating, "comment": "", "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                        st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                        if save_user_feedback(user_feedback_data): logger.info("User Framework Feedback Auto-Submitted (Rating >= 4) and saved.")
                        else: logger.error("User Framework Feedback Auto-Submitted (Rating >= 4) but FAILED TO SAVE TO DB.")
                        st.rerun()
                    else: st.session_state[show_comment_key] = True

                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(f"Comment for your {rating_display} rating:", key=f"{prefix}_fw_feedback_comment_input", placeholder="...") # Unique key
                    if st.button("Submit Rating and Comment", key=f"{prefix}_fw_submit_feedback_button"): # Unique key
                        if not feedback_comment.strip(): st.error("Comment cannot be empty...")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0: st.error("Invalid rating selected...")
                        else:
                            user_feedback_data = {"rating": current_rating_value, "comment": feedback_comment.strip(), "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"), "timestamp": time.time()}
                            st.session_state[user_feedback_key] = user_feedback_data; st.session_state[feedback_submitted_key] = True; st.session_state[show_comment_key] = False
                            if save_user_feedback(user_feedback_data): logger.info("User Framework Feedback Submitted with Comment and saved.")
                            else: logger.error("User Framework Feedback Submitted with Comment but FAILED TO SAVE TO DB.")
                            st.rerun()
        # [ Error/Warning display for feedback generation remains the same ]
        elif final_feedback_content and str(final_feedback_content).startswith("Error"): st.error(f"Could not display feedback: {final_feedback_content}")
        else: st.warning("Feedback is currently unavailable...")

        # [ Conclusion display remains the same ]
        st.divider(); st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds**...")
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_fw_practice_again"): # Unique key
                logger.info("User clicked 'Practice This Skill Again' for Framework Development.")
                reset_skill_state(); st.rerun()


# --- Entry Point ---
if __name__ == "__main__":
    # [ Initialization remains the same ]
    if 'key_prefix' not in st.session_state:
         st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    init_session_state_key('session_id', str(uuid.uuid4()))
    main_app()
    logger.info("--- Application Script Execution Finished ---")

