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

    else:
        print("Gemini Service could not be initialized. API_KEY not found or model init failed.")
        print("To run this example, ensure your API_KEY is in a .env file in the project root,")
        print("or set as an environment variable. The .env file should look like:")
        print("API_KEY=your_actual_api_key_here")
