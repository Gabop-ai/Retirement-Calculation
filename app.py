import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Comprehensive Household Retirement & Tax Simulator", page_icon="📈", layout="wide")

st.title("📈 Comprehensive Household Retirement & Tax Simulator")
st.markdown("Advanced multi-asset retirement projection model incorporating dual-income timelines, phased drawdowns, RRIF minimums, pensions, and progressive Alberta tax optimization.")

st.sidebar.header("⚙️ Simulation Controls")

# 1. Macro & Return Assumptions
with st.sidebar.expander("📊 Macro & Return Assumptions", expanded=True):
    annual_return = st.number_input("Annual Compound Return Rate (%)", min_value=0.0, max_value=15.0, value=6.0, step=0.25) / 100.0
    target_income = st.number_input("Target Annual Gross Income ($CAD)", min_value=50000, max_value=500000, value=230000, step=5000)
    life_expectancy = st.slider("Model End Age (Life Expectancy)", 80, 100, 90)

# 2. Household Timeline
with st.sidebar.expander("👥 Household Timeline", expanded=False):
    current_age_user = st.number_input("Your Current Age", 20, 80, 51)
    current_age_spouse = st.number_input("Spouse's Current Age", 20, 80, 51)
    retirement_age_user = st.number_input("Your Target Retirement Age", 50, 75, 65)
    retirement_age_spouse = st.number_input("Spouse's Target Retirement Age", 50, 75, 60)

# 3. Starting Portfolio Assets
with st.sidebar.expander("💰 Starting Portfolio Assets", expanded=False):
    st.markdown("**User Assets**")
    user_rrsp = st.number_input("User RRSP / RRIF ($)", value=443000, step=10000)
    user_lira = st.number_input("User LIRA / LIF ($)", value=562000, step=10000)
    user_tfsa_mf = st.number_input("User TFSA Mutual Funds ($)", value=81000, step=5000)
    user_tfsa_etf = st.number_input("User TFSA ETFs ($)", value=75000, step=5000)
    user_mutual_funds = st.number_input("User Non-Reg Mutual Funds ($)", value=653000, step=10000)
    
    st.markdown("**Spouse Assets**")
    spouse_rrsp = st.number_input("Spouse RRSP ($)", value=376550, step=10000)
    spouse_tfsa = st.number_input("Spouse TFSA ($)", value=156000, step=5000)
    spouse_tfsa_mf = st.number_input("Spouse Non-Reg Mutual Funds ($)", value=80000, step=5000)
    
    st.markdown("**Insurance / Other**")
    ul_initial_cash_value_each = st.number_input("Universal Life Cash Value (Each Policy) ($)", value=62000, step=5000)

# 4. Annual Contributions (Pre-Retirement)
with st.sidebar.expander("📥 Annual Contributions", expanded=False):
    user_rrsp_annual_contrib = st.number_input("User Annual RRSP Contribution ($)", value=32000, step=1000)
    user_tfsa_annual_contrib = st.number_input("User Annual TFSA Contribution ($)", value=7500, step=500)
    spouse_rrsp_annual_contrib = st.number_input("Spouse Annual RRSP Contribution ($)", value=15000, step=1000)
    spouse_tfsa_annual_contrib = st.number_input("Spouse Annual TFSA Contribution ($)", value=7500, step=500)

# 5. Pensions & Guaranteed Income
with st.sidebar.expander("🛡️ Pensions & Guaranteed Income", expanded=False):
    cpp_oas_annual = st.number_input("Combined CPP & OAS (Age 65+) ($)", value=53800, step=1000)
    spouse_company_pension = st.number_input("Spouse Company Pension (Starts at Spouse Retirement) ($)", value=35000, step=1000)

# RRIF Minimum Table Function
def get_rrif_minimum_pct(age):
    rates = {
        71: 0.0528, 72: 0.0540, 73: 0.0553, 74: 0.0567, 75: 0.0582,
        76: 0.0598, 77: 0.0617, 78: 0.0636, 79: 0.0658, 80: 0.0682,
        81: 0.0708, 82: 0.0738, 83: 0.0771, 84: 0.0808, 85: 0.0851,
        86: 0.0900, 87: 0.0955, 88: 0.1021, 89: 0.1099, 90: 0.1192
    }
    if age < 71:
        return 0.0
    return rates.get(age, 0.20)

# Alberta Progressive Tax Estimation Function
def estimate_alberta_tax(gross_income):
    if gross_income <= 0:
        return 0.0
    if gross_income <= 58523:
        tax = gross_income * 0.22
    elif gross_income <= 117045:
        tax = 12875 + (gross_income - 58523) * 0.305
    elif gross_income <= 181440:
        tax = 30724 + (gross_income - 117045) * 0.38
    else:
        tax = 55194 + (gross_income - 181440) * 0.42
    return round(tax, -2)

# Run Simulation Loop
start_age = current_age_user
end_age = life_expectancy
r = annual_return

u_rrsp, u_lira, u_tfsa_mf, u_tfsa_etf, u_mf = user_rrsp, user_lira, user_tfsa_mf, user_tfsa_etf, user_mutual_funds
s_rrsp, s_tfsa, s_mf = spouse_rrsp, spouse_tfsa, spouse_tfsa_mf
ul_user, ul_spouse = ul_initial_cash_value_each, ul_initial_cash_value_each

results = []

