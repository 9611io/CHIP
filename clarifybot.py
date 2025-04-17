import streamlit as st
import time
import uuid
import openai
import os
import re
import json
import random
import logging # Added for logging
import datetime # Added for logging timestamp

# --- Basic Logging Setup ---
# Configure logging to write to a file and include timestamps
log_filename = f"chip_app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename), # Log to a file
        logging.StreamHandler() # Also log to console/terminal
    ]
)
logger = logging.getLogger(__name__)
logger.info("--- Application Started ---")

# --- Page Config (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(
    page_title="CHIP",
    page_icon="🤖",
    layout="centered"
)

# --- Custom CSS Injection for Styling ---
# [CSS Remains the same as your provided version]
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
     div[data-testid="stButton"] > button[key="maybe_later_btn"] {
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
     div[data-testid="stButton"] > button[key="maybe_later_btn"]:hover {
         background: none !important;
         color: #FF4B4B !important; /* Primary color on hover */
         text-decoration: underline !important;
         transform: none !important; /* No scaling */
     }
     div[data-testid="stButton"] > button[key="maybe_later_btn"]:active {
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


# --- Configuration ---
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


# --- Session State Initialization ---
if 'key_prefix' not in st.session_state:
    st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    logger.info(f"Initialized new session with prefix: {st.session_state.key_prefix}")

def init_session_state_key(key, default_value):
    """Initializes session state key with prefix if not present."""
    full_key = f"{st.session_state.key_prefix}_{key}"
    if full_key not in st.session_state:
        st.session_state[full_key] = default_value

# Define available skills
SKILLS = ["Clarifying Questions", "Framework Development", "Hypothesis Formulation", "Analysis", "Recommendation"]

# Initialize common session state keys (skill-specific ones are initialized within their UI functions)
init_session_state_key('selected_skill', SKILLS[0])
init_session_state_key('run_count', 0) # Tracks total runs across skills in a session
init_session_state_key('show_donation_dialog', False)
# Add session ID for logging correlation
init_session_state_key('session_id', str(uuid.uuid4()))
logger.info(f"Session ID: {st.session_state.get(f'{st.session_state.key_prefix}_session_id', 'N/A')}")


# --- Helper Functions ---

def reset_skill_state():
    """Resets state variables specific to a practice run within a skill."""
    prefix = st.session_state.key_prefix
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "Unknown")
    logger.info(f"Resetting state for skill change to: {selected_skill}")

    # Define keys potentially used by ANY skill module that need resetting
    keys_to_reset = [
        'current_prompt_id', 'conversation', 'done_asking',
        'feedback_submitted', 'user_feedback', 'interaction_start_time',
        'total_time', 'is_typing', 'feedback',
        'show_comment_box', 'feedback_rating_value',
        # Add any other skill-specific keys here if needed
    ]
    logger.info(f"Resetting state keys: {keys_to_reset}")
    for key in keys_to_reset:
        full_key = f"{prefix}_{key}"
        if full_key in st.session_state:
            try:
                del st.session_state[full_key]
                # logger.debug(f"Deleted state key: {full_key}") # Verbose debug
            except KeyError:
                # logger.warning(f"Key {full_key} not found during reset, skipping.")
                pass # Ignore if key doesn't exist

    # Re-initialize essential keys after deletion to ensure they exist
    # (Skill-specific UI functions should handle their own specific initializations)
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
    init_session_state_key('current_prompt_id', None) # Ensure prompt is re-selected

# --- NEW: Function to Save/Log User Feedback ---
def save_user_feedback(feedback_data):
    """
    Logs the user feedback.
    In a production environment, this would send data to a database, API, or persistent file storage.
    """
    prefix = st.session_state.key_prefix
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = feedback_data.get("prompt_id", "N/A")
    rating = feedback_data.get("rating", "N/A")
    comment = feedback_data.get("comment", "")
    timestamp = feedback_data.get("timestamp", time.time())
    dt_object = datetime.datetime.fromtimestamp(timestamp)

    log_message = (
        f"USER_FEEDBACK :: SessionID: {session_id}, Skill: {selected_skill}, "
        f"PromptID: {prompt_id}, Rating: {rating}, Comment: '{comment}', "
        f"Timestamp: {dt_object.isoformat()}"
    )
    logger.info(log_message)

    # Placeholder for persistent storage:
    # try:
    #     # Example: Append to a CSV file
    #     feedback_file = "user_feedback.csv"
    #     file_exists = os.path.isfile(feedback_file)
    #     with open(feedback_file, 'a', newline='', encoding='utf-8') as f:
    #         writer = csv.writer(f)
    #         if not file_exists:
    #              writer.writerow(["SessionID", "Skill", "PromptID", "Rating", "Comment", "Timestamp"]) # Header
    #         writer.writerow([session_id, selected_skill, prompt_id, rating, comment, dt_object.isoformat()])
    #     logger.info(f"Successfully appended feedback to {feedback_file}")
    # except Exception as e:
    #     logger.error(f"Failed to save feedback to file: {e}")

    # Example: Send to an API endpoint
    # try:
    #     response = requests.post("YOUR_API_ENDPOINT", json=feedback_data)
    #     response.raise_for_status() # Raise an exception for bad status codes
    #     logger.info("Successfully sent feedback to API.")
    # except requests.exceptions.RequestException as e:
    #     logger.error(f"Failed to send feedback to API: {e}")


def select_new_prompt():
    """Selects a new random prompt, avoiding session repeats if possible."""
    prefix = st.session_state.key_prefix
    used_ids_key = f"{prefix}_used_prompt_ids"
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")

    init_session_state_key('used_prompt_ids', []) # Ensure it exists

    available_prompt_ids = [pid for pid in ALL_PROMPT_IDS if pid not in st.session_state[used_ids_key]]

    if not available_prompt_ids:
        logger.warning(f"SessionID: {session_id} - All prompts seen in this session, allowing repeats.")
        st.info("You've seen all available prompts in this session! Allowing repeats now.")
        st.session_state[used_ids_key] = []
        available_prompt_ids = ALL_PROMPT_IDS
        if not available_prompt_ids:
            logger.error(f"SessionID: {session_id} - Cannot select prompt - prompt list is empty.")
            st.error("Cannot select prompt - prompt list is empty.")
            return None

    selected_id = random.choice(available_prompt_ids)
    st.session_state[used_ids_key].append(selected_id)
    st.session_state[current_prompt_id_key] = selected_id
    logger.info(f"SessionID: {session_id} - Selected Prompt ID: {selected_id}")
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
    # Increased robustness: handle potential whitespace variations
    answer_match = re.search(r"###ANSWER###\s*(.*?)\s*###ASSESSMENT###", response_text, re.DOTALL | re.IGNORECASE)
    assessment_match = re.search(r"###ASSESSMENT###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)

    if answer_match:
        answer = answer_match.group(1).strip()
    if assessment_match:
        assessment = assessment_match.group(1).strip()

    # Log parsing issues
    if not answer_match and not assessment_match and response_text:
        answer = response_text.strip() # Assume entire response is the answer if delimiters fail
        assessment = "[Assessment not extracted - delimiters missing]"
        logger.warning(f"Could not find delimiters in LLM response: '{response_text[:100]}...'")
    elif answer_match and not assessment_match:
         assessment = "[Assessment delimiter missing]"
         logger.warning(f"Found ###ANSWER### but not ###ASSESSMENT### in LLM response.")
    elif not answer_match and assessment_match:
         answer = "[Answer delimiter missing]"
         logger.warning(f"Found ###ASSESSMENT### but not ###ANSWER### in LLM response.")
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
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")

    if not question or not question.strip():
        st.warning("Please enter a question.")
        logger.warning(f"SessionID: {session_id} - User attempted to send empty question.")
        return
    if not current_case_prompt_text:
        st.error("Internal Error: Cannot send question without case prompt context.")
        logger.error(f"SessionID: {session_id} - Internal Error: send_question called without case_prompt_text.")
        return

    st.session_state[is_typing_key] = True

    # Log user question
    logger.info(f"SessionID: {session_id}, Skill: {selected_skill}, PromptID: {prompt_id} - User Question: '{question}'")

    st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": question})

    try:
        # Prepare history for the LLM prompt
        history_for_prompt = "\n".join(
            [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.get(conv_key, [])[:-1]] # Exclude the latest question
        )

        # --- Define LLM Prompt based on Skill ---
        # This section might need refinement as other skills are added
        if selected_skill == "Clarifying Questions":
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

        # --- Placeholder for Framework Development LLM Call ---
        elif selected_skill == "Framework Development":
             # NOTE: This prompt needs to be fully developed for framework evaluation
             prompt_for_llm = f"""
             You are a case interview coach evaluating a candidate's proposed framework.

             Case Prompt Context:
             {current_case_prompt_text}

             Candidate's Proposed Framework/Approach:
             {question}  # Assuming the user types their framework here

             Your Task:
             1. Acknowledge the framework briefly.
             2. Provide a structured assessment of the framework covering: MECE (Mutually Exclusive, Collectively Exhaustive), Relevance to the case, Prioritization, Actionability.
             3. Suggest 1-2 specific improvements or alternative considerations.
             4. Use the following exact format:

             ###ANSWER###
             [Your brief acknowledgement]
             ###ASSESSMENT###
             [Your structured assessment and suggestions]
             """
             system_message = "You are a case interview coach evaluating framework proposals. Provide structured feedback using the specified format."
             # TODO: Implement the actual logic and UI for framework input/display


        else:
            # Fallback for unhandled skills
            logger.error(f"SessionID: {session_id} - Attempted to send question for unhandled skill: {selected_skill}")
            st.error(f"Interaction logic for '{selected_skill}' is not yet implemented.")
            st.session_state.setdefault(conv_key, []).append({
                "role": "interviewer",
                "content": f"Sorry, the interaction for '{selected_skill}' is not ready yet.",
                "assessment": "N/A"
            })
            st.session_state[is_typing_key] = False
            st.rerun()
            return # Stop processing for this case

        # logger.debug(f"SessionID: {session_id} - LLM Prompt:\n{prompt_for_llm}") # Uncomment for verbose debugging

        response = client.chat.completions.create(
            model="gpt-4o-mini", # Consider using GPT-4 for more complex skills if needed
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt_for_llm},
            ],
            max_tokens=350, # Slightly increased for potentially more complex answers/assessments
            temperature=0.5,
            stream=True
        )

        full_response = ""
        with st.spinner(f"CHIP is generating response for {selected_skill}..."):
             for chunk in response:
                 if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                     full_response += chunk.choices[0].delta.content

        # logger.debug(f"SessionID: {session_id} - Full LLM Response:\n{full_response}") # Uncomment for verbose debugging

        interviewer_answer, interviewer_assessment = parse_interviewer_response(full_response)

        # Log LLM response
        logger.info(f"SessionID: {session_id}, Skill: {selected_skill}, PromptID: {prompt_id} - LLM Answer: '{interviewer_answer[:100]}...'")
        logger.info(f"SessionID: {session_id}, Skill: {selected_skill}, PromptID: {prompt_id} - LLM Assessment: '{interviewer_assessment[:100]}...'")


        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer",
            "content": interviewer_answer,
            "assessment": interviewer_assessment
        })

    except Exception as e:
        logger.exception(f"SessionID: {session_id} - Error generating LLM response: {e}")
        st.error(f"Error generating response: {e}")
        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer",
            "content": f"Sorry, an error occurred while generating the response. Please try again or restart. ({type(e).__name__})",
            "assessment": "N/A due to error."
        })
    finally:
        st.session_state[is_typing_key] = False
        st.rerun() # Update UI


