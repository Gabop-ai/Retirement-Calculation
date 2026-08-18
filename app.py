import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Comprehensive Household Retirement & Tax Simulator", page_icon="📈", layout="wide")

st.title("📈 Comprehensive Household Retirement & Tax Simulator (Tax-Optimized)")
st.markdown("Advanced multi-asset retirement projection model featuring automated grid-search optimization for dual retirement ages, tax-bracket management, and Alberta tax scaling.")

st.sidebar.header("⚙️ Simulation Controls")

# 1. Macro & Return Assumptions
with st.sidebar.expander("📊 Macro & Return Assumptions", expanded=True):
    annual_return = st.number_input("Annual Compound Return Rate (%)", min_value=0.0, max_value=15.0, value=4.75, step=0.25) / 100.0
    target_income = st.number_input("Target Annual Gross Income ($CAD)", min_value=50000, max_value=500000, value=200000, step=5000)
    life_expectancy = st.slider("Model End Age (Life Expectancy)", 80, 100, 89)
    enable_meltdown = st.checkbox("Enable Pre-71 Tax-Optimized RRSP Meltdown", value=True, help="Voluntarily draws down RRSP/LIRAs in your 60s to fill lower tax brackets.")

# 2. Household Timeline
with st.sidebar.expander("👥 Household Timeline", expanded=False):
    current_age_user = st.number_input("Your Current Age", 20, 80, 51)
    current_age_spouse = st.number_input("Spouse's Current Age", 20, 80, 51)
    retirement_age_user = st.number_input("Your Target Retirement Age", 50, 75, 60)
    retirement_age_spouse = st.number_input("Spouse's Target Retirement Age", 50, 75, 60)

# 3. Starting Portfolio Assets
with st.sidebar.expander("💰 Starting Portfolio Assets", expanded=False):
    st.markdown("**User Assets**")
    user_rrsp_in = st.number_input("User RRSP / RRIF ($)", value=443000, step=10000)
    user_lira_in = st.number_input("User LIRA / LIF ($)", value=562000, step=10000)
    user_tfsa_mf_in = st.number_input("User TFSA Mutual Funds ($)", value=81000, step=5000)
    user_tfsa_etf_in = st.number_input("User TFSA ETFs ($)", value=75000, step=5000)
    user_mutual_funds_in = st.number_input("User Non-Reg Mutual Funds ($)", value=653000, step=10000)
    
    st.markdown("**Spouse Assets**")
    spouse_rrsp_in = st.number_input("Spouse RRSP ($)", value=376550, step=10000)
    spouse_tfsa_in = st.number_input("Spouse TFSA ($)", value=156000, step=5000)
    spouse_tfsa_mf_in = st.number_input("Spouse Non-Reg Mutual Funds ($)", value=80000, step=5000)
    
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

