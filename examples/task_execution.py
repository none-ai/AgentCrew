"""
Task Execution Example

Demonstrates how to:
1. Create tasks
2. Assign tasks to agents
3. Execute tasks
4. Track task status
"""

from AgentCrew import load_teams, get_executor


def main():
    print("=" * 50)
    print("Task Execution Demo")
    print("=" * 50)
    
    # Load teams
    teams = load_teams()
    team = teams.get("AgentCrew_dev")
    
    # Get executor
    executor = get_executor()
    
    # Create multiple tasks
    tasks_data = [
        {
            "title": "Design User Authentication",
            "description": "Design the user authentication system with JWT tokens",
            "task_type": "design"
        },
        {
            "title": "Implement Login API",
            "description": "Create REST API endpoints for user login/logout",
            "task_type": "development"
        },
        {
            "title": "Write Unit Tests",
            "description": "Write unit tests for authentication module",
            "task_type": "testing"
        }
    ]
    
    created_tasks = []
    for task_data in tasks_data:
        task = executor.create_task(**task_data)
        created_tasks.append(task)
        print(f"\n✅ Created task: {task.title} (ID: {task.id})")
    
    # Assign tasks to different agents
    agents = team.get_all_agents()
    for i, task in enumerate(created_tasks):
        agent = agents[i % len(agents)]
        executor.assign_task(task.id, agent.name)
        print(f"📌 Assigned '{task.title}' to {agent.name}")
    
    # Execute tasks
    print("\n🚀 Executing tasks...")
    for task in created_tasks:
        result = executor.execute_task(task.id)
        print(f"   ✅ Completed: {task.title}")
        print(f"      Result: {result.get('result', 'N/A')}")


if __name__ == "__main__":
    main()
