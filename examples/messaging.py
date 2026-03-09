"""
Messaging Example

Demonstrates inter-agent communication:
1. Send direct messages
2. Broadcast messages
3. Subscribe to message types
4. Query message history
"""

from AgentCrew import get_communication, MessageType, load_teams


def notification_handler(message):
    """Handler for notification messages"""
    print(f"🔔 [NOTIFICATION] {message.sender} -> {message.receiver}: {message.content}")


def main():
    print("=" * 50)
    print("Messaging Demo")
    print("=" * 50)
    
    # Get communication manager
    comm = get_communication()
    
    # Load teams to get agent names
    teams = load_teams()
    team = teams.get("AgentCrew_dev")
    agents = team.get_all_agents()
    
    # Subscribe to notifications
    comm.message_bus.subscribe(
        receiver="PM-001",
        msg_type=MessageType.NOTIFICATION,
        callback=notification_handler
    )
    
    print("\n📨 Sending direct messages...")
    
    # Send direct messages
    messages = [
        ("Developer-A", "PM-001", "Design document ready for review", MessageType.CHAT),
        ("QA-001", "PM-001", "Test cases completed", MessageType.CHAT),
        ("System", "PM-001", "Sprint goal achieved!", MessageType.NOTIFICATION),
    ]
    
    for sender, receiver, content, msg_type in messages:
        msg_id = comm.send_message(sender, receiver, content, msg_type)
        print(f"   ✅ Sent: {sender} -> {receiver}: {content[:30]}...")
    
    print("\n📢 Broadcasting...")
    
    # Broadcast to all
    broadcast_id = comm.broadcast(
        sender="System",
        content="All teams please attend the standup meeting at 10 AM",
        msg_type=MessageType.BROADCAST
    )
    print(f"   ✅ Broadcast ID: {broadcast_id}")
    
    print("\n📬 Checking inbox for PM-001...")
    
    # Get messages for PM-001
    inbox = comm.get_inbox("PM-001")
    for msg in inbox:
        status = "✅ Read" if msg.read else "📩 Unread"
        print(f"   {status} | {msg.type.value} | {msg.sender}: {msg.content[:40]}")


if __name__ == "__main__":
    main()
