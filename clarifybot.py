import streamlit as st
import time
import uuid
import openai
import os
import re
import json
import random
# Removed: from streamlit_cookies_manager import CookieManager

# --- Page Config (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(
    page_title="CHIP", # Updated Page Title
    page_icon="🤖",
    layout="centered" # Explicitly centered layout
)

# --- Custom CSS Injection for Styling ---
# Added specific styling for st.tabs
st.markdown("""
<style>
    /* --- Overall Dark Theme --- */

    .main .block-container {
         background-color: #0E1117;
         color: #FAFAFA;
         padding-top: 2rem;
         padding-bottom: 2rem;
    }

    /* --- Headers & Titles --- */
    h1 { /* Main Title: CHIP... */
        color: #FAFAFA;
        text-align: center;
        font-weight: bold;
        font-size: 2.5em;
        border-bottom: none;
        margin-bottom: 10px;
    }
    /* Removed skill-focus-badge as tabs provide focus */
     h2 { /* Section Headers: Case Prompt, Ask... */
        color: #E0E0E0;
        border-bottom: 1px solid #333;
        padding-bottom: 8px;
        margin-top: 40px;
        margin-bottom: 20px;
        font-size: 1.5em;
    }
     h3 { /* Subheader for Rating */
        color: #FAFAFA;
        margin-top: 25px;
        margin-bottom: 10px;
        font-size: 1.2em;
     }

    /* --- Containers & Cards --- */
    .stContainer, .stBlock {
        border-radius: 8px;
    }
    hr { /* Divider */
        border-top: 1px solid #333;
        margin-top: 30px;
        margin-bottom: 30px;
    }

    /* --- Custom Card for Case Prompt --- */
    .case-prompt-card {
        background-color: #161A21;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 25px;
        color: #FAFAFA;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .case-prompt-card .title-box { /* Box for icon and title */
        background-color: #2C313A;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 20px;
        display: inline-flex;
        align-items: center;
        border: 1px solid #444;
    }
     .case-prompt-card .title-box span.icon {
         margin-right: 10px;
         font-size: 1.3em;
         color: #808A9F;
     }
      .case-prompt-card .title-box span.title-text {
         font-size: 1.1em;
         font-weight: bold;
         color: #E0E0E0;
      }
     .case-prompt-card p { /* Style text within the card */
         line-height: 1.6;
         color: #C0C0C0;
         margin-bottom: 0;
     }

    /* --- Chat Area --- */
    /* Container for chat history */
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] div[style*="height: 300px"] {
         background-color: #161A21;
         border: 1px solid #333;
         border-radius: 12px;
         padding: 15px;
         margin-bottom: 15px;
    }
     /* --- Style Chat Message Bubbles (Reverted to Default Streamlit) --- */
     /* Let st.chat_message handle defaults */


    /* --- Buttons --- */
    div[data-testid="stButton"] > button {
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
        background-color: #4A90E2; /* Target blue */
        color: white;
        font-weight: bold;
        transition: background-color 0.2s ease-in-out, transform 0.1s ease-in-out;
        margin-top: 15px; /* Default top margin */
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #357ABD;
        transform: scale(1.02);
    }
     div[data-testid="stButton"] > button:active {
        background-color: #285A8C;
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


    /* --- Text Area & Chat Input --- */
    div[data-testid="stTextArea"] textarea { /* Style for feedback comment box */
        background-color: #161A21;
        border: 1px solid #333;
        border-radius: 8px;
        color: #FAFAFA;
    }
     /* Default stChatInput styling */
     div[data-testid="stChatInput"] {
         border-top: 1px solid #333;
         padding-top: 15px;
         background-color: #0E1117; /* Ensure input bar matches background */
     }
      div[data-testid="stChatInput"] textarea {
          background-color: #1E2229;
          border: 1px solid #444;
          border-radius: 8px;
          color: #FAFAFA;
      }

    /* --- Other Elements --- */
    div[data-testid="stInfo"], div[data-testid="stSuccess"], div[data-testid="stWarning"], div[data-testid="stError"] {
         border-radius: 8px;
         border: 1px solid #555;
         padding: 15px;
         margin-top: 10px;
         margin-bottom: 10px;
    }
     div[data-testid="stSuccess"] { background-color: #1E4620; border-left: 5px solid #28A745; color: #D4EDDA; }
     div[data-testid="stWarning"] { background-color: #4D411B; border-left: 5px solid #FFC107; color: #FFF3CD; }
     div[data-testid="stError"] { background-color: #58151C; border-left: 5px solid #DC3545; color: #F8D7DA; }

    /* --- Tab Styling --- */
    /* Target the tab buttons */
    button[data-baseweb="tab"] {
        background-color: #2C313A; /* Dark background for inactive tabs */
        border-radius: 8px !important; /* Rounded corners */
        margin: 0 5px 10px 5px !important; /* Add some horizontal and bottom margin */
        padding: 10px 15px !important; /* Adjust padding */
        border: 1px solid #444 !important; /* Subtle border */
        color: #A0A7B8 !important; /* Light grey text */
        transition: background-color 0.2s ease-in-out;
    }
    /* Style the selected tab */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #4A90E2 !important; /* Blue background for selected tab */
        color: white !important; /* White text for selected tab */
        font-weight: bold;
    }
    /* Optional: Hover effect for inactive tabs */
    button[data-baseweb="tab"]:not([aria-selected="true"]):hover {
         background-color: #3a414d !important;
         color: #FAFAFA !important;
    }
    /* Remove the default bottom border line from the tab bar */
     div[data-baseweb="tab-list"] {
         border-bottom: none !important;
     }

</style>
""", unsafe_allow_html=True)


