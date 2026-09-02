# main streamlit entry point (frontend and ui)

import streamlit as st
import pandas as pd
import json
from src.groq_client import get_ai_insights

st.set_page_config(page_title="SME AI Advisor", layout="centered")
st.title("AI Financial Advisor for Small Business Owners")

uploaded_file = st.file_uploader("Upload your bank CSV", type=["csv"])
user_question = st.text_input("Ask a question", placeholder="e.g., Am I spending too much on Food?")

if uploaded_file and user_question:
    df = pd.read_csv(uploaded_file)
    
    amount_col = None
    cat_col = None
    
    for col in df.columns:
        if 'amount' in col.lower() or 'value' in col.lower() or 'total' in col.lower():
            amount_col = col
        if 'category' in col.lower() or 'type' in col.lower() or 'description' in col.lower():
            cat_col = col
    
    if amount_col is None:
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                amount_col = col
                break
    if cat_col is None:
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                cat_col = col
                break
    
    if amount_col is None:
        amount_col = df.columns[0]
    if cat_col is None:
        cat_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    
    total_spend = df[amount_col].sum()
    
    category_totals = df.groupby(cat_col)[amount_col].sum().sort_values(ascending=False)
    
    top_cats = category_totals.head(3)
    cat_summary = ", ".join([f"{cat} (${amt:,.2f})" for cat, amt in top_cats.items()])
    
    top_category = top_cats.index[0] if len(top_cats) > 0 else "Unknown"
    top_amount = top_cats.iloc[0] if len(top_cats) > 0 else 0
    
    aggregated_data = {
        "total": total_spend,
        "top_category": top_category,
        "top_amount": top_amount,
        "count": len(df),
        "category_breakdown": cat_summary
    }
    
    st.caption(f"Detected Amount: `{amount_col}` | Category: `{cat_col}`")
    
    with st.spinner("Asking Groq Compound (reasoning + tools)..."):
        raw_json = get_ai_insights(aggregated_data, user_question)
        result = json.loads(raw_json)
    
    st.success("Groq Compound responded!")
    st.write(result["advice"])
    
    with st.expander("What I sent to the AI"):
        st.json(aggregated_data)