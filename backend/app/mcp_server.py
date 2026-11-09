from mcp.server import MCPServer

from backend.app.tools.flight_tools import (
    search_meetup_options as search_meetup_options_tool,
)
from backend.app.tools.lounge_tools import (
    find_lounges as find_lounges_tool,
    get_lounge_policy as get_lounge_policy_tool,
)


mcp = MCPServer("Flight Meetup")


@mcp.tool()
def find_lounges(
    card: str,
    airport: str,
) -> dict:
    """Find physical airport lounges matching a credit card's lounge networks."""

    return find_lounges_tool.invoke({
        "card": card,
        "airport": airport,
    })


@mcp.tool()
def get_lounge_policy(
    card: str,
    lounge_network: str,
) -> dict:
    """Retrieve lounge access-policy evidence for a card and lounge network."""

    return get_lounge_policy_tool.invoke({
        "card": card,
        "lounge_network": lounge_network,
    })


@mcp.tool()
def search_meetup_options(
    origin_a: str,
    depart_after_a: str,
    depart_before_a: str,
    origin_b: str,
    depart_after_b: str,
    depart_before_b: str,
    max_stops: int = 1,
    max_arrival_gap_minutes: int = 120,
) -> dict:
    """Find and rank meeting destinations for two travelers."""

    return search_meetup_options_tool.invoke({
        "origin_a": origin_a,
        "depart_after_a": depart_after_a,
        "depart_before_a": depart_before_a,
        "origin_b": origin_b,
        "depart_after_b": depart_after_b,
        "depart_before_b": depart_before_b,
        "max_stops": max_stops,
        "max_arrival_gap_minutes": max_arrival_gap_minutes,
    })


if __name__ == "__main__":
    mcp.run()