# --- Configuration ---
# [ Remains the same ]
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=openai.api_key)
    print("DEBUG: Using API Key from Streamlit secrets.") # Debug
except KeyError:
    print("DEBUG: API Key not found in Streamlit secrets, checking environment variable.") # Debug
    api_key_env = os.environ.get("OPENAI_API_KEY")
    if api_key_env:
        openai.api_key = api_key_env
        client = openai.OpenAI(api_key=openai.api_key)
        print("DEBUG: Using API Key from environment variable.") # Debug
    else:
        st.error("OpenAI API key not found. Please set it in Streamlit secrets (secrets.toml) or as an environment variable OPENAI_API_KEY.")
        st.stop()
except Exception as e:
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()

# --- Removed Cookie Manager Initialization ---

# --- Load Prompts ---
PROMPTS_FILE = "prompts.json"
ALL_PROMPTS = []
# [ Remains the same ]
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_path = os.path.join(script_dir, PROMPTS_FILE)
    if not os.path.exists(prompts_path):
         print(f"DEBUG: Warning: Prompts file not found at {prompts_path}, trying current directory.") # Debug
         prompts_path = PROMPTS_FILE

    print(f"DEBUG: Attempting to load prompts from: {os.path.abspath(prompts_path)}") # Debug absolute path
    with open(prompts_path, 'r', encoding='utf-8') as f:
        ALL_PROMPTS = json.load(f)
    if not isinstance(ALL_PROMPTS, list) or not all(isinstance(p, dict) and 'id' in p and 'prompt_text' in p for p in ALL_PROMPTS):
         raise ValueError("Prompts JSON must be a list of dictionaries, each with 'id' and 'prompt_text' keys.")
    ALL_PROMPT_IDS = [p['id'] for p in ALL_PROMPTS]
    if not ALL_PROMPT_IDS:
        st.error("Error: No prompts found in prompts.json!")
        ALL_PROMPTS = [{"id": "default_error", "title": "Default Prompt (Error Loading File)", "prompt_text": "Error: Could not load prompts correctly from prompts.json."}]
        ALL_PROMPT_IDS = ["default_error"]
except FileNotFoundError:
    st.error(f"Error: {PROMPTS_FILE} not found! Ensure it's in the same directory as the script or provide the correct path.")
    ALL_PROMPTS = [{"id": "default_notfound", "title": "Default Prompt (File Not Found)", "prompt_text": f"Error: {PROMPTS_FILE} file was not found."}]
    ALL_PROMPT_IDS = ["default_notfound"]