for age in range(start_age, end_age + 1):
    spouse_age_current = current_age_spouse + (age - start_age)
    user_is_working = age < retirement_age_user
    spouse_is_working = spouse_age_current < retirement_age_spouse
    is_retired = (age >= retirement_age_user) or (spouse_age_current >= retirement_age_spouse)
    
    pensions = 0.0
    required_draw = 0.0
    total_gross = 0.0
    est_tax = 0.0
    eff_tax_rate = 0.0
    
    if is_retired:
        if spouse_age_current >= retirement_age_spouse:
            pensions += spouse_company_pension
        if age >= 65:
            pensions += cpp_oas_annual
            
        if age >= 71:
            u_rrif_min = u_rrsp * get_rrif_minimum_pct(age)
            u_lira_min = u_lira * get_rrif_minimum_pct(age)
            s_rrif_min = s_rrsp * get_rrif_minimum_pct(age)
            required_draw = round(u_rrif_min + u_lira_min + s_rrif_min, 2)
        else:
            required_draw = max(0.0, target_income - pensions)
            
        total_gross = round(required_draw + pensions, 2)
        est_tax = estimate_alberta_tax(total_gross)
        eff_tax_rate = round((est_tax / total_gross) * 100, 1) if total_gross > 0 else 0.0
        
    total_portfolio = round(u_rrsp + u_tfsa_mf + u_tfsa_etf + u_mf + u_lira + s_rrsp + s_tfsa + s_mf + ul_user + ul_spouse, 2)
    
    results.append({
        "Age": age,
        "Spouse Age": spouse_age_current,
        "Retirement Status": "Retired" if is_retired else "Accumulating",
        "Portfolio Drawdown": round(required_draw, 0),
        "Pensions": round(pensions, 0),
        "Total Gross Income": round(total_gross, 0),
        "Est. Tax Paid": round(est_tax, 0),
        "Effective Tax Rate (%)": eff_tax_rate,
        "Total Household Portfolio": total_portfolio
    })
    
    # Asset evolution for next year
    if age < end_age:
        draw_ratio = 0.0
        if is_retired and (u_rrsp + u_lira + s_rrsp) > 0:
            draw_ratio = required_draw / (u_rrsp + u_lira + s_rrsp)
        
        u_rrsp = max(0.0, u_rrsp - (u_rrsp * draw_ratio))
        u_lira = max(0.0, u_lira - (u_lira * draw_ratio))
        s_rrsp = max(0.0, s_rrsp - (s_rrsp * draw_ratio))
        
        if user_is_working:
            u_rrsp += user_rrsp_annual_contrib
            u_tfsa_mf += user_tfsa_annual_contrib * 0.5
            u_tfsa_etf += user_tfsa_annual_contrib * 0.5
        if spouse_is_working:
            s_rrsp += spouse_rrsp_annual_contrib
            s_tfsa += spouse_tfsa_annual_contrib
            
        # Growth
        u_rrsp *= (1 + r)
        u_lira *= (1 + r)
        u_tfsa_mf *= (1 + r)
        u_tfsa_etf *= (1 + r)
        u_mf *= (1 + r)
        s_rrsp *= (1 + r)
        s_tfsa *= (1 + r)
        s_mf *= (1 + r)
        ul_user *= (1 + r)
        ul_spouse *= (1 + r)

df_master = pd.DataFrame(results)

# Display Table
st.subheader("📊 Full Projection Summary Schedule")
display_ages = [start_age, 55, 60, 64, retirement_age_user, 66, 70, 71, 75, 80, 85, end_age]
display_ages = sorted(list(set([a for a in display_ages if a <= end_age])))
df_display = df_master[df_master["Age"].isin(display_ages)]

st.dataframe(df_display.style.format({
    "Spouse Age": "{:.0f}",
    "Portfolio Drawdown": "${:,.0f}",
    "Pensions": "${:,.0f}",
    "Total Gross Income": "${:,.0f}",
    "Est. Tax Paid": "${:,.0f}",
    "Effective Tax Rate (%)": "{}%",
    "Total Household Portfolio": "${:,.0f}"
}), use_container_width=True)

# Visualizations
st.subheader("📈 Long-Term Wealth & Cashflow Trends")
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(10, 8), sharex=True)

axes[0].plot(df_master["Age"], df_master["Total Household Portfolio"] / 1e6, label=f"Total Portfolio ($M) @ {r*100:.2f}% Return", color="navy", linewidth=2.5)
axes[0].set_ylabel("Portfolio Value ($ Millions)")
axes[0].grid(True, linestyle=":", alpha=0.6)
axes[0].legend(loc="upper left")

axes[1].bar(df_master["Age"], df_master["Pensions"] / 1e3, label="Pensions / CPP / OAS", color="skyblue")
axes[1].bar(df_master["Age"], df_master["Portfolio Drawdown"] / 1e3, bottom=df_master["Pensions"] / 1e3, label="Portfolio Drawdowns", color="royalblue")
axes[1].plot(df_master["Age"], df_master["Est. Tax Paid"] / 1e3, label="Est. Tax Paid ($k)", color="crimson", linewidth=2)
axes[1].set_xlabel("Your Age")
axes[1].set_ylabel("Annual Amount ($k)")
axes[1].grid(True, linestyle=":", alpha=0.6)
axes[1].legend(loc="upper left")

st.pyplot(fig)
