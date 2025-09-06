import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os
from io import BytesIO

st.set_page_config(page_title="Bank → Financial Statements + Valuation", layout="wide")
st.title("🏦 Bank Statement → Financial Statements + Valuation")
st.markdown("""
Upload a CSV bank statement (Date, Description, Amount).  
You'll get transactions, a simple Income Statement, Balance Sheet, Ratios, charts, PDF & Excel export, and enterprise valuation (DCF, EV/EBITDA, Revenue multiple).
""")

# -------------------------
# File upload and parsing
# -------------------------
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

def categorize(description, amount):
    desc = str(description).lower()
    if "shell" in desc or "fuel" in desc:
        return "Fuel Expense"
    if "salary" in desc or "payroll" in desc:
        return "Payroll Expense"
    if "rent" in desc:
        return "Rent Expense"
    if any(k in desc for k in ["tax", "vat"]):
        return "Tax"
    if amount > 0:
        return "Sales Income"
    return "Other Expense"

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    required_cols = {"Date", "Description", "Amount"}
    if not required_cols.issubset(df.columns):
        st.error("CSV must have columns: Date, Description, Amount")
    else:
        df["Category"] = df.apply(lambda row: categorize(row["Description"], row["Amount"]), axis=1)
        df["Date"] = pd.to_datetime(df["Date"])

        st.subheader("📑 Transactions")
        st.dataframe(df, use_container_width=True)

        # Income Statement
        income = df[df["Category"] == "Sales Income"]["Amount"].sum()
        expenses = df[df["Category"].str.contains("Expense")]["Amount"].sum()
        net_profit = income + expenses  # expenses negative

        st.subheader("📊 Income Statement")
        st.write(f"**Revenue:** {income:,.2f}")
        st.write(f"**Expenses:** {expenses:,.2f}")
        st.write(f"**Net Profit:** {net_profit:,.2f}")

        # Balance Sheet (simplified)
        total_assets = df["Amount"].sum()
        total_liabilities = abs(df[df["Category"].str.contains("Expense")]["Amount"].sum())
        equity = total_assets - total_liabilities

        st.subheader("📒 Balance Sheet (Simplified)")
        st.write(f"**Assets:** {total_assets:,.2f}")
        st.write(f"**Liabilities:** {total_liabilities:,.2f}")
        st.write(f"**Equity:** {equity:,.2f}")

        # Ratios
        st.subheader("📈 Ratios")
        ratios = {
            "Net Profit Margin (%)": (net_profit / income * 100) if income != 0 else 0,
            "Debt-to-Equity": (total_liabilities / equity) if equity != 0 else 0,
            "Equity Ratio (%)": (equity / total_assets * 100) if total_assets != 0 else 0,
        }
        st.table(pd.DataFrame(ratios, index=["Value"]).T)

        # Charts
        st.subheader("📊 Charts")
        expense_df = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
        if not expense_df.empty:
            st.bar_chart(expense_df)
        cash_flow = df.groupby("Date")["Amount"].sum().cumsum()
        st.line_chart(cash_flow)

        # Valuation (very simple)
        st.subheader("💡 Enterprise Valuation")
        dcf_ev = net_profit * 5  # simple proxy
        ev_ebitda = net_profit * 6
        ev_revenue = income * 1.5
        st.write(f"DCF Proxy EV: {dcf_ev:,.2f}")
        st.write(f"EV/EBITDA Proxy: {ev_ebitda:,.2f}")
        st.write(f"Revenue Multiple EV: {ev_revenue:,.2f}")

        # PDF export
        def create_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, "Financial Report", ln=True, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Revenue: {income:,.2f}", ln=True)
            pdf.cell(0, 10, f"Expenses: {expenses:,.2f}", ln=True)
            pdf.cell(0, 10, f"Net Profit: {net_profit:,.2f}", ln=True)
            pdf.cell(0, 10, f"Assets: {total_assets:,.2f}", ln=True)
            pdf.cell(0, 10, f"Liabilities: {total_liabilities:,.2f}", ln=True)
            pdf.cell(0, 10, f"Equity: {equity:,.2f}", ln=True)
            pdf.cell(0, 10, f"DCF EV: {dcf_ev:,.2f}", ln=True)
            pdf.cell(0, 10, f"EV/EBITDA EV: {ev_ebitda:,.2f}", ln=True)
            pdf.cell(0, 10, f"Revenue Multiple EV: {ev_revenue:,.2f}", ln=True)
            tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf.output(tmp_pdf.name)
            return tmp_pdf.name

        if st.button("📥 Download PDF"):
            pdf_file = create_pdf()
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF", data=f, file_name="report.pdf", mime="application/pdf")
            os.remove(pdf_file)

        # Excel export
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Transactions")
            pd.DataFrame({
                "Metric": ["Revenue", "Expenses", "Net Profit", "Assets", "Liabilities", "Equity"],
                "Value": [income, expenses, net_profit, total_assets, total_liabilities, equity]
            }).to_excel(writer, index=False, sheet_name="Statements")
        st.download_button("📥 Download Excel", data=output.getvalue(),
                           file_name="financials.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

