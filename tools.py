"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """

    load_listings()
    max_price = max_price if max_price is not None else float("inf")
    size = size.lower() if size else None
    description_keywords = set(description.lower().split())

    scored_listings = []
    for listing in load_listings():
        if listing["price"] > max_price:
            continue
        if size and size not in listing["size"].lower():
            continue

        listing_keywords = set(listing["title"].lower().split()) | set(
            listing["description"].lower().split()
        )
        score = len(description_keywords & listing_keywords)
        if score > 0:
            # Tuples signal "this pair belongs together and won't be modified" 
            # — a score and its listing are a fixed pair. Lists signal 
            # "this might grow or change." 
            # Since you're never adding to the (score, listing) pair, 
            # a tuple is the more accurate choice. But functionally, either works.
            scored_listings.append((score, listing)) 

    scored_listings.sort(key=lambda x: x[0], reverse=True)
    return [listing for score, listing in scored_listings]

"""for score, listing in scored_listings:
    result.append(listing)   # ignore score, only keep listing
return result
"""

    # Replace this with your implementation
    #return []


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    if not wardrobe.get("items"):
        # Path A: empty wardrobe — give general styling advice
        prompt = (
            f"Suggest styling advice for a new thrifted item: {new_item['title']}\n"
            f"{new_item['description']}\n"
            f"What kinds of items pair well with it, and what vibe does it suit?"
        )
    else:
        # Path B: non-empty wardrobe — suggest specific outfits
        wardrobe_items = "\n".join(
            f"- {item['name']} ({item['category']})"
            for item in wardrobe["items"]
        )
        prompt = (
            f"I have a new thrifted item: {new_item['title']} - {new_item['description']}\n"
            f"My current wardrobe includes:\n{wardrobe_items}\n"
            "Suggest 1-2 complete outfit combinations using the new item and pieces from my wardrobe. "
            "Be specific about which items to pair together and the overall vibe of each outfit."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
   

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """

    client = _get_groq_client()
    if not outfit.strip():
        return "Error: No outfit suggestion provided. Cannot create fit card."
    prompt = (
        f"Create a short, casual, and authentic Instagram caption for an OOTD post featuring this thrifted item:\n"
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']} on {new_item['platform']}\n"
        f"Outfit suggestion: {outfit}\n\n"
        "The caption should mention the item name, price, and platform naturally, capture the outfit vibe in specific terms, and sound different each time for different inputs."
    )
    # Replace this with your implementation
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    # Example test for search_listings
    results = search_listings("vintage graphic tee", size="M", max_price=30)
    print(f"Found {len(results)} matching listings:")
    for listing in results:
        print(f"- {listing['title']} (${listing['price']})")

    # Test suggest_outfit (once implemented)
    if results:
        suggestion = suggest_outfit(results[0], get_example_wardrobe())
        print(f"\nOutfit: {suggestion}")

    # Test create_fit_card (once implemented)
        card = create_fit_card(suggestion, results[0])
        print(f"\nFit card: {card}")


                                            