# Core Simulation Engine Function (Encapsulated for Grid Search)
def run_simulation(ret_age_u, ret_age_s):
    start_age = current_age_user
    end_age = life_expectancy
    r = annual_return

    u_rrsp = user_rrsp_in
    u_lira = user_lira_in
    u_tfsa_mf = user_tfsa_mf_in
    u_tfsa_etf = user_tfsa_etf_in
    u_mf = user_mutual_funds_in
    
    s_rrsp = spouse_rrsp_in
    s_tfsa = spouse_tfsa_in
    s_mf = spouse_tfsa_mf_in
    
    ul_user = ul_initial_cash_value_each
    ul_spouse = ul_initial_cash_value_each

    sim_results = []
    total_lifetime_tax = 0.0

    for age in range(start_age, end_age + 1):
        spouse_age_current = current_age_spouse + (age - start_age)
        user_is_working = age < ret_age_u
        spouse_is_working = spouse_age_current < ret_age_s
        is_retired = (age >= ret_age_u) or (spouse_age_current >= ret_age_s)
        
        pensions = 0.0
        required_draw = 0.0
        total_gross = 0.0
        est_tax = 0.0
        eff_tax_rate = 0.0
        vol_rrsp_meltdown = 0.0
        
        if is_retired:
            if spouse_age_current >= ret_age_s:
                pensions += spouse_company_pension
            if age >= 65:
                pensions += cpp_oas_annual
                
            base_needed = max(0.0, target_income - pensions)
            
            mandatory_taxable_draw = 0.0
            u_rrif_min, u_lira_min, s_rrif_min = 0.0, 0.0, 0.0
            if age >= 71:
                u_rrif_min = u_rrsp * get_rrif_minimum_pct(age)
                u_lira_min = u_lira * get_rrif_minimum_pct(age)
                s_rrif_min = s_rrsp * get_rrif_minimum_pct(age)
                mandatory_taxable_draw = u_rrif_min + u_lira_min + s_rrif_min

            total_needed_cash = max(base_needed, mandatory_taxable_draw)
            remaining_cash_needed = total_needed_cash
            
            # Waterfall Drawdown Logic
            drawn_rrsp_lira = min(remaining_cash_needed, mandatory_taxable_draw)
            remaining_cash_needed -= drawn_rrsp_lira
            
            total_non_reg_avail = u_mf + s_mf
            drawn_non_reg = min(remaining_cash_needed, total_non_reg_avail)
            remaining_cash_needed -= drawn_non_reg
            
            total_tfsa_avail = u_tfsa_mf + u_tfsa_etf + s_tfsa
            drawn_tfsa = min(remaining_cash_needed, total_tfsa_avail)
            remaining_cash_needed -= drawn_tfsa
            
            total_rrsp_lira_pool = u_rrsp + u_lira + s_rrsp - drawn_rrsp_lira
            drawn_extra_rrsp = min(remaining_cash_needed, max(0.0, total_rrsp_lira_pool))
            remaining_cash_needed -= drawn_extra_rrsp
            
            # Pre-71 Meltdown Routine
            if enable_meltdown and age < 71:
                current_taxable_est = pensions + drawn_rrsp_lira + drawn_extra_rrsp
                headroom = 117045.0 - current_taxable_est
                if headroom > 5000:
                    available_to_melt = u_rrsp + u_lira + s_rrsp - drawn_rrsp_lira - drawn_extra_rrsp
                    vol_rrsp_meltdown = min(headroom * 0.6, available_to_melt)
                    vol_rrsp_meltdown = max(0.0, vol_rrsp_meltdown)

            total_portfolio_draw = drawn_rrsp_lira + drawn_non_reg + drawn_tfsa + drawn_extra_rrsp
            required_draw = total_portfolio_draw
                
            total_gross = round(required_draw + pensions + vol_rrsp_meltdown, 2)
            est_tax = estimate_alberta_tax(total_gross)
            total_lifetime_tax += est_tax
            eff_tax_rate = round((est_tax / total_gross) * 100, 1) if total_gross > 0 else 0.0
            
            surplus_meltdown_cash = max(0.0, vol_rrsp_meltdown - max(0.0, target_income - (pensions + required_draw)))
            if surplus_meltdown_cash > 0:
                u_tfsa_etf += surplus_meltdown_cash

            # Asset deductions
            if total_non_reg_avail > 0 and drawn_non_reg > 0:
                frac_u_mf = u_mf / total_non_reg_avail
                u_mf = max(0.0, u_mf - (drawn_non_reg * frac_u_mf))
                s_mf = max(0.0, s_mf - (drawn_non_reg * (1 - frac_u_mf)))
                
            if total_tfsa_avail > 0 and drawn_tfsa > 0:
                u_tfsa_total = u_tfsa_mf + u_tfsa_etf
                frac_u_tfsa = u_tfsa_total / total_tfsa_avail
                u_tfsa_target_draw = drawn_tfsa * frac_u_tfsa
                if u_tfsa_total > 0:
                    u_tfsa_mf = max(0.0, u_tfsa_mf - (u_tfsa_target_draw * (u_tfsa_mf / u_tfsa_total)))
                    u_tfsa_etf = max(0.0, u_tfsa_etf - (u_tfsa_target_draw * (u_tfsa_etf / u_tfsa_total)))
                s_tfsa = max(0.0, s_tfsa - (drawn_tfsa * (1 - frac_u_tfsa)))

            total_rrsp_lira_pool_start = u_rrsp + u_lira + s_rrsp
            total_rrsp_draw_amt = drawn_rrsp_lira + drawn_extra_rrsp + vol_rrsp_meltdown
            if total_rrsp_lira_pool_start > 0 and total_rrsp_draw_amt > 0:
                u_rrsp = max(0.0, u_rrsp - (total_rrsp_draw_amt * (u_rrsp / total_rrsp_lira_pool_start)))
                u_lira = max(0.0, u_lira - (total_rrsp_draw_amt * (u_lira / total_rrsp_lira_pool_start)))
                s_rrsp = max(0.0, s_rrsp - (total_rrsp_draw_amt * (s_rrsp / total_rrsp_lira_pool_start)))

        total_user_rrsp_lira = round(u_rrsp + u_lira + s_rrsp, 2)
        total_tfsa = round(u_tfsa_mf + u_tfsa_etf + s_tfsa, 2)
        total_non_reg = round(u_mf + s_mf, 2)
        total_ul = round(ul_user + ul_spouse, 2)
        total_portfolio = round(total_user_rrsp_lira + total_tfsa + total_non_reg + total_ul, 2)
        
        sim_results.append({
            "Age": age,
            "Spouse Age": spouse_age_current,
            "Retirement Status": "Retired" if is_is_retired := is_retired else "Accumulating",
            "Portfolio Drawdown": round(required_draw, 0),
            "Vol. RRSP Meltdown": round(vol_rrsp_meltdown, 0),
            "Pensions": round(pensions, 0),
            "Total Gross Income": round(total_gross, 0),
            "Est. Tax Paid": round(est_tax, 0),
            "Effective Tax Rate (%)": eff_tax_rate,
            "RRSP/LIRA Balances": total_user_rrsp_lira,
            "TFSA Balances": total_tfsa,
            "Non-Reg Balances": total_non_reg,
            "UL Cash Value": total_ul,
            "Total Household Portfolio": total_portfolio
        })
        
        if age < end_age:
            if user_is_working:
                u_rrsp += user_rrsp_annual_contrib
                u_tfsa_mf += user_tfsa_annual_contrib * 0.5
                u_tfsa_etf += user_tfsa_annual_contrib * 0.5
            if spouse_is_working:
                s_rrsp += spouse_rrsp_annual_contrib
                s_tfsa += spouse_tfsa_annual_contrib
                
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

