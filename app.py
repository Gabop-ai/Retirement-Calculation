import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Comprehensive Household Retirement & Tax Simulator", page_icon="📈", layout="wide")

st.title("📈 Comprehensive Household Retirement & Tax Simulator (Tax-Optimized)")
st.markdown("Advanced multi-asset retirement projection model incorporating dual-income timelines, automated pre-71 RRSP meltdowns, tax bracket management, and Alberta tax optimization.")

st.sidebar.header("⚙️ Simulation Controls")

# 1. Macro & Return Assumptions
with st.sidebar.expander("📊 Macro & Return Assumptions", expanded=True):
   annual_return = st.number_input("Annual Compound Return Rate (%)", min_value=0.0, max_value=15.0, value=4.75, step=0.25) / 100.0
   target_income = st.number_input("Target Annual Household Gross Income ($CAD)", min_value=50000, max_value=500000, value=200000, step=5000)
   life_expectancy = st.slider("Model End Age (Life Expectancy)", 80, 100, 89)
   enable_meltdown = st.checkbox("Enable Pre-71 Tax-Optimized RRSP Meltdown", value=True, help="Voluntarily draws down RRSP/LIRAs in your 60s to fill lower tax brackets and avoid age-71 mandatory minimum spikes.")

# 2. Household Timeline
with st.sidebar.expander("👥 Household Timeline", expanded=False):
   current_age_user = st.number_input("Your Current Age", 20, 80, 65)  # Older spouse set to 65
   current_age_spouse = st.number_input("Spouse's Current Age", 20, 80, 55)  # Younger spouse set to 55
   retirement_age_user = st.number_input("Your Target Retirement Age", 50, 75, 65)
   retirement_age_spouse = st.number_input("Spouse's Target Retirement Age", 50, 75, 55)

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
   user_rrsp_annual_contrib = st.number_input("User Annual RRSP Contribution ($)", value=0, step=1000)
   user_tfsa_annual_contrib = st.number_input("User Annual TFSA Contribution ($)", value=0, step=500)
   spouse_rrsp_annual_contrib = st.number_input("Spouse Annual RRSP Contribution ($)", value=0, step=1000)
   spouse_tfsa_annual_contrib = st.number_input("Spouse Annual TFSA Contribution ($)", value=0, step=500)

# 5. Pensions & Guaranteed Income
with st.sidebar.expander("🛡️ Pensions & Guaranteed Income", expanded=False):
   cpp_oas_annual = st.number_input("Combined CPP & OAS (Age 65+) ($)", value=53800, step=1000)
   spouse_company_pension = st.number_input("Spouse Company Pension (Starts at Spouse Retirement) ($)", value=29000, step=1000)

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

