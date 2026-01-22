"""
Demo: Kill Chain Methodology in Action
Shows how RedTeamAgent thinks through the RECON → PLAN → EXPLOIT process
"""

from app.agents.red_team import RedTeamAgent


def main():
    print("=" * 80)
    print(" CodeJanitor Phase 3 (Revised): Kill Chain Demonstration")
    print("=" * 80)
    print()
    
    # Create Red Team agent
    red_team = RedTeamAgent()
    
    # Example 1: SQL Injection vulnerability
    print("📋 Example 1: SQL Injection Attack")
    print("-" * 80)
    
    vulnerable_code = '''
def login(username, password):
    """Vulnerable login function"""
    import sqlite3
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchone() is not None
'''
    
    vulnerability_details = {
        "type": "SQL Injection",
        "description": "User input directly concatenated into SQL query without parameterization",
        "function_code": vulnerable_code
    }
    
    print(f"\n🎯 Target: login.py")
    print(f"⚠️  Vulnerability: {vulnerability_details['type']}")
    print(f"\n📝 Code:")
    print(vulnerable_code)
    print()
    
    # Run Kill Chain validation
    print("🚀 Starting Kill Chain Validation...")
    print()
    
    result = red_team.run_validation(
        target_file="login.py",
        vulnerability_details=vulnerability_details
    )
    
    # Display the thought process
    if result.get("thought_process"):
        tp = result["thought_process"]
        
        print("\n" + "=" * 80)
        print("🔍 PHASE 1: RECON (Reconnaissance)")
        print("=" * 80)
        print(tp.get("recon", "No recon available"))
        
        print("\n" + "=" * 80)
        print("🎯 PHASE 2: PLAN (Attack Strategy)")
        print("=" * 80)
        print(tp.get("plan", "No plan available"))
        
        print("\n" + "=" * 80)
        print("💥 PHASE 3: EXPLOIT (Proof of Concept)")
        print("=" * 80)
        exploit_code = tp.get("exploit_code", "No exploit generated")
        print(exploit_code[:500] + "..." if len(exploit_code) > 500 else exploit_code)
    
    # Show result
    print("\n" + "=" * 80)
    print("🎬 RESULT")
    print("=" * 80)
    
    if result.get("verified"):
        print("✅ EXPLOIT_SUCCESS - Vulnerability confirmed!")
    else:
        print("❌ EXPLOIT_FAILED - Could not verify")
    
    if result.get("output"):
        print(f"\n📤 Output:\n{result['output'][:300]}")
    
    print("\n" + "=" * 80)
    print("✨ Kill Chain Complete")
    print("=" * 80)
    print()
    print("Key Insight: The agent showed its work! You can see:")
    print("  1. 🔍 RECON - Analyzed the code and identified the vulnerability location")
    print("  2. 🎯 PLAN - Described the attack vector and payload strategy")
    print("  3. 💥 EXPLOIT - Generated executable proof-of-concept code")
    print()
    print("This transparency makes the Red Team 'smart' - you understand WHY it")
    print("flagged something, not just THAT it flagged something.")
    print()


if __name__ == "__main__":
    main()
