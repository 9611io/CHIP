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
# REMOVED @st.cache_resource as a debugging step for the TypeError
def get_supabase_client() -> Client | None:
    """Initializes and returns the Supabase client using secrets."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        # logger.info("Attempting to create Supabase client.") # Reduce noise during debug
        client: Client = create_client(url, key)
        # logger.info("Supabase client created successfully.") # Reduce noise during debug
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

# Simplified for debugging - only init keys needed for the core loop
init_session_state_key('conversation', [])
init_session_state_key('current_prompt_id', None)
init_session_state_key('is_typing', False)
init_session_state_key('used_prompt_ids', []) # Still needed for select_new_prompt


# --- Page Config ---
st.set_page_config(
    page_title="CHIP (Debug)", # Indicate debug mode
    page_icon="🤖",
    layout="centered"
)

# --- Custom CSS ---
# [Your CSS remains unchanged - Assuming it's not the cause for now]
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
# [ reset_skill_state is no longer called in this simplified version but kept for later ]
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
            try: del st.session_state[full_key]
            except KeyError: pass
    # Re-initialize essential keys
    init_session_state_key('conversation', []); init_session_state_key('done_asking', False)
    init_session_state_key('feedback_submitted', False); init_session_state_key('is_typing', False)
    init_session_state_key('feedback', None); init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None); init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0); init_session_state_key('user_feedback', None)
    init_session_state_key('current_prompt_id', None)


# --- UPDATED: Function to Save User Feedback to Supabase ---
# [ Kept for future use, but not called in this simplified version ]
def save_user_feedback(feedback_data):
    """
    Saves the user feedback to the configured Supabase database.
    Assumes a table named 'user_feedback' exists with matching columns.
    """
    prefix = st.session_state.key_prefix
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A") # Might be missing if skill selection removed
    prompt_id = feedback_data.get("prompt_id", "N/A")
    rating = feedback_data.get("rating")
    comment = feedback_data.get("comment", "")
    log_message = (f"Attempting to save USER_FEEDBACK via Supabase :: Skill: {selected_skill}, PromptID: {prompt_id}, Rating: {rating}, Comment: '{comment}'")
    logger.info(log_message)
    supabase = get_supabase_client()
    if supabase is None:
        logger.error("Cannot save feedback, Supabase client failed to initialize.")
        st.error("Failed to save feedback due to Supabase connection issue.")
        return False
    success = False
    try:
        data_to_insert = {"session_id": session_id, "skill": selected_skill, "prompt_id": prompt_id, "rating": rating, "comment": comment}
        response = supabase.table('user_feedback').insert(data_to_insert).execute()
        logger.info(f"Successfully saved feedback to Supabase for SessionID: {session_id}. Response: {response}")
        success = True
    except Exception as e:
        logger.exception(f"Supabase error saving feedback: {e}")
        error_details = str(e)
        if hasattr(e, 'details'): error_details = f"{e} - Details: {e.details}"
        elif hasattr(e, 'message'): error_details = f"{e} - Message: {e.message}"
        st.error(f"Database error saving feedback: {error_details}")
    return success


# --- Other Helper Functions ---
def select_new_prompt():
    """Selects a new random prompt, avoiding session repeats if possible."""
    prefix = st.session_state.key_prefix
    used_ids_key = f"{prefix}_used_prompt_ids"
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    init_session_state_key('used_prompt_ids', [])
    available_prompt_ids = [pid for pid in ALL_PROMPT_IDS if pid not in st.session_state[used_ids_key]]
    if not available_prompt_ids:
        logger.warning("All prompts seen in this session, allowing repeats.")
        # st.info("You've seen all available prompts in this session! Allowing repeats now.") # Removed for simplicity
        st.session_state[used_ids_key] = []
        available_prompt_ids = ALL_PROMPT_IDS
        if not available_prompt_ids:
            logger.error("Cannot select prompt - prompt list is empty."); st.error("Cannot select prompt - prompt list is empty."); return None
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
    # selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A") # Skill fixed in this debug version
    selected_skill = "Clarifying Questions" # Hardcoded for debug
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")

    if not question or not question.strip(): st.warning("Please enter a question."); logger.warning("User attempted to send empty question."); return
    if not current_case_prompt_text: st.error("Internal Error: No case prompt context."); logger.error("Internal Error: send_question called without case_prompt_text."); return

    st.session_state[is_typing_key] = True
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - User Input: '{question}'")
    st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": question})

    try:
        history_for_prompt = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.get(conv_key, [])[:-1]])
        # Only use Clarifying Questions prompt for this debug version
        prompt_for_llm = f"""
        You are a **strict** case interviewer simulator focusing ONLY on the clarifying questions phase...
        Current Case Prompt Context:
        {current_case_prompt_text}
        Conversation History So Far:
        {history_for_prompt}
        Interviewee's Latest Question:
        {question}
        Your Task: ... [Provide concise answer and rigorous assessment] ...
        ###ANSWER###
        [Your plausible answer here]
        ###ASSESSMENT###
        [Your brief but rigorous assessment...]
        """
        system_message = "You are a strict case interview simulator for clarifying questions..."

        # logger.debug(f"LLM Prompt:\n{prompt_for_llm}")
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt_for_llm}],
            max_tokens=350, temperature=0.5, stream=True
        )
        full_response = ""
        with st.spinner(f"CHIP is generating response..."): # Simplified spinner message
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
        st.session_state.setdefault(conv_key, []).append({"role": "interviewer", "content": f"Sorry, an error occurred... ({type(e).__name__})", "assessment": "N/A due to error."})
    finally:
        st.session_state[is_typing_key] = False
        st.rerun() # Still need rerun to display new message

# --- generate_final_feedback is no longer called in this simplified version but kept for later ---
def generate_final_feedback(current_case_prompt_text):
    """Generates overall feedback markdown based on the conversation history."""
    prefix = st.session_state.key_prefix; conv_key = f"{prefix}_conversation"; feedback_key = f"{prefix}_feedback"
    feedback_submitted_key = f"{prefix}_feedback_submitted"; selected_skill = "Clarifying Questions" # Hardcoded
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")
    logger.info(f"Skill: {selected_skill}, PromptID: {prompt_id} - Attempting to generate final feedback.")
    # ... [Rest of function kept for later, but won't be called in current flow] ...
    return "[Final feedback generation skipped in debug mode]"


# --- Main Streamlit Application Function (Simplified) ---
def main_app():
    """Main function - Simplified to only run Clarifying Questions."""
    st.title("CHIP (Debug Mode)")
    logger.info("Simplified main_app UI rendered.")

    # --- No Skill Selection ---
    # st.write("Select Skill to Practice:")
    # ... [Skill buttons removed] ...
    # st.divider()

    # --- Directly call the simplified UI ---
    clarifying_questions_bot_ui_simplified()


# --- SIMPLIFIED Skill-Specific UI Function ---
def clarifying_questions_bot_ui_simplified():
    """Simplified UI for Clarifying Questions - Debugging JS Error."""
    logger.info("Loading SIMPLIFIED Clarifying Questions UI.")
    prefix = st.session_state.key_prefix
    # Define needed keys
    conv_key = f"{prefix}_conversation"
    is_typing_key = f"{prefix}_is_typing"
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    # Initialize state (already done globally for this version)

    # --- Select and Display Case Prompt ---
    if st.session_state.get(current_prompt_id_key) is None:
        logger.info("No current prompt ID, selecting new one.")
        selected_id = select_new_prompt()
        if selected_id is None: st.error("Failed to select prompt."); st.stop()
        st.session_state[current_prompt_id_key] = selected_id # Ensure state is set

    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))
    if not current_prompt:
        logger.error(f"Could not load details for prompt ID: {st.session_state.get(current_prompt_id_key)}")
        st.error("Could not load the current case prompt details."); st.stop()
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A'); case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"): st.error(case_prompt_text); st.stop()
    else: st.info(f"**{case_title}**\n\n{case_prompt_text}"); logger.debug(f"Displayed prompt: {case_title}")

    # --- Main Interaction Area (No End Button, No Feedback) ---
    st.header("Ask Clarifying Questions (Debug Mode)")
    st.caption("Chat interaction only. No end state or feedback.")

    # Chat history display
    chat_container = st.container()
    with chat_container:
        conversation_history = st.session_state.get(conv_key, [])
        if isinstance(conversation_history, list):
             for msg in conversation_history:
                 role = msg.get("role"); display_role = "user" if role == "interviewee" else "assistant"
                 with st.chat_message(display_role):
                     st.markdown(msg.get("content", ""))
                     # Optionally show assessment inline for debug
                     if role == "interviewer" and msg.get("assessment"):
                         st.caption(f"Assessment: {msg.get('assessment')}")

    # Typing indicator
    typing_placeholder = st.empty()
    if st.session_state.get(is_typing_key): typing_placeholder.text("CHIP is thinking...")
    else: typing_placeholder.empty()

    # Chat input
    logger.debug("Attempting to render st.chat_input...") # Add log before chat_input
    try:
        user_question = st.chat_input(
            "Type your question here...",
            key=f"{prefix}_chat_input_cq_debug", # Use unique key
            disabled=st.session_state.get(is_typing_key, False)
        )
        if user_question:
            logger.debug(f"st.chat_input received question: '{user_question}'")
            if st.session_state.get(is_typing_key):
                typing_placeholder.empty()
            send_question(user_question, case_prompt_text)
        # else:
            # logger.debug("st.chat_input rendered, no question entered.") # Log if rendered without input
    except Exception as e:
        logger.exception("ERROR rendering or processing st.chat_input!")
        st.error(f"Error with chat input: {e}")

# --- framework_development_ui function commented out for debug ---
# def framework_development_ui():
#    ...

# --- Entry Point ---
if __name__ == "__main__":
    # [ Initialization remains the same ]
    if 'key_prefix' not in st.session_state:
         st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    init_session_state_key('session_id', str(uuid.uuid4()))
    main_app() # Calls the simplified main_app
    logger.info("--- Application Script Execution Finished ---")

