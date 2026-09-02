# Groq API (prompts + response streaming)

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_ai_insights(aggregated_data: dict, user_question: str):
    """
    Sends the data to Groq's compound model (which can reason and use tools).
    Returns structured JSON advice.
    """
    system_prompt = """
    You are a brutally honest financial advisor for small business owners.
    Look at the provided numbers and answer the user's question.
    Give specific, actionable feedback. Reference exact dollar amounts and category names.
    Keep it to 3 short bullet points or a short paragraph.
    
    IMPORTANT: Output ONLY a valid JSON object with a single key: "advice" (string).
    Do not include any other text, explanations, or markdown.
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