def generate_final_feedback(current_case_prompt_text):
    """Generates overall feedback markdown based on the conversation history."""
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    feedback_key = f"{prefix}_feedback"
    feedback_submitted_key = f"{prefix}_feedback_submitted"
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")
    selected_skill = st.session_state.get(f"{prefix}_selected_skill", "N/A")
    prompt_id = st.session_state.get(f"{prefix}_current_prompt_id", "N/A")

    logger.info(f"SessionID: {session_id}, Skill: {selected_skill}, PromptID: {prompt_id} - Attempting to generate final feedback.")

    existing_feedback = st.session_state.get(feedback_key)
    feedback_submitted = st.session_state.get(feedback_submitted_key, False)

    # Skipping logic
    if feedback_submitted:
         logger.info(f"SessionID: {session_id} - Skipping feedback gen: Feedback already submitted by user.")
         # Return existing feedback if it was generated before submission, otherwise None
         return existing_feedback
    if existing_feedback is not None:
        logger.info(f"SessionID: {session_id} - Skipping feedback gen: Feedback key exists and is not None (already generated or error occurred).")
        return existing_feedback
    if not st.session_state.get(conv_key):
        logger.warning(f"SessionID: {session_id} - Skipping feedback gen: No conversation history.")
        return None # Cannot generate feedback without conversation

    with st.spinner(f"Generating Final Feedback for {selected_skill}..."):
        try:
            formatted_history = []
            conversation_history = st.session_state.get(conv_key, [])
            if not isinstance(conversation_history, list):
                logger.error(f"SessionID: {session_id} - Internal Error: Conversation history format issue. Type: {type(conversation_history)}")
                st.error("Internal Error: Conversation history format issue.")
                st.session_state[feedback_key] = "Error: Could not generate feedback due to history format."
                return st.session_state[feedback_key]

            # Format history including assessments
            for i, msg in enumerate(conversation_history):
                role = msg.get("role")
                content = msg.get("content", "[missing content]")
                if role == 'interviewee':
                    # Determine question number (integer division by 2, plus 1)
                    q_num = (i // 2) + 1
                    formatted_history.append(f"Interviewee Input {q_num}: {content}")
                elif role == 'interviewer':
                    # Response corresponds to the previous question number
                    q_num = (i // 2) + 1
                    formatted_history.append(f"Interviewer Response to Input {q_num}: {content}")
                    assessment = msg.get('assessment')
                    if assessment:
                        formatted_history.append(f" -> Interviewer's Assessment of Input {q_num}: {assessment}")

            history_string = "\n\n".join(formatted_history)

            # --- Define Feedback Prompt based on Skill ---
            if selected_skill == "Clarifying Questions":
                feedback_prompt = f"""
                You are an experienced case interview coach providing feedback on the clarifying questions phase ONLY.

                Case Prompt Context for this Session:
                {current_case_prompt_text}

                Interview Interaction History (including interviewer's assessment of each question):
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

            elif selected_skill == "Framework Development":
                 # NOTE: This feedback prompt needs to be tailored for framework evaluation
                 feedback_prompt = f"""
                 You are an experienced case interview coach providing feedback on the framework development phase.

                 Case Prompt Context for this Session:
                 {current_case_prompt_text}

                 Interaction History (Candidate's framework proposal(s) and interviewer's assessments):
                 {history_string}

                 Your Task:
                 Provide detailed, professional feedback on the candidate's framework(s). Use markdown formatting.

                 Structure your feedback precisely as follows:

                 ## Overall Framework Rating: [1-5]/5
                 *(Justify the rating based on MECE, Relevance, Prioritization, Actionability, and Clarity)*

                 ---

                 1.  **Overall Summary:** Summarize the effectiveness of the proposed framework(s) for this case.
                 2.  **Strengths:** Identify 1-2 specific strengths (e.g., good structure, relevant buckets, clear logic).
                 3.  **Areas for Improvement:** Identify 1-2 key weaknesses (e.g., not MECE, missing key areas, poor prioritization, too generic).
                 4.  **Actionable Next Steps:** Provide 2 concrete steps to improve framework development skills.
                 5.  **Example Refinement:** Suggest a specific refinement or alternative structure for the framework proposed in *this case*.

                 **Rating Criteria Reference:**
                    * 1: Fundamentally flawed. Not MECE, irrelevant, unclear, unusable.
                    * 2: Major issues. Significant gaps, poor structure, lacks relevance or actionability.
                    * 3: Partially effective. Some relevant components but structure could be much better (e.g., not fully MECE, poor prioritization).
                    * 4: Good framework. Mostly MECE, relevant, actionable, and well-prioritized, with minor refinements possible.
                    * 5: Excellent. Clear, MECE, highly relevant, well-prioritized, actionable, and tailored to the case specifics.

                 Start directly with the '## Overall Framework Rating:' heading.
                 """
                 system_message_feedback = "You are an expert case interview coach providing structured feedback on framework development. Start directly with the '## Overall Framework Rating:' heading. Evaluate critically based on history and assessments. Use markdown effectively."
                 max_tokens_feedback = 700 # Adjust as needed

            else:
                logger.error(f"SessionID: {session_id} - Cannot generate feedback for unhandled skill: {selected_skill}")
                st.error(f"Feedback generation for '{selected_skill}' is not yet implemented.")
                st.session_state[feedback_key] = f"Error: Feedback generation not implemented for {selected_skill}."
                return st.session_state[feedback_key]


            logger.info(f"SessionID: {session_id} - Calling OpenAI API for final feedback...")
            feedback_response = client.chat.completions.create(
                model="gpt-4o-mini", # Or GPT-4 if needed
                messages=[
                    {"role": "system", "content": system_message_feedback},
                    {"role": "user", "content": feedback_prompt},
                ],
                max_tokens=max_tokens_feedback,
                temperature=0.5,
            )
            feedback = feedback_response.choices[0].message.content.strip()
            logger.info(f"SessionID: {session_id} - Feedback received from API (first 100 chars): {feedback[:100]}")

            if feedback:
                 st.session_state[feedback_key] = feedback
            else:
                 logger.warning(f"SessionID: {session_id} - LLM returned empty feedback.")
                 st.session_state[feedback_key] = "[Feedback generation returned empty]"
            return st.session_state[feedback_key]

        except Exception as e:
            logger.exception(f"SessionID: {session_id} - Error during feedback generation API call: {e}")
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
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")

    st.write("Select Skill to Practice:")

    # Skill Selection Buttons
    cols_row1 = st.columns(3)
    cols_row2 = st.columns(3)
    current_selection = st.session_state.get(skill_key, SKILLS[0])

    # Function to handle button click logic
    def handle_skill_click(skill_name):
        if skill_name != st.session_state.get(skill_key):
            logger.info(f"SessionID: {session_id} - Skill selected: {skill_name}")
            st.session_state[skill_key] = skill_name
            reset_skill_state()
            st.rerun()
        else:
            logger.debug(f"SessionID: {session_id} - Clicked already selected skill: {skill_name}")

    # Create buttons
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

    # Display Selected Skill UI
    selected_skill = st.session_state.get(skill_key, SKILLS[0])
    logger.debug(f"SessionID: {session_id} - Loading UI for skill: {selected_skill}")

    if selected_skill == "Clarifying Questions":
        clarifying_questions_bot_ui()
    elif selected_skill == "Framework Development":
        framework_development_ui() # Call the new UI function
    elif selected_skill == "Hypothesis Formulation":
        st.header("Hypothesis Formulation")
        st.info("This module is under construction. Check back later!")
        logger.info(f"SessionID: {session_id} - Displayed 'Under Construction' for Hypothesis Formulation.")
    elif selected_skill == "Analysis":
        st.header("Analysis")
        st.info("This module is under construction. Check back later!")
        logger.info(f"SessionID: {session_id} - Displayed 'Under Construction' for Analysis.")
    elif selected_skill == "Recommendation":
        st.header("Recommendation")
        st.info("This module is under construction. Check back later!")
        logger.info(f"SessionID: {session_id} - Displayed 'Under Construction' for Recommendation.")
    else:
        logger.error(f"SessionID: {session_id} - Invalid skill selected in main_app: {selected_skill}")
        st.error("Invalid skill selected.")


# --- Skill-Specific UI Function (Clarifying Questions) ---
def clarifying_questions_bot_ui():
    """Defines the Streamlit UI and logic SPECIFICALLY for the Clarifying Questions skill."""
    logger.info("Loading Clarifying Questions UI.")
    prefix = st.session_state.key_prefix
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")

    # Define Session State Keys specific to this skill
    done_key = f"{prefix}_done_asking"
    time_key = f"{prefix}_total_time"
    start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"
    feedback_key = f"{prefix}_feedback"
    is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"
    user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    run_count_key = f"{prefix}_run_count" # Session state run count (global)
    show_comment_key = f"{prefix}_show_comment_box"
    feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    show_donation_dialog_key = f"{prefix}_show_donation_dialog" # Key for dialog

    # Initialize skill-specific state if needed (reset_skill_state clears most)
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


    # --- Show Donation Dialog ---
    if st.session_state.get(show_donation_dialog_key):
        logger.info(f"SessionID: {session_id} - Displaying donation dialog.")
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
                if st.button("Maybe later", key="maybe_later_btn", use_container_width=True):
                    logger.info(f"SessionID: {session_id} - User clicked 'Maybe later' on donation dialog.")
                    st.session_state[show_donation_dialog_key] = False
                    st.rerun()
            show_donation()
        else:
            # Fallback if st.dialog is not available
            with st.container(border=True):
                st.success(
                    "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
                    "Consider making a small donation (suggested $5) to help cover server and API costs."
                )
                st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary")
            st.session_state[show_donation_dialog_key] = False # Hide after showing fallback


    # --- Select and Display Case Prompt ---
    if st.session_state.get(current_prompt_id_key) is None:
        logger.info(f"SessionID: {session_id} - No current prompt ID, selecting new one.")
        selected_id = select_new_prompt()
        if selected_id is None:
             st.error("Failed to select a new prompt. Please check prompt file.")
             st.stop()
        # Ensure state is updated before proceeding
        st.session_state[current_prompt_id_key] = selected_id

    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))

    if not current_prompt:
        logger.error(f"SessionID: {session_id} - Could not load details for prompt ID: {st.session_state.get(current_prompt_id_key)}")
        st.error("Could not load the current case prompt details. Please try restarting.")
        if st.button("Restart This Skill Practice"):
             logger.warning(f"SessionID: {session_id} - Restarting skill due to prompt load failure.")
             reset_skill_state()
             st.rerun()
        st.stop()

    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A')
    case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"):
        logger.error(f"SessionID: {session_id} - Displaying prompt text error: {case_prompt_text}")
        st.error(case_prompt_text)
        st.stop()
    else:
        st.info(f"**{case_title}**\n\n{case_prompt_text}")
        logger.debug(f"SessionID: {session_id} - Displayed prompt: {case_title}")


    # --- Main Interaction Area ---
    if not st.session_state.get(done_key):
        st.header("Ask Clarifying Questions")
        st.caption("Ask questions below. Click 'End Clarification Questions' when finished.")

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            if st.button("End Clarification Questions", use_container_width=True):
                logger.info(f"SessionID: {session_id} - User clicked 'End Clarification Questions'.")
                end_time = time.time()
                start_time = st.session_state.get(start_time_key)
                if start_time is not None:
                    elapsed_time = end_time - start_time
                    st.session_state[time_key] = elapsed_time
                    logger.info(f"SessionID: {session_id} - Interaction ended. Time elapsed: {elapsed_time:.2f} seconds.")
                else:
                    st.session_state[time_key] = 0.0
                    logger.warning(f"SessionID: {session_id} - Interaction ended, but start time was not recorded.")
                st.session_state[done_key] = True

                # Increment Run Count and Trigger Dialog Check
                current_session_run_count = st.session_state.get(run_count_key, 0)
                new_session_run_count = current_session_run_count + 1
                st.session_state[run_count_key] = new_session_run_count
                logger.info(f"SessionID: {session_id} - Session run count incremented to: {new_session_run_count}")

                # Show donation prompt on 2nd and 11th completed run
                if new_session_run_count == 2 or new_session_run_count == 11:
                     st.session_state[show_donation_dialog_key] = True
                     logger.info(f"SessionID: {session_id} - Flag set to show donation dialog for achieving run count {new_session_run_count}")

                st.rerun() # Rerun to show feedback section

        # Record start time only once
        if st.session_state.get(start_time_key) is None:
            st.session_state[start_time_key] = time.time()
            logger.info(f"SessionID: {session_id} - Interaction timer started.")

        # Chat history display
        chat_container = st.container()
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role")
                     display_role = "user" if role == "interviewee" else "assistant"
                     with st.chat_message(display_role):
                         st.markdown(msg.get("content", ""))
                         # Optionally display assessment inline (could be verbose)
                         # if role == "interviewer" and msg.get("assessment"):
                         #    st.caption(f"Assessment: {msg.get('assessment')}")

        # Typing indicator
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key):
            typing_placeholder.text("CHIP is thinking...")
        else:
            typing_placeholder.empty()

        # Chat input
        user_question = st.chat_input(
            "Type your question here...",
            key=f"{prefix}_chat_input", # Use prefix in key
            disabled=st.session_state.get(is_typing_key, False)
        )

        if user_question:
            if st.session_state.get(is_typing_key):
                 typing_placeholder.empty() # Clear indicator if user types while processing (should be disabled, but belt-and-suspenders)
            send_question(user_question, case_prompt_text) # Function handles logging and state update


    # --- Feedback and Conclusion Area ---
    if st.session_state.get(done_key):
        logger.debug(f"SessionID: {session_id} - Entering feedback and conclusion area.")

        # Generate feedback (or retrieve existing)
        final_feedback_content = generate_final_feedback(case_prompt_text)
        # logger.debug(f"SessionID: {session_id} - Result from generate_final_feedback: '{str(final_feedback_content)[:100]}...'")

        feedback_was_generated = final_feedback_content and not str(final_feedback_content).startswith("Error") and not str(final_feedback_content).startswith("[Feedback")

        if feedback_was_generated:
            st.divider()
            with st.container():
                 st.markdown(final_feedback_content)
            st.divider()

            # --- User Feedback Section ---
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)

            if feedback_already_submitted:
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0)
                     st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'):
                         st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                # Display rating input
                st.markdown("**How helpful was the feedback provided above? (Click a star rating)**")
                st.write(" ") # Spacer
                cols = st.columns(5)
                selected_rating = 0
                rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        button_label = '★' * (i + 1)
                        if st.button(button_label, key=f"{prefix}_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"):
                            selected_rating = i + 1
                            rating_clicked = True
                            logger.info(f"SessionID: {session_id} - User clicked rating: {selected_rating} stars.")

                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4: # Auto-submit for 4 or 5 stars
                        user_feedback_data = {
                            "rating": selected_rating, "comment": "", # No comment needed
                            "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"),
                            "timestamp": time.time()
                        }
                        st.session_state[user_feedback_key] = user_feedback_data
                        st.session_state[feedback_submitted_key] = True
                        st.session_state[show_comment_key] = False
                        save_user_feedback(user_feedback_data) # <<< SAVE/LOG FEEDBACK
                        logger.info(f"SessionID: {session_id} - User Feedback Auto-Submitted (Rating >= 4): {user_feedback_data}")
                        st.rerun()
                    else: # Show comment box for 1-3 stars
                        st.session_state[show_comment_key] = True
                        # Don't rerun yet, let the comment box show below

                # Show comment box if needed (triggered by rating_clicked or already true)
                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(
                        f"Comment for your {rating_display} rating:",
                        key=f"{prefix}_feedback_comment_input",
                        placeholder="e.g., More specific examples, clearer actionable steps..."
                    )
                    if st.button("Submit Rating and Comment", key=f"{prefix}_submit_feedback_button"):
                        if not feedback_comment.strip():
                            st.error("Comment cannot be empty for ratings below 4 stars.")
                            logger.warning(f"SessionID: {session_id} - User tried to submit low rating feedback with empty comment.")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0:
                             st.error("Invalid rating selected. Please click a star rating again.")
                             logger.warning(f"SessionID: {session_id} - User tried to submit feedback with invalid rating value: {current_rating_value}")
                        else:
                            user_feedback_data = {
                                "rating": current_rating_value, "comment": feedback_comment.strip(),
                                "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"),
                                "timestamp": time.time()
                             }
                            st.session_state[user_feedback_key] = user_feedback_data
                            st.session_state[feedback_submitted_key] = True
                            st.session_state[show_comment_key] = False
                            save_user_feedback(user_feedback_data) # <<< SAVE/LOG FEEDBACK
                            logger.info(f"SessionID: {session_id} - User Feedback Submitted with Comment: {user_feedback_data}")
                            st.rerun()

        # Handle cases where feedback generation failed or was skipped
        elif final_feedback_content and str(final_feedback_content).startswith("Error"):
             st.error(f"Could not display feedback: {final_feedback_content}")
             logger.error(f"SessionID: {session_id} - Displaying feedback generation error: {final_feedback_content}")
        else:
            # Check state to provide more context for why feedback isn't shown
            if st.session_state.get(feedback_submitted_key):
                 st.warning("Feedback was submitted, but could not be displayed (an error likely occurred during generation).")
                 logger.warning(f"SessionID: {session_id} - Feedback unavailable, but feedback_submitted is True. Final content was: {final_feedback_content}")
            elif feedback_key in st.session_state and st.session_state[feedback_key] is None and st.session_state.get(conv_key):
                 st.warning("Feedback generation was skipped (e.g., already attempted or error occurred).")
                 logger.warning(f"SessionID: {session_id} - Feedback unavailable. Key exists but is None. Final content was: {final_feedback_content}")
            else:
                 st.warning("Feedback is currently unavailable (e.g., no conversation yet or generation failed).")
                 logger.warning(f"SessionID: {session_id} - Feedback unavailable. Final content was: {final_feedback_content}")


        # Conclusion Section (always shown when done_key is True)
        st.divider()
        st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** in the clarifying questions phase for this case.")
        logger.info(f"SessionID: {session_id} - Displayed conclusion. Total time: {total_interaction_time:.2f}s")

        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True):
                logger.info(f"SessionID: {session_id} - User clicked 'Practice This Skill Again' for Clarifying Questions.")
                reset_skill_state() # Use reset function
                st.rerun()

# --- NEW: Skill-Specific UI Function (Framework Development) ---
def framework_development_ui():
    """Defines the Streamlit UI and logic SPECIFICALLY for the Framework Development skill."""
    logger.info("Loading Framework Development UI.")
    prefix = st.session_state.key_prefix
    session_id = st.session_state.get(f"{prefix}_session_id", "N/A")

    # Define Session State Keys specific to this skill (mirroring clarifying_questions if applicable)
    done_key = f"{prefix}_done_asking" # Reuse name, but context is different (e.g., done submitting framework)
    time_key = f"{prefix}_total_time"
    start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation" # Stores framework attempts and feedback
    feedback_key = f"{prefix}_feedback" # Stores final LLM feedback on framework(s)
    is_typing_key = f"{prefix}_is_typing" # For LLM feedback generation
    feedback_submitted_key = f"{prefix}_feedback_submitted" # User rating of LLM feedback
    user_feedback_key = f"{prefix}_user_feedback" # User rating/comment data
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    run_count_key = f"{prefix}_run_count" # Global run count
    show_comment_key = f"{prefix}_show_comment_box" # For user feedback rating
    feedback_rating_value_key = f"{prefix}_feedback_rating_value" # For user feedback rating
    show_donation_dialog_key = f"{prefix}_show_donation_dialog" # Global dialog key

    # Initialize skill-specific state
    init_session_state_key('conversation', [])
    init_session_state_key('done_asking', False) # Represents finishing the framework attempt
    init_session_state_key('feedback_submitted', False)
    init_session_state_key('is_typing', False)
    init_session_state_key('feedback', None)
    init_session_state_key('show_comment_box', False)
    init_session_state_key('feedback_rating_value', None)
    init_session_state_key('interaction_start_time', None)
    init_session_state_key('total_time', 0.0)
    init_session_state_key('user_feedback', None)
    init_session_state_key('current_prompt_id', None)

    # --- Show Donation Dialog (copied logic) ---
    if st.session_state.get(show_donation_dialog_key):
        logger.info(f"SessionID: {session_id} - Displaying donation dialog (Framework Dev).")
        # [ Identical donation dialog code as in clarifying_questions_bot_ui ]
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
                if st.button("Maybe later", key="maybe_later_btn_fw", use_container_width=True): # Use different key
                    logger.info(f"SessionID: {session_id} - User clicked 'Maybe later' on donation dialog (Framework Dev).")
                    st.session_state[show_donation_dialog_key] = False
                    st.rerun()
            show_donation()
        else:
            # Fallback if st.dialog is not available
            with st.container(border=True):
                st.success(
                    "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
                    "Consider making a small donation (suggested $5) to help cover server and API costs."
                )
                st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary")
            st.session_state[show_donation_dialog_key] = False # Hide after showing fallback

    # --- Select and Display Case Prompt ---
    # TODO: Potentially filter prompts for those suitable for framework development?
    # For now, use the same prompt selection logic.
    if st.session_state.get(current_prompt_id_key) is None:
        logger.info(f"SessionID: {session_id} - No current prompt ID (Framework Dev), selecting new one.")
        selected_id = select_new_prompt()
        if selected_id is None:
             st.error("Failed to select a new prompt. Please check prompt file.")
             st.stop()
        st.session_state[current_prompt_id_key] = selected_id

    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))

    if not current_prompt:
        logger.error(f"SessionID: {session_id} - Could not load details for prompt ID (Framework Dev): {st.session_state.get(current_prompt_id_key)}")
        st.error("Could not load the current case prompt details. Please try restarting.")
        if st.button("Restart This Skill Practice"):
             logger.warning(f"SessionID: {session_id} - Restarting skill (Framework Dev) due to prompt load failure.")
             reset_skill_state()
             st.rerun()
        st.stop()

    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A')
    case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"):
        logger.error(f"SessionID: {session_id} - Displaying prompt text error (Framework Dev): {case_prompt_text}")
        st.error(case_prompt_text)
        st.stop()
    else:
        st.info(f"**{case_title}**\n\n{case_prompt_text}")
        logger.debug(f"SessionID: {session_id} - Displayed prompt (Framework Dev): {case_title}")


    # --- Main Interaction Area (Framework Development) ---
    if not st.session_state.get(done_key):
        st.header("Develop Your Framework")
        st.caption("Outline your framework structure below. Click 'Submit Framework' when ready for feedback.")

        # Use a text area for framework input
        framework_input = st.text_area(
            "Enter your framework here:",
            height=200,
            key=f"{prefix}_framework_input",
            placeholder="e.g.,\n1. Market Analysis\n   a. Market Size\n   b. Growth Rate\n   c. Trends\n2. Competitive Landscape\n   a. Key Competitors\n   b. Market Share\n   c. Strengths/Weaknesses\n3. Company Capabilities\n   a. ...",
            disabled=st.session_state.get(is_typing_key, False) # Disable while processing feedback
        )

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            # Button to submit the framework for evaluation
            if st.button("Submit Framework for Feedback", use_container_width=True, disabled=not framework_input.strip()):
                logger.info(f"SessionID: {session_id} - User submitted framework.")
                # Record start time if not already done (maybe less relevant here than continuous chat)
                if st.session_state.get(start_time_key) is None:
                    st.session_state[start_time_key] = time.time()
                    logger.info(f"SessionID: {session_id} - Framework interaction timer started.")

                # Call send_question (or a similar function tailored for framework submission)
                # The user's framework goes in the 'question' parameter
                send_question(framework_input, case_prompt_text)
                # Note: send_question now has basic logic for Framework Dev.
                # It will add the framework and the LLM's assessment to the conversation.
                # We might want to set done_key=True immediately after one submission,
                # or allow multiple iterations. For now, let's assume one submission.

                # Option 1: End interaction after one submission
                # end_time = time.time()
                # start_time = st.session_state.get(start_time_key)
                # if start_time: st.session_state[time_key] = end_time - start_time
                # st.session_state[done_key] = True
                # # Increment run count etc. (Consider if one framework attempt counts as a 'run')
                # st.rerun()

                # Option 2: Allow multiple submissions (don't set done_key here)
                # The user would see the feedback and could potentially refine/resubmit.
                # We'd need a separate "I'm finished" button.
                # For simplicity now, let's stick closer to the clarifying questions flow.
                # We'll assume the LLM response includes feedback, and then we show the final feedback section.

                # Let's set done_key=True after the response is received and displayed by send_question's rerun.
                # We need to trigger the final feedback generation *after* the assessment is shown.
                # Maybe add a button "Get Overall Feedback" after the first assessment?

                # --- Revised Flow: Submit -> Get Assessment -> Get Final Feedback ---
                # 1. User submits framework via text_area + button.
                # 2. `send_question` gets *initial* assessment, adds to chat, reruns.
                # 3. UI now shows the framework + assessment. Add a "Get Final Summary Feedback" button.

        # Display Conversation History (Framework attempts + Assessments)
        chat_container = st.container()
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role")
                     # Use 'user' for interviewee's framework, 'assistant' for feedback
                     display_role = "user" if role == "interviewee" else "assistant"
                     with st.chat_message(display_role):
                         st.markdown(f"**{'Your Framework Submission' if role == 'interviewee' else 'Interviewer Feedback'}**")
                         st.markdown(msg.get("content", ""))
                         # Display assessment clearly if it exists
                         if role == "interviewer" and msg.get("assessment"):
                            with st.expander("View Assessment Details", expanded=False):
                                st.markdown(msg.get("assessment"))

        # Typing indicator placeholder (for feedback generation)
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key):
            typing_placeholder.text("CHIP is analyzing your framework...")
        else:
            typing_placeholder.empty()

        # Add button to trigger final feedback generation *if* there's been at least one interaction
        if st.session_state.get(conv_key):
             col_fbtn1, col_fbtn2, col_fbtn3 = st.columns([1, 1.5, 1])
             with col_fbtn2:
                 if st.button("Get Final Summary Feedback", use_container_width=True):
                     logger.info(f"SessionID: {session_id} - User requested final framework feedback.")
                     end_time = time.time()
                     start_time = st.session_state.get(start_time_key)
                     if start_time is not None:
                         elapsed_time = end_time - start_time
                         st.session_state[time_key] = elapsed_time
                         logger.info(f"SessionID: {session_id} - Framework interaction ended. Time elapsed: {elapsed_time:.2f} seconds.")
                     else:
                         st.session_state[time_key] = 0.0
                         logger.warning(f"SessionID: {session_id} - Framework interaction ended, but start time was not recorded.")
                     st.session_state[done_key] = True

                     # Increment Run Count and Trigger Dialog Check
                     current_session_run_count = st.session_state.get(run_count_key, 0)
                     new_session_run_count = current_session_run_count + 1
                     st.session_state[run_count_key] = new_session_run_count
                     logger.info(f"SessionID: {session_id} - Session run count incremented to: {new_session_run_count} (Framework Dev)")

                     if new_session_run_count == 2 or new_session_run_count == 11:
                          st.session_state[show_donation_dialog_key] = True
                          logger.info(f"SessionID: {session_id} - Flag set to show donation dialog for achieving run count {new_session_run_count} (Framework Dev)")

                     st.rerun()


    # --- Feedback and Conclusion Area (Framework Development) ---
    if st.session_state.get(done_key):
        logger.debug(f"SessionID: {session_id} - Entering framework feedback and conclusion area.")

        # Generate final feedback (tailored for frameworks)
        final_feedback_content = generate_final_feedback(case_prompt_text)

        feedback_was_generated = final_feedback_content and not str(final_feedback_content).startswith("Error") and not str(final_feedback_content).startswith("[Feedback")

        if feedback_was_generated:
            st.divider()
            st.header("Overall Framework Feedback") # Different header
            with st.container():
                 st.markdown(final_feedback_content)
            st.divider()

            # --- User Feedback Section (Identical logic, different keys for buttons/inputs) ---
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)

            if feedback_already_submitted:
                # [ Identical display logic as clarifying questions ]
                stored_user_feedback = st.session_state.get(user_feedback_key)
                st.success("Thank you for your feedback!")
                if stored_user_feedback:
                     rating_display = '★' * stored_user_feedback.get('rating', 0)
                     st.caption(f"Your rating: {rating_display}")
                     if stored_user_feedback.get('comment'):
                         st.caption(f"Your comment: {stored_user_feedback.get('comment')}")
            else:
                # Display rating input
                st.markdown("**How helpful was the overall framework feedback? (Click a star rating)**")
                st.write(" ") # Spacer
                cols = st.columns(5)
                selected_rating = 0
                rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        button_label = '★' * (i + 1)
                        # Use different keys to avoid conflicts if both skills somehow render state together
                        if st.button(button_label, key=f"{prefix}_fw_star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"):
                            selected_rating = i + 1
                            rating_clicked = True
                            logger.info(f"SessionID: {session_id} - User clicked framework feedback rating: {selected_rating} stars.")

                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4: # Auto-submit
                        user_feedback_data = {
                            "rating": selected_rating, "comment": "",
                            "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"),
                            "timestamp": time.time()
                        }
                        st.session_state[user_feedback_key] = user_feedback_data
                        st.session_state[feedback_submitted_key] = True
                        st.session_state[show_comment_key] = False
                        save_user_feedback(user_feedback_data) # <<< SAVE/LOG FEEDBACK
                        logger.info(f"SessionID: {session_id} - User Framework Feedback Auto-Submitted (Rating >= 4): {user_feedback_data}")
                        st.rerun()
                    else: # Show comment box
                        st.session_state[show_comment_key] = True
                        # Rerun will happen naturally if comment box needs to show

                if st.session_state.get(show_comment_key, False):
                    st.warning("Please provide a comment for ratings below 4 stars.")
                    current_rating_value = st.session_state.get(feedback_rating_value_key, 0)
                    rating_display = ('★' * current_rating_value) if isinstance(current_rating_value, int) and current_rating_value > 0 else "(select rating)"
                    feedback_comment = st.text_area(
                        f"Comment for your {rating_display} rating:",
                        key=f"{prefix}_fw_feedback_comment_input", # Different key
                        placeholder="e.g., Assessment wasn't specific enough..."
                    )
                    if st.button("Submit Rating and Comment", key=f"{prefix}_fw_submit_feedback_button"): # Different key
                        if not feedback_comment.strip():
                            st.error("Comment cannot be empty for ratings below 4 stars.")
                            logger.warning(f"SessionID: {session_id} - User tried to submit low rating framework feedback with empty comment.")
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0:
                             st.error("Invalid rating selected. Please click a star rating again.")
                             logger.warning(f"SessionID: {session_id} - User tried to submit framework feedback with invalid rating value: {current_rating_value}")
                        else:
                            user_feedback_data = {
                                "rating": current_rating_value, "comment": feedback_comment.strip(),
                                "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"),
                                "timestamp": time.time()
                             }
                            st.session_state[user_feedback_key] = user_feedback_data
                            st.session_state[feedback_submitted_key] = True
                            st.session_state[show_comment_key] = False
                            save_user_feedback(user_feedback_data) # <<< SAVE/LOG FEEDBACK
                            logger.info(f"SessionID: {session_id} - User Framework Feedback Submitted with Comment: {user_feedback_data}")
                            st.rerun()

        # Handle feedback generation errors (identical logic)
        elif final_feedback_content and str(final_feedback_content).startswith("Error"):
             st.error(f"Could not display feedback: {final_feedback_content}")
             logger.error(f"SessionID: {session_id} - Displaying framework feedback generation error: {final_feedback_content}")
        else:
             # [ Identical warning logic as clarifying questions ]
            if st.session_state.get(feedback_submitted_key):
                 st.warning("Feedback was submitted, but could not be displayed (an error likely occurred during generation).")
                 logger.warning(f"SessionID: {session_id} - Framework feedback unavailable, but feedback_submitted is True. Final content was: {final_feedback_content}")
            elif feedback_key in st.session_state and st.session_state[feedback_key] is None and st.session_state.get(conv_key):
                 st.warning("Feedback generation was skipped (e.g., already attempted or error occurred).")
                 logger.warning(f"SessionID: {session_id} - Framework feedback unavailable. Key exists but is None. Final content was: {final_feedback_content}")
            else:
                 st.warning("Feedback is currently unavailable (e.g., no framework submitted yet or generation failed).")
                 logger.warning(f"SessionID: {session_id} - Framework feedback unavailable. Final content was: {final_feedback_content}")


        # Conclusion Section (identical logic)
        st.divider()
        st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** in the framework development phase for this case.")
        logger.info(f"SessionID: {session_id} - Displayed framework conclusion. Total time: {total_interaction_time:.2f}s")

        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            if st.button("Practice This Skill Again", use_container_width=True, key=f"{prefix}_fw_practice_again"): # Different key
                logger.info(f"SessionID: {session_id} - User clicked 'Practice This Skill Again' for Framework Development.")
                reset_skill_state()
                st.rerun()


# --- Entry Point ---
if __name__ == "__main__":
    # Initialize state prefix first if not present
    if 'key_prefix' not in st.session_state:
         st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
         # Initialize session ID here too, right after prefix is set
         init_session_state_key('session_id', str(uuid.uuid4()))
         logger.info(f"Initialized new session with prefix: {st.session_state.key_prefix} and SessionID: {st.session_state.get(f'{st.session_state.key_prefix}_session_id')}")
    elif f"{st.session_state.key_prefix}_session_id" not in st.session_state:
         # Ensure session_id exists even if prefix was already set (e.g., script rerun)
         init_session_state_key('session_id', str(uuid.uuid4()))
         logger.info(f"Re-initialized SessionID for existing prefix {st.session_state.key_prefix}: {st.session_state.get(f'{st.session_state.key_prefix}_session_id')}")

    main_app()
    logger.info("--- Application Script Execution Finished ---")
