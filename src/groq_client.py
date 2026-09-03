# Groq API (prompts + response streaming)

import os
import json
import re
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def get_groq_client():
    """Get Groq client with API key from environment or Streamlit secrets."""
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        try:
            api_key = st.secrets.GROQ_API_KEY
        except Exception:
            pass
    
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Please set it in your .env file or Streamlit secrets."
        )
    
    return Groq(api_key=api_key)

client = get_groq_client()

def get_ai_insights(aggregated_data: dict, user_question: str, rag_context: str = None):
    if rag_context and len(rag_context) > 8000:
        rag_context = rag_context[:8000] + "\n...[truncated due to length]"

    if rag_context and len(rag_context) > 10:
        system_prompt = f"""
        You are a brutally honest financial advisor for small business owners.
        IMPORTANT: You must ground your advice in the following tax/financial rules 
        retrieved from the user's uploaded knowledge base:
        === KNOWLEDGE BASE CONTEXT ===
        {rag_context}
        === END CONTEXT ===
        Look at the provided numbers and answer the user's question.
        Reference the specific rules or sections from the knowledge base.
        Give specific, actionable feedback with exact dollar amounts and category names.
        Keep it to 3 short bullet points or a short paragraph.
        OUTPUT ONLY: A valid JSON object with a single key: "advice" (string).
        No other text, no markdown.
        """
    else:
        system_prompt = """
        You are a brutally honest financial advisor for small business owners.
        Look at the provided numbers and answer the user's question.
        Give specific, actionable feedback. Reference exact dollar amounts and category names.
        Keep it to 3 short bullet points or a short paragraph.
        OUTPUT ONLY: A valid JSON object with a single key: "advice" (string).
        No other text, no markdown.
        """
    
    user_prompt = f"""
    Here is my expense data:
    - Total Expenses: ${aggregated_data['total']:,.2f}
    - Top 3 Spending Categories: {aggregated_data['category_breakdown']}
    - Number of Transactions: {aggregated_data['count']}
    My question: {user_question}
    """
    
    response = client.chat.completions.create(
        model="groq/compound",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
    )
    
    raw_content = response.choices[0].message.content
    json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
    if json_match:
        return json_match.group()
    else:
        return json.dumps({"advice": raw_content})