except (json.JSONDecodeError, ValueError) as e:
     st.error(f"Error parsing {PROMPTS_FILE}: {e}. Please ensure it's valid JSON.")
     ALL_PROMPTS = [{"id": "default_parse_error", "title": "Default Prompt (Parse Error)", "prompt_text": f"Error: Could not parse {PROMPTS_FILE}."}]
     ALL_PROMPT_IDS = ["default_parse_error"]
except Exception as e:
    st.error(f"An unexpected error occurred loading prompts: {e}")
    ALL_PROMPTS = [{"id": "default_unknown_error", "title": "Default Prompt (Unknown Error)", "prompt_text": "Error: Unknown error loading prompts."}]
    ALL_PROMPT_IDS = ["default_unknown_error"]


# --- Session State Initialization ---
if 'key_prefix' not in st.session_state:
    st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"

def init_session_state_key(key, default_value):
    """Initializes session state key with prefix if not present."""
    full_key = f"{st.session_state.key_prefix}_{key}"
    if full_key not in st.session_state:
        st.session_state[full_key] = default_value

# Define available skills
SKILLS = ["Clarifying Questions", "Framework Development", "Hypothesis Formulation", "Analysis", "Recommendation"]

# Initialize session state keys
# init_session_state_key('selected_skill', SKILLS[0]) # REMOVED - Tabs handle selection
init_session_state_key('current_prompt_id', None)
init_session_state_key('used_prompt_ids', [])
init_session_state_key('conversation', []) # Initialize as empty
init_session_state_key('done_asking', False)
init_session_state_key('feedback_submitted', False)
init_session_state_key('user_feedback', None)
init_session_state_key('run_count', 0)
# init_session_state_key('run_counted_this_instance', False) # REMOVED
init_session_state_key('interaction_start_time', None)
init_session_state_key('total_time', 0.0)
init_session_state_key('is_typing', False)
init_session_state_key('feedback', None)
init_session_state_key('show_comment_box', False)
init_session_state_key('feedback_rating_value', None)
init_session_state_key('show_donation_dialog', False)

# --- Helper Functions ---

def reset_skill_state():
    """Resets state variables specific to a practice run within a skill."""
    prefix = st.session_state.key_prefix
    # Define keys specific to practice runs that need resetting
    keys_to_reset = [
        'current_prompt_id', 'conversation', 'done_asking',
        'feedback_submitted', 'user_feedback', 'interaction_start_time',
        'total_time', 'is_typing', 'feedback',
        'show_comment_box', 'feedback_rating_value',
    ]
    print("DEBUG: Resetting state for skill practice:", keys_to_reset)
    for key in keys_to_reset:
        full_key = f"{prefix}_{key}"
        if full_key in st.session_state:
            try:
                del st.session_state[full_key]
            except KeyError:
                pass
    # Re-initialize needed keys after deletion
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

# [select_new_prompt, get_prompt_details, parse_interviewer_response, send_question, generate_final_feedback functions remain the same as previous version]
# ...
# --- Re-include Helper Functions for completeness ---
def select_new_prompt():
    """Selects a new random prompt, avoiding session repeats if possible."""
    prefix = st.session_state.key_prefix
    used_ids_key = f"{prefix}_used_prompt_ids"
    current_prompt_id_key = f"{prefix}_current_prompt_id"

    if used_ids_key not in st.session_state:
        st.session_state[used_ids_key] = []

    available_prompt_ids = [pid for pid in ALL_PROMPT_IDS if pid not in st.session_state[used_ids_key]]

    if not available_prompt_ids:
        st.info("You've seen all available prompts in this session! Allowing repeats now.")
        st.session_state[used_ids_key] = []
        available_prompt_ids = ALL_PROMPT_IDS
        if not available_prompt_ids:
            st.error("Cannot select prompt - prompt list is empty.")
            return None

    selected_id = random.choice(available_prompt_ids)
    st.session_state[used_ids_key].append(selected_id)
    st.session_state[current_prompt_id_key] = selected_id
    print(f"DEBUG: Selected Prompt ID: {selected_id}") # Debug
    return selected_id

