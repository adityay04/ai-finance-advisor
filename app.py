# main streamlit entry point (frontend and ui)

import streamlit as st
import pandas as pd
import json
import plotly.express as px
from src.groq_client import get_ai_insights
from src.rag_engine import ingest_pdf, retrieve_context, get_knowledge_count, clear_vector_db

st.set_page_config(page_title="SME AI Advisor", layout="wide")
st.title("🚀 AI Financial Advisor (Powered by Groq + RAG)")

with st.sidebar:
    st.header("📚 Knowledge Base (RAG)")
    st.caption("Upload tax guides, financial rules, or policy PDFs.")
    uploaded_pdfs = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True, key="pdf_uploader")
    if uploaded_pdfs:
        with st.spinner("Indexing PDFs for AI retrieval..."):
            total_chunks = 0
            for pdf in uploaded_pdfs:
                chunks = ingest_pdf(pdf.read(), pdf.name)
                total_chunks += chunks
            st.success(f"✅ {len(uploaded_pdfs)} PDFs ingested! ({total_chunks} chunks stored)")
    kb_count = get_knowledge_count()
    if kb_count > 0:
        st.info(f"📊 Knowledge Base: {kb_count} text chunks ready.")
        if st.button("🗑️ Clear Knowledge Base"):
            clear_vector_db()
            st.rerun()
    else:
        st.warning("⚠️ No knowledge loaded. AI will use general knowledge only.")

uploaded_file = st.file_uploader("Upload your bank CSV or Excel file", type=["csv", "xlsx"])
user_question = st.text_input("Ask a question", placeholder="e.g., Am I spending too much on Food?")
analyze_clicked = st.button("📊 Analyze", type="primary")

if uploaded_file and user_question and analyze_clicked:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    amount_col = None
    cat_col = None

    for col in df.columns:
        col_lower = col.lower()
        if 'sales' in col_lower or 'amount' in col_lower or 'value' in col_lower or 'total' in col_lower:
            amount_col = col
        if 'item type' in col_lower or 'category' in col_lower or 'type' in col_lower or 'description' in col_lower:
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

    aggregated_data = {
        "total": total_spend,
        "top_category": top_cats.index[0] if len(top_cats) > 0 else "Unknown",
        "top_amount": top_cats.iloc[0] if len(top_cats) > 0 else 0,
        "count": len(df),
        "category_breakdown": cat_summary
    }

    rag_context = ""
    if get_knowledge_count() > 0:
        with st.spinner("🔍 Searching knowledge base for relevant tax rules..."):
            search_query = f"{user_question} {top_cats.index[0]}"
            rag_context = retrieve_context(search_query, top_k=1)
            if rag_context:
                st.sidebar.success("📖 Found relevant knowledge!")
            else:
                st.sidebar.info("📖 No specific match found. Using general knowledge.")

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Expenses", f"${total_spend:,.2f}")
    col2.metric("📄 Transactions", len(df))
    col3.metric("🏆 Top Category", f"{top_cats.index[0]} (${top_cats.iloc[0]:,.2f})")

    chart_col1, chart_col2 = st.columns(2)
    top5 = category_totals.head(5).reset_index()
    top5.columns = ['Category', 'Amount']

    with chart_col1:
        st.subheader("📊 Spending by Category")
        fig_bar = px.bar(
            top5, x='Category', y='Amount', text='Amount',
            color='Category', title="Top 5 Categories",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_bar.update_traces(texttemplate='$%{text:,.2f}', textposition='outside')
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, width='stretch')

    with chart_col2:
        st.subheader("🍩 Expense Distribution")
        fig_pie = px.pie(
            top5, values='Amount', names='Category',
            title="% of Total Spend",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, width='stretch')

    st.divider()
    st.subheader("🤖 AI Financial Advice")
    with st.spinner("Asking Groq Compound (with RAG context)..."):
        raw_json = get_ai_insights(aggregated_data, user_question, rag_context)
        result = json.loads(raw_json)
    st.success("✅ Groq Compound responded!")
    st.markdown(f"**{result['advice']}**")

    if rag_context:
        with st.expander("📖 View Knowledge Base Sources (RAG Context)"):
            st.text(rag_context)

    with st.expander("🔢 Data sent to AI"):
        st.json(aggregated_data)
    with st.expander("📋 Raw Data Preview (first 5 rows)"):
        st.dataframe(df.head())
else:
    st.info("👆 Upload a file, type a question, and click 'Analyze' to get started!")

st.divider()
st.caption("💡 Tip: Upload tax PDFs in the sidebar to enable RAG (AI will reference your specific rules).")