# Alberta Progressive Tax Estimation Function (Per-Person)
def estimate_alberta_tax_per_person(income):
   if income <= 0:
       return 0.0
   if income <= 58523:
       tax = income * 0.15  # Fixed lower bracket approximation for personal splitting
   elif income <= 117045:
       tax = 8778 + (income - 58523) * 0.305
   elif income <= 181440:
       tax = 26627 + (income - 117045) * 0.38
   else:
       tax = 51100 + (income - 181440) * 0.42
   return tax

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
   
   # Growth Step
   u_rrsp *= (1 + r); u_lira *= (1 + r); u_tfsa_mf *= (1 + r); u_tfsa_etf *= (1 + r); u_mf *= (1 + r)
   s_rrsp *= (1 + r); s_tfsa *= (1 + r); s_mf *= (1 + r)
   ul_user *= (1 + r); ul_spouse *= (1 + r)

   # Determine baseline fixed incomes
   user_pension = cpp_oas_annual if age >= 65 else 0.0
   spouse_pension = spouse_company_pension
   if spouse_age_current >= 65:
       spouse_pension += cpp_oas_annual

   # Mandatory RRIF minimum values
   u_rrif_min = (u_rrsp + u_lira) * get_rrif_minimum_pct(age)
   s_rrif_min = s_rrsp * get_rrif_minimum_pct(spouse_age_current)
   mandatory_taxable_draw = u_rrif_min + s_rrif_min

   # Strategy Waterfall: Calculate required portfolio income
   total_guaranteed = user_pension + spouse_pension
   base_needed = max(0.0, target_income - total_guaranteed)
   
   remaining_cash_needed = max(base_needed, mandatory_taxable_draw)
   
   # 1. Take Mandatory RRIF draws first
   drawn_rrsp_lira = min(remaining_cash_needed, mandatory_taxable_draw)
   if mandatory_taxable_draw > 0:
       u_rrsp -= min(u_rrsp, u_rrif_min)
       s_rrsp -= min(s_rrsp, s_rrif_min)
   remaining_cash_needed -= drawn_rrsp_lira

   # 2. Spend down Non-Registered accounts next to protect TFSA room and keep brackets down
   total_non_reg = u_mf + s_mf
   drawn_non_reg = min(remaining_cash_needed, total_non_reg)
   if total_non_reg > 0:
       ratio = u_mf / total_non_reg if total_non_reg > 0 else 0.5
       u_mf -= drawn_non_reg * ratio
       s_mf -= drawn_non_reg * (1 - ratio)
   remaining_cash_needed -= drawn_non_reg

   # 3. Use Discretionary RRSP Draw for shortfall (controlled meltdown staging)
   total_rrsp_pool = u_rrsp + s_rrsp
   drawn_extra_rrsp = min(remaining_cash_needed, total_rrsp_pool)
   if total_rrsp_pool > 0:
       u_rrsp -= drawn_extra_rrsp * 0.5
       s_rrsp -= drawn_extra_rrsp * 0.5
   remaining_cash_needed -= drawn_extra_rrsp

   # 4. TFSA serves as the absolute last resort to maintain compounding and protect OAS thresholds
   total_tfsa = u_tfsa_mf + u_tfsa_etf + s_tfsa
   drawn_tfsa = min(remaining_cash_needed, total_tfsa)
   if total_tfsa > 0:
       s_tfsa -= drawn_tfsa * 0.5
       u_tfsa_mf -= drawn_tfsa * 0.5
   remaining_cash_needed -= drawn_tfsa

   # 5. Voluntary Pre-71 Meltdown Strategy
   vol_rrsp_meltdown = 0.0
   if enable_meltdown and (age < 71 or spouse_age_current < 71):
       current_taxable_est = total_guaranteed + drawn_rrsp_lira + drawn_extra_rrsp
       # Keep household taxable income under lower brackets to avoid spikes
       headroom = 117045.0 - current_taxable_est
       if headroom > 5000:
           vol_rrsp_meltdown = min(headroom * 0.4, u_rrsp + s_rrsp)
           u_rrsp -= vol_rrsp_meltdown * 0.5
           s_rrsp -= vol_rrsp_meltdown * 0.5
           # Reinvest surplus meltdown room straight back into tax-free TFSA
           s_tfsa += vol_rrsp_meltdown * 0.5

   # TAX SPLITTING LOGIC ENGINE
   total_taxable_income = total_guaranteed + drawn_rrsp_lira + drawn_extra_rrsp + vol_rrsp_meltdown
   
   # Pension Splitting Eligibility Check
   if age >= 65 and spouse_age_current >= 65:
       # Optimal 50/50 split across brackets
       user_share = total_taxable_income * 0.5
       spouse_share = total_taxable_income * 0.5
   elif age >= 65 and spouse_age_current < 65:
       # Split what is legally allowed (User can split their RRIF income down to younger spouse)
       eligible_to_split = drawn_rrsp_lira + drawn_extra_rrsp + vol_rrsp_meltdown
       user_share = user_pension + (eligible_to_split * 0.5)
       spouse_share = spouse_pension + (eligible_to_split * 0.5)
   else:
       # No splitting allowed yet (under 65)
       user_share = user_pension + (drawn_rrsp_lira + drawn_extra_rrsp + vol_rrsp_meltdown) * 0.5
       spouse_share = spouse_pension + (drawn_rrsp_lira + drawn_extra_rrsp + vol_rrsp_meltdown) * 0.5

   # Calculate progressive personal tax totals
   tax_user = estimate_alberta_tax_per_person(user_share)
   tax_spouse = estimate_alberta_tax_per_person(spouse_share)
   est_tax = round(tax_user + tax_spouse, -2)
   
   eff_tax_rate = round((est_tax / total_taxable_income) * 100, 1) if total_taxable_income > 0 else 0.0
   total_portfolio_draw = drawn_rrsp_lira + drawn_non_reg + drawn_tfsa + drawn_extra_rrsp
   total_household_portfolio = u_rrsp + u_lira + u_tfsa_mf + u_tfsa_etf + s_rrsp + s_tfsa + u_mf + s_mf

   results.append({
       "Age": age,
       "Spouse Age": spouse_age_current,
       "Portfolio Drawdown": round(total_portfolio_draw),
       "Vol. RRSP Meltdown": round(vol_rrsp_meltdown),
       "Pensions": round(total_guaranteed),
       "Total Gross Income": round(total_taxable_income),
       "Est. Tax Paid": round(est_tax),
       "Effective Tax Rate (%)": eff_tax_rate,
       "RRSP/LIRA Balances": round(u_rrsp + u_lira + s_rrsp),
       "TFSA Balances": round(u_tfsa_mf + u_tfsa_etf + s_tfsa),
       "Non-Reg Balances": round(u_mf + s_mf),
       "UL Cash Value": round(ul_user + ul_spouse),
       "Total Household Portfolio": round(total_household_portfolio)
   })

df_results = pd.DataFrame(results)

# Display DataFrame
st.subheader("📋 Tax-Optimized Household Projection Ledger")
st.dataframe(df_results.style.format({
   "Portfolio Drawdown": "${:,.0f}",
   "Vol. RRSP Meltdown": "${:,.0f}",
   "Pensions": "${:,.0f}",
   "Total Gross Income": "${:,.0f}",
   "Est. Tax Paid": "${:,.0f}",
   "Effective Tax Rate (%)": "{:.1f}%",
   "RRSP/LIRA Balances": "${:,.0f}",
   "TFSA Balances": "${:,.0f}",
   "Non-Reg Balances": "${:,.0f}",
   "UL Cash Value": "${:,.0f}",
   "Total Household Portfolio": "${:,.0f}"
}))