def get_prompt_details(prompt_id):
    """Retrieves prompt details from the loaded list using its ID."""
    if not prompt_id: return None
    for prompt in ALL_PROMPTS:
        if prompt.get('id') == prompt_id:
            return prompt
    print(f"DEBUG: Warning: Prompt ID '{prompt_id}' not found in loaded prompts.") # Debug
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
    elif answer_match and not assessment_match:
         assessment = "[Assessment delimiter missing]"
    elif not answer_match and assessment_match:
         answer = "[Answer delimiter missing]"
    elif not response_text.strip():
        answer = "[LLM returned empty response]"
        assessment = "[LLM returned empty response]"

    return answer, assessment

def send_question(question, current_case_prompt_text):
    """Sends user question to LLM, gets plausible answer & assessment, updates conversation state."""
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    is_typing_key = f"{prefix}_is_typing"

    if not question or not question.strip():
        st.warning("Please enter a question.")
        return
    if not current_case_prompt_text:
        st.error("Internal Error: Cannot send question without case prompt context.")
        return

    st.session_state[is_typing_key] = True
    # --- REMOVED Placeholder Clearing Logic ---
    # if 'placeholder_conversation' in globals() and ... :
    #    st.session_state[conv_key] = []
    #    print("DEBUG: Cleared placeholder conversation.")

    st.session_state.setdefault(conv_key, []).append({"role": "interviewee", "content": question})


    try:
        history_for_prompt = "\n".join(
            [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.get(conv_key, [])[:-1]]
        )

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
        # print(f"DEBUG: LLM Prompt:\n{prompt_for_llm}") # Uncomment for verbose debugging

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict case interview simulator for clarifying questions. Evaluate questions rigorously based on specific categories (Objective, Company, Terms, Repetition, Quality). Provide plausible answers if needed. Use the specified response format."},
                {"role": "user", "content": prompt_for_llm},
            ],
            max_tokens=250,
            temperature=0.5,
            stream=True
        )

        full_response = ""
        with st.spinner("CHIP is generating response..."):
             for chunk in response:
                 if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                     full_response += chunk.choices[0].delta.content

        # print(f"DEBUG: Full LLM Response:\n{full_response}") # Uncomment for verbose debugging

        interviewer_answer, interviewer_assessment = parse_interviewer_response(full_response)

        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer",
            "content": interviewer_answer,
            "assessment": interviewer_assessment
        })

    except Exception as e:
        st.error(f"Error generating response: {e}")
        print(f"DEBUG: Error details during LLM call: {e}") # Added Error Detail Print
        st.session_state.setdefault(conv_key, []).append({
            "role": "interviewer",
            "content": f"Sorry, an error occurred while generating the response. Please try again or restart. ({type(e).__name__})",
            "assessment": "N/A due to error."
        })
    finally:
        st.session_state[is_typing_key] = False
        # --- RESTORED FINAL RERUN --- To update UI after response is processed
        st.rerun()