-   return pd.DataFrame(sim_results), total_lifetime_tax

# --- OPTIMIZATION TOOL IN SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Automated Retirement Age Optimizer")
if st.sidebar.button("Find Lowest Lifetime Tax Ages"):
    best_tax = float('inf')
    best_combo = (retirement_age_user, retirement_age_spouse)
    
    # Grid search across reasonable retirement ages (e.g., 55 to 68)
    for u_age in range(55, 69):
        for s_age in range(55, 69):
            _, lifetime_tax = run_simulation(u_age, s_age)
            if lifetime_tax < best_tax:
                best_tax = lifetime_tax
                best_combo = (u_age, s_age)
                
    st.sidebar.success(f"Optimal Found! You: Age {best_combo[0]} | Spouse: Age {best_combo[1]} (Est. Lifetime Tax: ${best_tax:,.0f})")

# Run main simulation with current inputs
df_master, total_tax_paid = run_simulation(retirement_age_user, retirement_age_spouse)

# Display Table
st.subheader("📊 Tax-Optimized Projection Schedule & Account Balances")
display_ages = [start_age, 55, 60, 64, retirement_age_user, 66, 70, 71, 75, 80, 85, life_expectancy]
display_ages = sorted(list(set([a for a in display_ages if a <= life_expectancy])))
df_display = df_master[df_master["Age"].isin(display_ages)]

st.metric(label="Estimated Cumulative Lifetime Tax (Selected Ages)", value=f"${total_tax_paid:,.0f}")

st.dataframe(df_display.style.format({
    "Spouse Age": "{:.0f}",
    "Portfolio Drawdown": "${:,.0f}",
    "Vol. RRSP Meltdown": "${:,.0f}",
    "Pensions": "${:,.0f}",
    "Total Gross Income": "${:,.0f}",
    "Est. Tax Paid": "${:,.0f}",
    "Effective Tax Rate (%)": "{}%",
    "RRSP/LIRA Balances": "${:,.0f}",
    "TFSA Balances": "${:,.0f}",
    "Non-Reg Balances": "${:,.0f}",
    "UL Cash Value": "${:,.0f}",
    "Total Household Portfolio": "${:,.0f}"
}), use_container_width=True)

# Visualizations
st.subheader("📈 Long-Term Wealth & Tax-Smoothed Cashflow Trends")
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 11), sharex=True)

axes[0].plot(df_master["Age"], df_master["Total Household Portfolio"] / 1e6, label=f"Total Portfolio ($M) @ {annual_return*100:.2f}% Return", color="navy", linewidth=2.5)
axes[0].set_ylabel("Portfolio Value ($M)")
axes[0].grid(True, linestyle=":", alpha=0.6)
axes[0].legend(loc="upper left")

axes[1].stackplot(
    df_master["Age"],
    df_master["RRSP/LIRA Balances"] / 1e6,
    df_master["TFSA Balances"] / 1e6,
    df_master["Non-Reg Balances"] / 1e6,
    df_master["UL Cash Value"] / 1e6,
    labels=["RRSP / LIRA", "TFSA", "Non-Registered", "Universal Life"],
    colors=["#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"],
    alpha=0.85
)
axes[1].set_ylabel("Asset Mix ($M)")
axes[1].grid(True, linestyle=":", alpha=0.6)
axes[1].legend(loc="upper left")

axes[2].bar(df_master["Age"], df_master["Pensions"] / 1e3, label="Pensions / CPP / OAS", color="skyblue")
axes[2].bar(df_master["Age"], df_master["Portfolio Drawdown"] / 1e3, bottom=df_master["Pensions"] / 1e3, label="Portfolio Drawdowns", color="royalblue")
axes[2].bar(df_master["Age"], df_master["Vol. RRSP Meltdown"] / 1e3, bottom=(df_master["Pensions"] + df_master["Portfolio Drawdown"]) / 1e3, label="Voluntary RRSP Meltdown", color="darkorange")
axes[2].plot(df_master["Age"], df_master["Est. Tax Paid"] / 1e3, label="Est. Tax Paid ($k)", color="crimson", linewidth=2)
axes[2].set_xlabel("Your Age")
axes[2].set_ylabel("Annual Amount ($k)")
axes[2].grid(True, linestyle=":", alpha=0.6)
axes[2].legend(loc="upper left")

plt.tight_layout()
st.pyplot(fig)
