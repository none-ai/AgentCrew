"""
OpenAgent Basic Usage Example

This example demonstrates the fundamental operations of OpenAgent:
1. Loading agent teams
2. Getting team status
3. Listing available agents
"""

from openagent import load_teams


def main():
    # Load all configured teams
    teams = load_teams()
    
    print("=" * 50)
    print("OpenAgent Basic Usage Demo")
    print("=" * 50)
    
    # Iterate through all teams
    for team_id, team in teams.items():
        print(f"\n📦 Team: {team.name} (ID: {team_id})")
        print("-" * 40)
        
        # Get team status
        status = team.get_status()
        print(f"   Members: {status['member_count']}")
        
        # List all agents in the team
        for agent in team.get_all_agents():
            agent_status = agent.get_status()
            print(f"   👤 {agent_status['role_title']}: {agent_status['name']}")
            print(f"      Active Tasks: {agent_status['active_tasks']}")
            print(f"      Completed: {agent_status['completed_tasks']}")


if __name__ == "__main__":
    main()