def generate_final_feedback(current_case_prompt_text):
    """Generates overall feedback markdown based on the conversation history."""
    prefix = st.session_state.key_prefix
    conv_key = f"{prefix}_conversation"
    feedback_key = f"{prefix}_feedback"
    feedback_submitted_key = f"{prefix}_feedback_submitted"

    # Debugging checks at the start
    print(f"DEBUG: generate_final_feedback called.")
    existing_feedback = st.session_state.get(feedback_key)
    feedback_submitted = st.session_state.get(feedback_submitted_key, False)
    print(f"DEBUG: Conversation length: {len(st.session_state.get(conv_key, []))}")
    print(f"DEBUG: Feedback key '{feedback_key}' exists: {feedback_key in st.session_state}, Value is None: {existing_feedback is None}")
    print(f"DEBUG: Feedback submitted key '{feedback_submitted_key}' value: {feedback_submitted}")


    # --- FIXED Skipping Logic ---
    if feedback_submitted:
         print("DEBUG: Skipping feedback gen: Feedback already submitted.")
         return existing_feedback
    if existing_feedback is not None: # Only skip if feedback/error already exists
        print("DEBUG: Skipping feedback gen: Feedback key exists and is not None (already generated or error occurred).")
        return existing_feedback
    if not st.session_state.get(conv_key):
        print("DEBUG: Skipping feedback gen: No conversation history.")
        return None
    # --- REMOVED Placeholder Check ---


    with st.spinner("Generating Final Feedback..."):
        try:
            formatted_history = []
            conversation_history = st.session_state.get(conv_key, [])
            if not isinstance(conversation_history, list):
                st.error("Internal Error: Conversation history format issue.")
                print("DEBUG: Error: Conversation history is not a list.")
                st.session_state[feedback_key] = "Error: Could not generate feedback due to history format."
                return st.session_state[feedback_key]

            for i, msg in enumerate(conversation_history):
                role = msg.get("role")
                content = msg.get("content", "[missing content]")
                if role == 'interviewee':
                    formatted_history.append(f"Interviewee Question {i//2 + 1}: {content}")
                elif role == 'interviewer':
                    formatted_history.append(f"Interviewer Response: {content}")
                    assessment = msg.get('assessment')
                    if assessment:
                        formatted_history.append(f" -> Interviewer's Assessment of Question {i//2 + 1}: {assessment}")

            history_string = "\n\n".join(formatted_history)

            feedback_prompt = f"""
            You are an experienced case interview coach providing feedback on the clarifying questions phase ONLY.

            Case Prompt Context for this Session:
            {current_case_prompt_text}

            Interview Interaction History (including interviewer's assessment of each question):
            {history_string}

            Your Task:
            Provide detailed, professional, and direct feedback on the interviewee's clarifying questions phase based *only* on the interaction history provided.

            Structure your feedback precisely as follows using Markdown:
            1.  **Overall Summary:** Briefly summarize the interviewee's performance in asking clarifying questions for *this specific case context*.
            2.  **Strengths:** Identify 1-2 specific strengths demonstrated (e.g., good initial questions, logical flow, conciseness). Refer to specific question numbers or assessments if possible.
            3.  **Areas for Improvement:** Identify 1-2 key areas where the interviewee could improve (e.g., question relevance, depth, avoiding compound questions, structure, digging deeper based on answers). Refer to specific question numbers or assessments.
            4.  **Actionable Next Steps:** Provide at least two concrete, actionable steps the interviewee can take to improve their clarifying questions skills *for future cases*.
            5.  **Example Questions:** For *each* actionable next step that relates to the *content* or *quality* of the questions asked, provide 1-2 specific *alternative* example questions the interviewee *could have asked* in *this case* to demonstrate improvement in that area.
            6.  **Overall Rating (1-5):** Rate the interviewee's clarifying question skills based *only* on this interaction. Justify your rating briefly, referencing the conversation specifics or assessments. **Be very critical and use the full range of scores:**
                * 1: **Must use this score** if questions were predominantly vague (like single words), irrelevant, unclear, compound, or demonstrated a fundamental lack of understanding of how to clarify effectively. Added little to no value.
                * 2: Significant issues remain. Many questions were poor, with only occasional relevant ones, or showed a consistent lack of focus/structure.
                * 3: A mixed bag. Some decent questions fitting the ideal categories (Objective, Company, Terms, Repetition) but also notable lapses in quality, relevance, or efficiency.
                * 4: Generally strong performance. Most questions were relevant, clear, targeted, and fit the ideal categories. Good progress made in clarifying the case, with only minor areas for refinement.
                * 5: Excellent. Consistently high-quality questions that were relevant, concise, targeted, and demonstrated a strong grasp of the ideal clarifying categories. Effectively and efficiently clarified key aspects of the case prompt.
               **Consider the per-question assessments provided in the history when assigning the overall rating.**

            Be constructive and focus *only* on the clarifying questions phase of *this specific case*. Ensure your response does **not** start with a title like "Feedback on Clarifying Questions". Start directly with point 1. Overall Summary using Markdown bolding as shown.
            """
            print("DEBUG: Calling OpenAI API for final feedback...") # Debug
            feedback_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert case interview coach providing structured feedback, starting directly with the 'Overall Summary'. Evaluate critically based on history and assessments. Do not include a title in your response."},
                    {"role": "user", "content": feedback_prompt},
                ],
                max_tokens=800,
                temperature=0.5,
            )
            feedback = feedback_response.choices[0].message.content.strip()
            print(f"DEBUG: Feedback received from API (first 100 chars): {feedback[:100]}") # Debug

            if feedback:
                 st.session_state[feedback_key] = feedback
            else:
                 print("DEBUG: Warning - LLM returned empty feedback.")
                 st.session_state[feedback_key] = "[Feedback generation returned empty]" # Store placeholder
            return st.session_state[feedback_key]

        except Exception as e:
            st.error(f"Could not generate feedback. Error: {e}")
            print(f"DEBUG: Error during feedback generation API call: {e}") # Added Error Detail Print
            st.session_state[feedback_key] = f"Error generating feedback: {type(e).__name__}"
            return st.session_state[feedback_key]


