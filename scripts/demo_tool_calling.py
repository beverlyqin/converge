from backend.app.agent.meetup_agent import run_meetup_agent


question = (
    "My sister and I want to meet on November 13, 2026. "
    "I am leaving JFK between 5 PM and midnight Eastern Time. "
    "She is leaving SEA between 2 PM and 8 PM Pacific Time. "
    "Find a good meeting destination with at most one stop and "
    "no more than a 2 hour arrival gap. "
    "I also have an Amex Platinum. "
    "Tell me what lounges I can use at JFK before my flight."
)


answer = run_meetup_agent(question)

print(answer)