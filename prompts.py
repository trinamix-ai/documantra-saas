# prompts.py

def get_classification_prompt(text_content):
    return f"""
    Role: You are a Document Classifier.

    Task:
    Classify the document into EXACTLY ONE of the following categories:
    - PO
    - Invoice

    Input Text:
    {text_content}

    Classification Rules (to be followed in order):

    1. Invoice
       - If the document contains keywords such as: "Invoice", "Tax Invoice", "Bill To", or "Amount Due".
       - OR if it requests a payment.

    2. PO (Purchase Order)
       - If the document contains keywords such as: "Purchase Order", "PO Number", "Order #", "Ship To".
       - AND it lists items to be bought/shipped.

    Output Rules:
    - Output ONLY one of the following exact strings:
      PO
      Invoice
    - Do not add punctuation or explanations.
    """