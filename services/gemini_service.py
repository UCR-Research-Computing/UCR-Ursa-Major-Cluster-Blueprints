import os
import google.generativeai as genai
from dotenv import load_dotenv # Should be loaded by app.py, but good for standalone service testing

# Ensure environment variables are loaded (especially if running this service standalone)
# In the Flask app context, app.py already calls load_dotenv()
# If this service might be used independently, calling it here is a fallback.
if os.getenv("FLASK_APP_CONTEXT") != "true": # Avoid double loading if in Flask app
    load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    # This will cause an error if the service is loaded and API_KEY is not set.
    # The configure step will fail. Consider raising a custom error or logging.
    print("Warning: API_KEY for Gemini not found in environment variables.")
    # Depending on strictness, could raise an ImproperlyConfigured error here.

try:
    genai.configure(api_key=API_KEY)
    # Initialize a generative model
    # Using gemini-1.5-flash as it's generally available and fast for summarization
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    # Handle cases where API_KEY might be None or invalid at configuration time
    print(f"Error configuring Gemini API: {e}")
    # Set model to None or a mock/dummy model to prevent further errors if config fails
    model = None

class GeminiServiceError(Exception):
    """Custom exception for Gemini service errors."""
    pass

def summarize_text(text_to_summarize: str) -> str:
    """
    Summarizes the given text using the Gemini API.
    Raises GeminiServiceError if the API call fails or the model is not configured.
    """
    if not model:
        raise GeminiServiceError("Gemini model is not configured or API key is missing.")
    if not text_to_summarize or not isinstance(text_to_summarize, str) or not text_to_summarize.strip():
        raise ValueError("Input text cannot be empty or invalid.")

    prompt = f"Please provide a concise summary of the following text:\n\n---\n{text_to_summarize}\n---\n\nSummary:"

    try:
        response = model.generate_content(prompt)

        # Check for empty response or parts
        if not response.parts:
            # Check for safety ratings if parts are empty
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 raise GeminiServiceError(f"Text summarization blocked due to: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise GeminiServiceError("Failed to summarize text: No content generated and no specific block reason.")

        # Assuming the first part contains the text if multiple parts exist
        summary = response.text # .text accessor usually combines text parts
        if not summary.strip():
             raise GeminiServiceError("Failed to summarize text: Empty summary generated.")
        return summary

    except Exception as e:
        # Catching broader exceptions from the generate_content call or response processing
        # Log the actual error e for debugging
        # For example: current_app.logger.error(f"Gemini API error: {str(e)}")
        print(f"Gemini API error: {str(e)}") # Placeholder for proper logging
        raise GeminiServiceError(f"Failed to summarize text via AI service: {str(e)}")

if __name__ == '__main__':
    # Example usage (requires API_KEY to be set in .env or environment)
    if API_KEY and model:
        print("Gemini Service Initialized with key:", API_KEY[:5] + "...")

        example_text_short = "This is a test sentence. It is short."
        example_text_long = (
            "The James Webb Space Telescope (JWST) is a space telescope designed primarily to conduct "
            "infrared astronomy. As the largest optical telescope in space, its high infrared resolution "
            "and sensitivity allow it to view objects too old, distant, or faint for the Hubble Space "
            "Telescope. This is expected to enable a broad range of investigations across the fields of "
            "astronomy and cosmology, such as observation of the first stars and the formation of the "
            "first galaxies, and detailed atmospheric characterization of potentially habitable exoplanets."
            "JWST was launched in December 2021 on an Ariane 5 rocket from Kourou, French Guiana, and "
            "entered orbit around the Sun–Earth L2 Lagrange point in January 2022. "
            "The first image from JWST was released to the public via a press conference on 11 July 2022."
        )
        print(f"\nAttempting to summarize short text: '{example_text_short}'")
        try:
            summary_short = summarize_text(example_text_short)
            print(f"Short Summary: {summary_short}")
        except Exception as e:
            print(f"Error summarizing short text: {e}")

        print(f"\nAttempting to summarize long text (JWST intro)...")
        try:
            summary_long = summarize_text(example_text_long)
            print(f"Long Summary: {summary_long}")
        except Exception as e:
            print(f"Error summarizing long text: {e}")

        # Test empty text
        print("\nAttempting to summarize empty text...")
        try:
            summarize_text(" ")
        except Exception as e:
            print(f"Error (expected for empty text): {e}")

        # Test analyze_notes_text
        example_notes = """
        Meeting 1 (2024-01-15): Discussed initial project scope for quantum entanglement research. Dr. Eva Rostova seems very enthusiastic and knowledgeable. She proposed several innovative approaches. Team morale is high.
        Meeting 2 (2024-02-01): Follow-up on experimental design. Some concerns raised by Dr. Kenji Tanaka about equipment availability, which seemed to frustrate Dr. Rostova slightly. However, solutions were brainstormed. Overall progress is good.
        Observation (2024-02-20): Lab work is proceeding, but Dr. Rostova appears stressed managing multiple grant deadlines. Output is still high quality.
        Meeting 3 (2024-03-05): Positive results from the first set of experiments. Dr. Rostova presented compelling findings. Funding agency representative was impressed. Some minor setbacks with data processing pipeline, but team is addressing it.
        """
        print(f"\nAttempting to analyze notes:\n{example_notes}")
        try:
            analysis_result = analyze_notes_text(example_notes)
            print(f"Analysis Result: {analysis_result}")
        except Exception as e:
            print(f"Error analyzing notes: {e}")

    else:
        print("Gemini Service could not be initialized. API_KEY not found or model init failed.")
        print("To run this example, ensure your API_KEY is in a .env file in the project root,")
        print("or set as an environment variable. The .env file should look like:")
        print("API_KEY=your_actual_api_key_here")

# --- New function: analyze_notes_text ---
import json
from google.generativeai.types import GenerationConfig # For specifying JSON output

def analyze_notes_text(notes_text: str) -> dict:
    """
    Analyzes the given text (researcher notes) using the Gemini API.
    Returns a dictionary with sentiment, keyThemes, and summary.
    Raises GeminiServiceError or ValueError for issues.
    """
    if not model:
        raise GeminiServiceError("Gemini model is not configured or API key is missing.")
    if not notes_text or not isinstance(notes_text, str) or not notes_text.strip():
        raise ValueError("Input notes_text cannot be empty or invalid.")

    prompt = f"""Analyze the following text, which consists of notes about a researcher's activities, discussions, and progress. Provide:
1.  Overall sentiment expressed in the notes. This should be one of: "Positive", "Negative", "Neutral", "Mixed", or "Unknown".
2.  A list of 3-5 key themes or topics discussed in the notes. These should be concise phrases.
3.  A brief summary of the notes (2-3 sentences).

Format the output strictly as a JSON object with the following keys: "sentiment", "keyThemes", "summary".
Ensure the "keyThemes" value is an array of strings.

Text to analyze:
---
{notes_text}
---

JSON Output:"""

    try:
        # Specify JSON output if the model/API version supports it directly in GenerationConfig
        # For gemini-1.5-flash, this is done by instructing in the prompt and parsing.
        # Some newer models might have a specific response_mime_type setting in GenerationConfig.
        # generation_config = GenerationConfig(response_mime_type="application/json")
        # response = model.generate_content(prompt, generation_config=generation_config)

        response = model.generate_content(prompt)

        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                raise GeminiServiceError(f"Notes analysis blocked due to: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise GeminiServiceError("Failed to analyze notes: No content generated and no specific block reason.")

        generated_text = response.text.strip()

        # The model is asked for JSON, but it might be wrapped in markdown (```json ... ```)
        if generated_text.startswith("```json"):
            generated_text = generated_text[7:] # Remove ```json\n
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3] # Remove ```

        generated_text = generated_text.strip() # Clean up any extra whitespace

        try:
            analysis_result = json.loads(generated_text)
        except json.JSONDecodeError as jde:
            # Log the problematic text for debugging: print(f"Problematic JSON string: {generated_text}")
            raise GeminiServiceError(f"Failed to parse AI response as JSON: {jde}. Response was: {generated_text[:200]}...") # Show partial response

        # Validate structure of the parsed JSON
        if not all(key in analysis_result for key in ["sentiment", "keyThemes", "summary"]):
            raise GeminiServiceError("AI response is missing one or more required keys (sentiment, keyThemes, summary).")
        if not isinstance(analysis_result["keyThemes"], list):
            raise GeminiServiceError("AI response 'keyThemes' is not a list.")

        # Further validation for sentiment value if desired
        allowed_sentiments = ["Positive", "Negative", "Neutral", "Mixed", "Unknown"]
        if analysis_result["sentiment"] not in allowed_sentiments:
             # You could either raise an error or default to "Unknown"
             print(f"Warning: Sentiment '{analysis_result['sentiment']}' not in allowed list. Defaulting or flagging.")
             # analysis_result["sentiment"] = "Unknown" # Example of defaulting

        return analysis_result

    except Exception as e:
        # Log the actual error e for debugging
        print(f"Gemini API or processing error during notes analysis: {str(e)}") # Placeholder
        if isinstance(e, GeminiServiceError): # Re-raise if already our custom type
            raise
        raise GeminiServiceError(f"Failed to analyze notes via AI service: {str(e)}")


# --- New function: perform_global_search ---
def perform_global_search(query: str, context_data: dict) -> list[dict]:
    """
    Performs a global search across provided context data using the Gemini API.
    Args:
        query (str): The search query.
        context_data (dict): A dictionary containing lists of researchers, labs, projects, etc.
                             Each item in these lists should be a dictionary itself (serialized).
    Returns:
        list[dict]: A list of search result items, each a dictionary.
    Raises GeminiServiceError or ValueError for issues.
    """
    if not model:
        raise GeminiServiceError("Gemini model is not configured or API key is missing.")
    if not query or not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty or invalid.")
    if not context_data or not isinstance(context_data, dict):
        # Basic check; more detailed validation of context_data structure might be needed.
        raise ValueError("Context data must be a valid dictionary.")

    # Prepare context data strings for the prompt (truncate if too long for token limits)
    # This is a simplified representation; real-world usage might need more sophisticated truncation
    # or summarization if context_data is very large.
    researchers_str = json.dumps(context_data.get("researchers", [])[:5], indent=2) # Example: first 5
    labs_str = json.dumps(context_data.get("labs", [])[:5], indent=2)
    projects_str = json.dumps(context_data.get("projects", [])[:5], indent=2)
    compute_resources_str = json.dumps(context_data.get("computeResources", [])[:3], indent=2)
    grants_str = json.dumps(context_data.get("grants", [])[:3], indent=2)
    notes_str = json.dumps(context_data.get("notes", [])[:10], indent=2) # Example: first 10 notes

    prompt = f"""Please perform a global search across the provided UCR Research Computing data context.
Your task is to identify items from the context that are relevant to the search query.

Search Query: "{query}"

Data Context (some data might be truncated for brevity):
Researchers:
{researchers_str}

Labs:
{labs_str}

Projects:
{projects_str}

Compute Resources:
{compute_resources_str}

Grants:
{grants_str}

All Notes:
{notes_str}

Based *only* on the provided Data Context, identify items that directly match or are highly relevant to the search query.
For each matched item, provide a JSON object with the following fields:
- "id": The ID of the matched item (must be a string).
- "type": The type of the item (e.g., "Researcher", "Lab", "Project", "ComputeResource", "Grant", "Note").
- "name": A concise display name for the item (e.g., researcher's name, project title, lab name, grant title, compute resource name, or for a note, use its first ~20 characters like "Note ID [id]: [content snippet]...").
- "matchContext": A brief explanation (1-2 sentences) of why this item matches the query, referencing specific parts of the item's data if possible.

Return your findings as a JSON array of these objects.
If no items match the query, return an empty JSON array ([]).
Ensure the output is a valid JSON array.
"""

    try:
        response = model.generate_content(prompt)

        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                raise GeminiServiceError(f"Global search blocked due to: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise GeminiServiceError("Global search failed: No content generated and no specific block reason.")

        generated_text = response.text.strip()

        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
        generated_text = generated_text.strip()

        try:
            search_results = json.loads(generated_text)
        except json.JSONDecodeError as jde:
            print(f"Problematic JSON string from global search: {generated_text}") # Log for debugging
            raise GeminiServiceError(f"Failed to parse AI response for global search as JSON: {jde}. Response snippet: {generated_text[:200]}...")

        if not isinstance(search_results, list):
            # If the API didn't return a list (e.g., returned a single object or error message in JSON)
            print(f"Unexpected AI response format for global search (not a list): {search_results}")
            raise GeminiServiceError(f"AI response for global search was not a list as expected. Got: {type(search_results)}")

        # Validate structure of each item in the list
        validated_results = []
        for item in search_results:
            if not isinstance(item, dict):
                print(f"Warning: Search result item is not a dictionary: {item}")
                continue # Skip this item
            if not all(key in item for key in ["id", "type", "name", "matchContext"]):
                print(f"Warning: Search result item missing required keys: {item}")
                continue # Skip this item
            validated_results.append(item)

        return validated_results

    except Exception as e:
        print(f"Gemini API or processing error during global search: {str(e)}")
        if isinstance(e, GeminiServiceError):
            raise
        raise GeminiServiceError(f"Failed to perform global search via AI service: {str(e)}")


# --- New function: search_external_grants_via_ai ---
def search_external_grants_via_ai(search_criteria: dict) -> list[dict]:
    """
    Searches for external research grant opportunities using the Gemini API.
    Args:
        search_criteria (dict): A dictionary with search parameters like keywords, focusArea, etc.
    Returns:
        list[dict]: A list of potential grant opportunities.
    Raises GeminiServiceError or ValueError for issues.
    """
    if not model:
        raise GeminiServiceError("Gemini model is not configured or API key is missing.")
    if not search_criteria or not isinstance(search_criteria, dict):
        raise ValueError("Search criteria must be a valid dictionary.")

    # Constructing the prompt based on provided criteria
    keywords = search_criteria.get('keywords', 'N/A')
    focus_area = search_criteria.get('focusArea', 'N/A') # Matches types.ts PotentialGrantSearchCriteria
    funding_amount = search_criteria.get('fundingAmount', 'N/A') # Matches types.ts
    eligibility = search_criteria.get('eligibility', 'University Researchers') # Default or from criteria

    prompt = f"""Please search for external research grant opportunities based on the following criteria.
Focus on grants relevant to university-level research, primarily in the USA, unless other regions are specified in keywords or focus area.

Search Criteria:
Keywords: {keywords}
Focus Area: {focus_area}
Funding Amount (approximate desired): ${funding_amount if funding_amount != 'N/A' else 'Any'}
Eligibility: {eligibility}

For each potential grant opportunity you identify, provide a JSON object with the following fields:
- "id": A unique temporary ID you generate for this grant (e.g., "temp-grant-1", "temp-grant-2").
- "title": The official title of the grant or funding opportunity.
- "agency": The full name of the funding agency or organization.
- "description": A brief (2-4 sentences) description of the grant's objectives, scope, and eligibility if not covered by the general eligibility criterion.
- "awardNumber": The grant or solicitation number (e.g., NSF-24-501, PAR-23-100), if readily available. If not, use "TBD" or "N/A".
- "amount": Estimated funding amount or range (e.g., "$100,000 - $500,000", "Up to $250,000", "Varies").
- "submissionDate": The submission deadline or relevant date (e.g., "2024-12-01", "October 1, 2024", "Rolling Basis", "Letter of Intent Due: 2024-09-15", "TBD").
- "url": A direct URL to the grant opportunity page, if available. If not, provide a URL to the agency's main funding page or search portal.

Return a JSON array containing a list of these grant objects.
Aim for 5-7 relevant grant opportunities. If very few match, return what you find. If many match, prioritize the most relevant.
If no relevant grants are found based on the criteria, return an empty JSON array ([]).
Ensure the output is a valid JSON array.
"""

    try:
        response = model.generate_content(prompt)

        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                raise GeminiServiceError(f"External grant search blocked due to: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise GeminiServiceError("External grant search failed: No content generated and no specific block reason.")

        generated_text = response.text.strip()

        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
        generated_text = generated_text.strip()

        # Handle empty array case explicitly if model might return non-JSON for it
        if generated_text == "[]":
            return []

        try:
            search_results = json.loads(generated_text)
        except json.JSONDecodeError as jde:
            print(f"Problematic JSON string from external grant search: {generated_text}")
            raise GeminiServiceError(f"Failed to parse AI response for external grant search as JSON: {jde}. Response snippet: {generated_text[:200]}...")

        if not isinstance(search_results, list):
            print(f"Unexpected AI response format for external grant search (not a list): {search_results}")
            raise GeminiServiceError(f"AI response for external grant search was not a list. Got: {type(search_results)}")

        # Validate structure of each item
        validated_results = []
        required_keys = ["id", "title", "agency", "description", "amount", "submissionDate"] # awardNumber and url are optional-ish
        for item in search_results:
            if not isinstance(item, dict):
                print(f"Warning: Grant search result item is not a dictionary: {item}")
                continue
            if not all(key in item for key in required_keys):
                # Could be more lenient here, or AI might sometimes miss fields.
                # For now, basic check.
                print(f"Warning: Grant search result item missing some required keys: {item}")
                # continue # Skip if strict, or append if partial data is acceptable
            validated_results.append(item)

        return validated_results

    except Exception as e:
        print(f"Gemini API or processing error during external grant search: {str(e)}")
        if isinstance(e, GeminiServiceError):
            raise
        raise GeminiServiceError(f"Failed to perform external grant search via AI service: {str(e)}")


# --- New function: match_researchers_to_grant_via_ai ---
def match_researchers_to_grant_via_ai(grant_description: str, researchers_context: list[dict]) -> list[dict]:
    """
    Matches internal researchers to a given grant description using the Gemini API.
    Args:
        grant_description (str): The description of the grant.
        researchers_context (list[dict]): A list of serialized researcher data.
                                          Each researcher dict should have 'id', 'name', 'bio', 'department'.
    Returns:
        list[dict]: A list of matched researcher objects.
    Raises GeminiServiceError or ValueError for issues.
    """
    if not model:
        raise GeminiServiceError("Gemini model is not configured or API key is missing.")
    if not grant_description or not isinstance(grant_description, str) or not grant_description.strip():
        raise ValueError("Grant description cannot be empty or invalid.")
    if not researchers_context or not isinstance(researchers_context, list): # Could be empty list
        raise ValueError("Researchers context must be a list (can be empty).")

    # Prepare researchers_context string for the prompt (truncate if too long)
    # Assuming each researcher_dict in researchers_context has 'id', 'name', 'bio', 'department'
    # Adding 'research' field as per prompt requirement (could be derived from bio or dedicated field)
    researchers_context_formatted = []
    for r_data in researchers_context[:10]: # Example: Max 10 researchers in context for brevity
        research_info = r_data.get('bio', '') # Use bio as proxy for 'research' interests/area
        if len(research_info) > 200: research_info = research_info[:197] + "..."
        researchers_context_formatted.append({
            "id": r_data.get("id"),
            "name": r_data.get("name"),
            "department": r_data.get("department"),
            "research": research_info # Placeholder for more specific research interests
        })
    researchers_str = json.dumps(researchers_context_formatted, indent=2)


    prompt = f"""Given the following research grant description and a list of internal researchers (with their ID, name, department, and a summary of their research/bio), your task is to identify the most suitable researchers from the list to apply for this grant.

Grant Description:
---
{grant_description}
---

Internal Researchers:
---
{researchers_str}
---

For each matched researcher, provide a JSON object with the following fields:
- "originalId": The original ID of the researcher from the input list (must be a string).
- "name": The name of the researcher.
- "matchReason": A brief explanation (1-2 sentences) of why this researcher is a good match for the grant, considering their research summary/bio and department against the grant description.
- "research": The research summary/bio provided for the researcher in the input context.

Return a JSON array of these objects, ordered from most to least relevant.
Limit the results to the top 3-5 most relevant researchers. If fewer match, return all matches.
If no researchers are a good match, return an empty JSON array ([]).
Ensure the output is a valid JSON array.
"""

    try:
        response = model.generate_content(prompt)

        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                raise GeminiServiceError(f"Researcher matching blocked due to: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise GeminiServiceError("Researcher matching failed: No content generated and no specific block reason.")

        generated_text = response.text.strip()

        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
        generated_text = generated_text.strip()

        if generated_text == "[]":
            return []

        try:
            match_results = json.loads(generated_text)
        except json.JSONDecodeError as jde:
            print(f"Problematic JSON string from researcher matching: {generated_text}")
            raise GeminiServiceError(f"Failed to parse AI response for researcher matching as JSON: {jde}. Response snippet: {generated_text[:200]}...")

        if not isinstance(match_results, list):
            print(f"Unexpected AI response format for researcher matching (not a list): {match_results}")
            raise GeminiServiceError(f"AI response for researcher matching was not a list. Got: {type(match_results)}")

        validated_results = []
        required_keys = ["originalId", "name", "matchReason", "research"]
        for item in match_results:
            if not isinstance(item, dict):
                print(f"Warning: Matched researcher item is not a dictionary: {item}")
                continue
            if not all(key in item for key in required_keys):
                print(f"Warning: Matched researcher item missing some required keys ({required_keys}): {item}")
                # continue # Be lenient for now, or make stricter based on needs
            validated_results.append(item)

        return validated_results

    except Exception as e:
        print(f"Gemini API or processing error during researcher matching: {str(e)}")
        if isinstance(e, GeminiServiceError):
            raise
        raise GeminiServiceError(f"Failed to match researchers to grant via AI service: {str(e)}")


# --- New function: generate_grant_intro_email_via_ai ---
def generate_grant_intro_email_via_ai(grant_details: dict, pi_details: dict) -> dict:
    """
    Generates a draft introductory email for a PI regarding a grant, using Gemini API.
    Args:
        grant_details (dict): Dictionary with grant information (title, agency, description, etc.).
        pi_details (dict): Dictionary with PI information (name, email, department, research/bio).
    Returns:
        dict: A dictionary containing "subject" and "body" for the email draft.
    Raises GeminiServiceError or ValueError for issues.
    """
    if not model:
        raise GeminiServiceError("Gemini model is not configured or API key is missing.")
    if not grant_details or not isinstance(grant_details, dict) or not grant_details.get("title"):
        raise ValueError("Grant details must be a valid dictionary with at least a 'title'.")
    if not pi_details or not isinstance(pi_details, dict) or not pi_details.get("name"):
        raise ValueError("PI details must be a valid dictionary with at least a 'name'.")

    # Prepare details for the prompt
    grant_title = grant_details.get('title', 'N/A')
    grant_agency = grant_details.get('agency', 'N/A')
    grant_desc = grant_details.get('description', 'N/A')
    grant_submission_date = grant_details.get('submissionDate', 'N/A')
    grant_award_number = grant_details.get('awardNumber', 'N/A')


    pi_name = pi_details.get('name', 'N/A')
    pi_email = pi_details.get('email', 'N/A') # For context, not necessarily for inclusion in body directly
    pi_department = pi_details.get('department', 'N/A')
    # 'research' key is used in previous AI call, 'bio' might be from researcher_to_json
    pi_research_summary = pi_details.get('research', pi_details.get('bio', 'N/A'))
    if len(pi_research_summary) > 300: pi_research_summary = pi_research_summary[:297] + "..."


    prompt = f"""Please draft a professional introductory email for a Principal Investigator (PI) to send to a funding agency program officer or contact about a specific grant opportunity.

Grant Details:
- Title: {grant_title}
- Agency: {grant_agency}
- Description: {grant_desc}
- Submission Deadline: {grant_submission_date}
- Grant/Award Number: {grant_award_number}

Principal Investigator (PI) Details:
- Name: {pi_name}
- Email: {pi_email}
- Department: {pi_department}
- Research Summary/Bio: {pi_research_summary}

The email draft should:
1.  Be addressed generically (e.g., "Dear Program Officer," or "Dear [Funding Agency Contact],").
2.  Briefly introduce the PI ({pi_name}), their department, and university (assume "our university" or similar generic term if not specified).
3.  Clearly state the PI's interest in the specific grant opportunity (mentioning title and number if available).
4.  Succinctly highlight the alignment between the PI's research expertise/experience (from their Research Summary/Bio) and the grant's objectives/description.
5.  Politely request a brief informational meeting or call to discuss the opportunity further or to ask specific questions. Suggest availability or ask for theirs.
6.  Maintain a concise, professional, and engaging tone.
7.  Conclude with appropriate professional closing (e.g., "Sincerely," followed by PI's name and title - just use name for now).

Return the draft as a JSON object with two keys: "subject" and "body".
Example: {{ "subject": "Inquiry regarding Grant [Grant Title]", "body": "Dear Program Officer,\\n\\nI am writing to..." }}
Ensure the "body" is a single string, potentially with newline characters (\\n) for paragraph breaks.
"""

    try:
        response = model.generate_content(prompt)

        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                raise GeminiServiceError(f"Email generation blocked due to: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise GeminiServiceError("Email generation failed: No content generated and no specific block reason.")

        generated_text = response.text.strip()

        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
        generated_text = generated_text.strip()

        try:
            email_draft = json.loads(generated_text)
        except json.JSONDecodeError as jde:
            print(f"Problematic JSON string from email generation: {generated_text}")
            raise GeminiServiceError(f"Failed to parse AI response for email generation as JSON: {jde}. Response snippet: {generated_text[:200]}...")

        if not isinstance(email_draft, dict) or not all(key in email_draft for key in ["subject", "body"]):
            print(f"Unexpected AI response format for email draft: {email_draft}")
            raise GeminiServiceError("AI response for email draft missing 'subject' or 'body'.")

        return email_draft

    except Exception as e:
        print(f"Gemini API or processing error during email generation: {str(e)}")
        if isinstance(e, GeminiServiceError):
            raise
        raise GeminiServiceError(f"Failed to generate email draft via AI service: {str(e)}")
