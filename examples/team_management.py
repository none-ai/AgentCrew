"""
Team Management Example

Demonstrates:
1. Creating custom teams
2. Adding/removing agents
3. Managing agent roles
4. Saving team configurations
"""

from AgentCrew.agents import Agent, AgentTeam, AGENT_ROLES, load_teams, save_teams


def main():
    print("=" * 50)
    print("Team Management Demo")
    print("=" * 50)
    
    # First, load existing teams
    teams = load_teams()
    
    print("\n📋 Available Roles:")
    for role_code, role_info in AGENT_ROLES.items():
        print(f"   • {role_code}: {role_info['title']} - {role_info['description']}")
    
    # Create a custom team
    print("\n🏗️ Creating custom team...")
    
    custom_team_config = {
        "name": "My Custom Team",
        "members": [
            {"role": "pm", "name": "Alice", "active": True},
            {"role": "architect", "name": "Bob", "active": True},
            {"role": "developer", "name": "Charlie", "active": True},
            {"role": "developer", "name": "Diana", "active": True},
            {"role": "qa", "name": "Eve", "active": True},
            {"role": "techwriter", "name": "Frank", "active": True},
        ]
    }
    
    custom_team = AgentTeam("my_custom_team", custom_team_config)
    teams["my_custom_team"] = custom_team
    
    # Display team status
    status = custom_team.get_status()
    print(f"\n✅ Created team: {status['name']}")
    print(f"   Members: {status['member_count']}")
    for member in status['members']:
        print(f"   • {member['role_title']}: {member['name']}")
    
    # Get specific agent
    print("\n👤 Getting agent details...")
    alice = custom_team.get_agent("Alice")
    if alice:
        print(f"   Name: {alice.name}")
        print(f"   Role: {alice.role}")
        print(f"   Active Tasks: {len(alice.tasks)}")
    
    # Save team configuration
    print("\n💾 Saving team configuration...")
    save_teams(teams, "data/my_teams.json")
    print("   ✅ Saved to data/my_teams.json")


if __name__ == "__main__":
    main()