# --- Main Streamlit Application Function ---
def main_app():
    """Main function to control skill selection and display."""
    st.title("CHIP")

    prefix = st.session_state.key_prefix
    # REMOVED skill_key definition here as it's handled by tabs

    # --- Skill Selection using st.tabs ---
    tab_names = SKILLS
    # Use st.tabs for the selection UI
    tabs = st.tabs(tab_names)

    # --- Display Selected Skill UI ---
    # Each skill's content goes within its corresponding 'with' block
    with tabs[0]: # Corresponds to SKILLS[0] = "Clarifying Questions"
        clarifying_questions_bot_ui() # Call the UI function for this skill

    with tabs[1]: # Corresponds to SKILLS[1] = "Framework Development"
        st.header(f"{SKILLS[1]}")
        st.info("This module is under construction. Check back later!")
        # framework_bot_ui() # Call function for this skill later

    with tabs[2]: # Corresponds to SKILLS[2] = "Hypothesis Formulation"
        st.header(f"{SKILLS[2]}")
        st.info("This module is under construction. Check back later!")
        # hypothesis_bot_ui()

    with tabs[3]: # Corresponds to SKILLS[3] = "Analysis"
        st.header(f"{SKILLS[3]}")
        st.info("This module is under construction. Check back later!")
        # analysis_bot_ui()

    with tabs[4]: # Corresponds to SKILLS[4] = "Recommendation"
        st.header(f"{SKILLS[4]}")
        st.info("This module is under construction. Check back later!")
        # recommendation_bot_ui()


