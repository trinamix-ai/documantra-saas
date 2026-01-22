# main.py
import oci
import base64
import os
import sys

import prompts

# 1. Load config
def load_config_properties(filepath):
    """
    Reads a file with format 'KEY = VALUE' and returns a dictionary.
    Ignores lines starting with #.
    """
    config_dict = {}
    if not os.path.exists(filepath):
        print(f"Error: Config file not found at {filepath}")
        sys.exit(1)
        
    with open(filepath, 'r') as f:
        for line in f:
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Split at the first '=' only
            if '=' in line:
                key, value = line.split('=', 1)
                config_dict[key.strip()] = value.strip()
    return config_dict

# Load the file
config_path = 'config/oci.config'
config_data = load_config_properties(config_path)

# 2. Get variables from config file
try:
    COMPARTMENT_ID = config_data['COMPARTMENT_ID']
    GENAI_MODEL_ID = config_data['GENAI_MODEL_ID']
    TARGET_FILE    = config_data['TARGET_FILE']
    
    # Convert numbers from string to int
    TEMPERATURE    = int(config_data['TEMPERATURE'])
    MAX_TOKENS     = int(config_data['MAX_TOKENS'])
    TEXT_LIMIT     = int(config_data['TEXT_LIMIT'])
except KeyError as e:
    print(f"Missing config key: {e}")
    sys.exit(1)
except ValueError as e:
    print(f"Config formatting error (expected number): {e}")
    sys.exit(1)

# --- 3. OCI AUTHENTICATION ---
try:
    oci_config = oci.config.from_file()
except Exception as e:
    print(f"Error loading ~/.oci/config: {e}")
    sys.exit(1)

# --- FUNCTIONS ---

def extract_text_from_pdf(file_path):
    aidoc_client = oci.ai_document.AIServiceDocumentClient(oci_config)

    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
            encoded_string = base64.b64encode(file_content).decode('utf-8')
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    analyze_details = oci.ai_document.models.AnalyzeDocumentDetails(
        features=[oci.ai_document.models.DocumentTextExtractionFeature()],
        document=oci.ai_document.models.InlineDocumentDetails(data=encoded_string),
        compartment_id=COMPARTMENT_ID
    )

    try:
        response = aidoc_client.analyze_document(analyze_document_details=analyze_details)
        full_text = []
        if response.data.pages:
            for page in response.data.pages:
                for line in page.lines:
                    full_text.append(line.text)
        return "\n".join(full_text)
    except oci.exceptions.ServiceError as e:
        print(f"Error calling OCI Doc Understanding: {e}")
        return None

def classify_with_genai(extracted_text):
    if not extracted_text:
        return "Unknown"
    
    truncated_text = extracted_text[:TEXT_LIMIT]

    genai_client = oci.generative_ai_inference.GenerativeAiInferenceClient(oci_config)

    # Get prompt from prompts.py
    final_prompt = prompts.get_classification_prompt(truncated_text)

    chat_details = oci.generative_ai_inference.models.ChatDetails(
        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
            model_id=GENAI_MODEL_ID
        ),
        chat_request=oci.generative_ai_inference.models.CohereChatRequest(
            message=final_prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            is_stream=False
        ),
        compartment_id=COMPARTMENT_ID
    )

    try:
        response = genai_client.chat(chat_details)
        return response.data.chat_response.text.strip()
    except oci.exceptions.ServiceError as e:
        return f"Error: {e}"

# --- MAIN EXECUTION ---

def main():
    if not os.path.exists(TARGET_FILE):
        print(f"File not found: {TARGET_FILE}")
        return

    print(f"Processing: {os.path.basename(TARGET_FILE)}")

    # Check extension
    _, ext = os.path.splitext(TARGET_FILE)
    ext = ext.lower()
    
    final_category = "Unknown"

    if ext in ['.xlsx', '.xls', '.csv']:
        final_category = "Excel docs"
    
    elif ext == '.pdf':
        doc_text = extract_text_from_pdf(TARGET_FILE)
        
        if doc_text:
            ai_decision = classify_with_genai(doc_text)
            
            if "PO" in ai_decision:
                final_category = "PO/pdf"
            elif "Invoice" in ai_decision:
                final_category = "Invoice/pdf"
            else:
                final_category = f"Unsure/pdf ({ai_decision})"
    else:
        final_category = "Unsupported File Type"

    print(f"\n FINAL CLASSIFICATION: {final_category}")

if __name__ == "__main__":
    main()