# --- Skill-Specific UI Function (Example for Clarifying Questions) ---
def clarifying_questions_bot_ui():
    """Defines the Streamlit UI and logic SPECIFICALLY for the Clarifying Questions skill."""

    # Display Skill Focus Badge (now redundant with tabs, can be removed or kept)
    # st.markdown('<div class="skill-focus-badge">Skill Focus: Clarifying Questions</div>', unsafe_allow_html=True)

    # Define Session State Keys using prefix
    prefix = st.session_state.key_prefix
    done_key = f"{prefix}_done_asking"
    time_key = f"{prefix}_total_time"
    start_time_key = f"{prefix}_interaction_start_time"
    conv_key = f"{prefix}_conversation"
    feedback_key = f"{prefix}_feedback"
    is_typing_key = f"{prefix}_is_typing"
    feedback_submitted_key = f"{prefix}_feedback_submitted"
    user_feedback_key = f"{prefix}_user_feedback"
    current_prompt_id_key = f"{prefix}_current_prompt_id"
    run_count_key = f"{prefix}_run_count" # Session state run count
    show_comment_key = f"{prefix}_show_comment_box"
    feedback_rating_value_key = f"{prefix}_feedback_rating_value"
    show_donation_dialog_key = f"{prefix}_show_donation_dialog" # Key for dialog

    # --- Session State Run Count Display ---
    current_run_count_display = st.session_state.get(run_count_key, 0)
    # st.caption(f"Debug: Total runs completed this session = {current_run_count_display}") # Removed

    # --- Show Donation Dialog ---
    if st.session_state.get(show_donation_dialog_key):
        print("DEBUG: Attempting to show donation dialog.")
        if hasattr(st, 'dialog'):
            @st.dialog("Support CHIP!")
            def show_donation():
                st.write(
                    "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
                    "Consider making a small donation (suggested $5) to help cover server and API costs."
                )
                col1, col2, col3 = st.columns([1,2,1])
                with col2:
                     st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary", use_container_width=True) # Updated Link
                if st.button("Maybe later", use_container_width=True):
                    st.session_state[show_donation_dialog_key] = False
                    st.rerun()
            show_donation()
        else:
            # Fallback
            with st.container(border=True):
                st.success(
                    "Love CHIP? Your support helps keep this tool free and improving! 🙏\n\n"
                    "Consider making a small donation (suggested $5) to help cover server and API costs."
                )
                st.link_button("Donate via Buy Me a Coffee ☕", "https://buymeacoffee.com/9611", type="primary") # Updated Link
            st.session_state[show_donation_dialog_key] = False


    # --- Select and Display Case Prompt ---
    # Select a new prompt only if one isn't already selected for this skill instance
    if st.session_state.get(current_prompt_id_key) is None:
        selected_id = select_new_prompt()
        if selected_id is None:
             st.error("Failed to select a new prompt. Please check prompt file.")
             st.stop()

    current_prompt = get_prompt_details(st.session_state.get(current_prompt_id_key))

    if not current_prompt:
        st.error("Could not load the current case prompt details. Please try restarting.")
        # Changed button to use reset function
        if st.button("Restart This Skill Practice"):
             reset_skill_state() # Use reset function
             st.rerun()
        st.stop()

    # --- Display Case Prompt using Custom Card Layout ---
    st.header("Case Prompt")
    case_title = current_prompt.get('title', 'N/A')
    case_prompt_text = current_prompt.get('prompt_text', 'Error: Prompt text missing.')
    if case_prompt_text.startswith("Error"):
        st.error(case_prompt_text)
        st.stop()
    else:
        st.markdown(f"""
        <div class="case-prompt-card">
            <div class="title-box">
                <span class="icon">💼</span>
                <span class="title-text">{case_title}</span>
            </div>
            <p>{case_prompt_text}</p>
        </div>
        """, unsafe_allow_html=True)


    # --- Main Interaction Area (Clarifying Questions) ---
    if not st.session_state.get(done_key):
        st.header("Ask Clarifying Questions")
        st.caption("Ask questions below. Click 'End Clarification Questions' when finished.")

        # --- Moved Button ---
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
        with col_btn2:
            if st.button("End Clarification Questions", use_container_width=True):
                end_time = time.time()
                start_time = st.session_state.get(start_time_key)
                if start_time is not None:
                    st.session_state[time_key] = end_time - start_time
                else:
                    st.session_state[time_key] = 0.0
                st.session_state[done_key] = True

                # --- Increment Run Count and Trigger Dialog Check HERE ---
                current_session_run_count = st.session_state.get(run_count_key, 0)
                new_session_run_count = current_session_run_count + 1
                st.session_state[run_count_key] = new_session_run_count
                print(f"DEBUG: Session run count incremented to: {new_session_run_count}")

                if new_session_run_count == 2 or new_session_run_count == 11:
                     st.session_state[show_donation_dialog_key] = True
                     print(f"DEBUG: Flag set to show donation dialog for achieving run count {new_session_run_count}")

                st.rerun() # Rerun to show feedback section

        # Record start time only once when interaction begins
        if st.session_state.get(start_time_key) is None:
            st.session_state[start_time_key] = time.time()

        # Chat history display
        chat_container = st.container(height=300)
        with chat_container:
            conversation_history = st.session_state.get(conv_key, [])
            if isinstance(conversation_history, list):
                 for msg in conversation_history:
                     role = msg.get("role")
                     display_role = "user" if role == "interviewee" else "assistant"
                     with st.chat_message(display_role):
                         st.markdown(msg.get("content", ""))

        # Typing indicator placeholder
        typing_placeholder = st.empty()
        if st.session_state.get(is_typing_key):
            typing_placeholder.markdown("_(CHIP is thinking...)_")
        else:
            typing_placeholder.empty()

        # --- Reverted to st.chat_input ---
        user_question = st.chat_input(
            "Type your question here...",
            key="chat_input",
            disabled=st.session_state.get(is_typing_key, False)
        )

        if user_question:
            if st.session_state.get(is_typing_key):
                 typing_placeholder.empty()
            send_question(user_question, case_prompt_text)


    # --- Feedback and Conclusion Area ---
    if st.session_state.get(done_key):

        final_feedback_content = generate_final_feedback(case_prompt_text)
        print(f"DEBUG: Result from generate_final_feedback: '{str(final_feedback_content)[:100]}...'")

        feedback_was_generated = final_feedback_content and not final_feedback_content.startswith("Error") and not final_feedback_content.startswith("[Feedback")

        if feedback_was_generated:
            st.markdown("---")
            with st.container(border=True):
                 st.markdown(final_feedback_content)
            st.markdown("---")

            # --- User Feedback Section ---
            st.subheader("Rate this Feedback")
            feedback_already_submitted = st.session_state.get(feedback_submitted_key, False)
            if feedback_already_submitted:
                # Display submitted feedback
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
                st.write(" ")
                cols = st.columns(5)
                selected_rating = 0
                rating_clicked = False
                for i in range(5):
                    with cols[i]:
                        button_label = '★' * (i + 1)
                        if st.button(button_label, key=f"star_{i+1}", help=f"Rate {i+1} star{'s' if i>0 else ''}"):
                            selected_rating = i + 1
                            rating_clicked = True
                if rating_clicked:
                    st.session_state[feedback_rating_value_key] = selected_rating
                    if selected_rating >= 4:
                        user_feedback_data = {
                            "rating": selected_rating, "comment": "",
                            "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"),
                            "timestamp": time.time()
                        }
                        st.session_state[user_feedback_key] = user_feedback_data
                        st.session_state[feedback_submitted_key] = True
                        st.session_state[show_comment_key] = False
                        print(f"DEBUG: User Feedback Auto-Submitted: {user_feedback_data}")
                        st.rerun()
                    else:
                        st.session_state[show_comment_key] = True
                        st.rerun()
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
                        elif not isinstance(current_rating_value, int) or current_rating_value <= 0:
                             st.error("Invalid rating selected. Please click a star rating again.")
                        else:
                            user_feedback_data = {
                                "rating": current_rating_value, "comment": feedback_comment.strip(),
                                "prompt_id": st.session_state.get(current_prompt_id_key, "N/A"),
                                "timestamp": time.time()
                             }
                            st.session_state[user_feedback_key] = user_feedback_data
                            st.session_state[feedback_submitted_key] = True
                            st.session_state[show_comment_key] = False
                            print(f"DEBUG: User Feedback Submitted with Comment: {user_feedback_data}")
                            st.rerun()

        elif final_feedback_content and final_feedback_content.startswith("Error"):
             st.error(f"Could not display feedback: {final_feedback_content}")
             print(f"DEBUG: Displaying feedback error: {final_feedback_content}")
        else:
            if st.session_state.get(feedback_submitted_key):
                 st.warning("Feedback was submitted, but could not be displayed.")
                 print(f"DEBUG: Displaying 'Feedback unavailable' warning, but feedback_submitted is True. Value was: {final_feedback_content}")
            elif feedback_key in st.session_state and st.session_state[feedback_key] is None:
                 st.warning("Feedback generation skipped (already attempted).")
                 print(f"DEBUG: Displaying 'Feedback unavailable' warning. Feedback key exists but is None.")
            else:
                 st.warning("Feedback is currently unavailable.")
                 print(f"DEBUG: Displaying 'Feedback currently unavailable' warning. Value was: {final_feedback_content}")


        st.divider()
        st.header("Conclusion")
        total_interaction_time = st.session_state.get(time_key, 0.0)
        st.write(f"You spent **{total_interaction_time:.2f} seconds** in the clarifying questions phase for this case.")

        # --- Restart Button (for the specific skill) ---
        col_btn_r1, col_btn_r2, col_btn_r3 = st.columns([1, 1.5, 1])
        with col_btn_r2:
            # Changed label slightly
            if st.button("Practice This Skill Again", use_container_width=True):
                reset_skill_state() # Use reset function
                st.rerun()

# --- Entry Point ---
if __name__ == "__main__":
    # Initialize state prefix first if not present
    if 'key_prefix' not in st.session_state:
         st.session_state.key_prefix = f"chip_bot_{uuid.uuid4().hex[:6]}"
    main_app() # Call the main controller function

