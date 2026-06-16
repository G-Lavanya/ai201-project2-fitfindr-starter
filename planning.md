# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
It searches the mock listings dataset for items matching the description,
optional size, and optional price ceiling.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
 search_listings(description, size, max_price)
 description(str)-> Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
 size(str)-> Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
 max_price(float)->  Maximum price (inclusive), or None to skip price filtering.
   
   
**What it returns:**
list[dict] — a list of matching listing dicts sorted by relevance score (best match first).
Each dict contains: id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform.
 
**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Returns an empty list if nothing matches — does NOT raise an exception.

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
 suggest_outfit(new_item, wardrobe) → str
Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

**What it returns:**
<!-- Describe the return value -->
A non-empty string with outfit suggestions.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
- If the wardrobe is empty, offer general styling advice for the item
- rather than raising an exception or returning an empty string.

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
- Generate a short, shareable outfit caption for the thrifted find.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- create_fit_card(outfit, new_item)               
- Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.


**What it returns:**
<!-- Describe the return value -->
- str:A 2–4 sentence string usable as an Instagram/TikTok caption.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- If outfit is empty or missing, return a descriptive error message
- string — do NOT raise an exception.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
search_listings
1. Load all listings with load_listings().
2. Filter by max_price and size (if provided).
3. Score each remaining listing by keyword overlap with `description`.
4. Drop any listings with a score of 0 (no relevant matches).
5. Sort by score, highest first, and return the listing dicts.

suggest_outfit
1. Check whether wardrobe['items'] is empty.
2. If empty: call the LLM with a prompt for general styling ideas
(what kinds of items pair well, what vibe it suits, etc.).
3. If not empty: format the wardrobe items into a prompt and ask
the LLM to suggest specific outfit combinations using the new item
and named pieces from the wardrobe.
4. Return the LLM's response as a string.

create_fit_card
1. Guard against an empty or whitespace-only outfit string.
2. Build a prompt that gives the LLM the item details and the outfit,
and asks for a caption matching the style guidelines above.
3. Call the LLM and return the response.

The agent always calls tools in fixed order: search_listings → suggest_outfit → create_fit_card. It calls the next tool only if the previous one succeeded. If search_listings returns an empty list, the agent sets session["error"] and stops — it does not proceed to suggest_outfit with no item. There are no branches beyond this one early-exit condition.
---

## State Management

**How does information from one tool get passed to the next?**

All state for a single user interaction lives in one `session` dict, initialized by `_new_session()` at the start of `run_agent()`. Each tool writes its output into a specific key; the next tool reads from that key.

| Key | Set by | Read by | Contains |
|-----|--------|---------|----------|
| `query` | `run_agent` (input) | query parser | Original natural-language user input |
| `parsed` | query parser (regex) | `search_listings` | Extracted `description`, `size`, `max_price` |
| `search_results` | `search_listings` | Step 4 selector | List of matching listing dicts |
| `selected_item` | Step 4 selector | `suggest_outfit`, `create_fit_card` | Top-scored listing dict |
| `wardrobe` | `run_agent` (input) | `suggest_outfit` | User's wardrobe dict |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` | Outfit suggestion string from LLM |
| `fit_card` | `create_fit_card` | caller / UI | Final Instagram-style caption string |
| `error` | any step on failure | caller / UI | Helpful error message; remaining output keys stay `None` |

The agent stops early if `search_results` is empty — it sets `session["error"]` and returns without calling `suggest_outfit` or `create_fit_card`.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]` to a helpful message and returns the session early. `suggest_outfit` and `create_fit_card` are never called. |
| suggest_outfit | Wardrobe is empty | Calls the LLM with a general styling prompt instead of a wardrobe-specific one. Never raises an exception or returns an empty string. |
| create_fit_card | Outfit input is empty or whitespace | Returns a descriptive error string immediately without calling the LLM. Does NOT raise an exception. |

---

## Architecture

```
User query + wardrobe choice
        │
        ▼
  run_agent(query, wardrobe)
        │
        ▼
  Parse query with regex
  → description, size, max_price
  → stored in session["parsed"]
        │
        ▼
  search_listings(description, size, max_price)
  → searches listings.json
  → stored in session["search_results"]
        │
        ├─── empty? ──► set session["error"] ──► return session (early exit)
        │
        ▼
  select session["search_results"][0]
  → stored in session["selected_item"]
        │
        ▼
  suggest_outfit(selected_item, wardrobe)
  → calls Groq LLM
  → stored in session["outfit_suggestion"]
        │
        ▼
  create_fit_card(outfit_suggestion, selected_item)
  → calls Groq LLM
  → stored in session["fit_card"]
        │
        ▼
  return session
        │
        ▼
  handle_query() in app.py formats and sends to Gradio UI
  → Panel 1: selected_item details
  → Panel 2: outfit_suggestion
  → Panel 3: fit_card
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I used Claude Code with the Tool 1 spec (inputs, return value, failure mode) to implement `search_listings()` using `load_listings()` from the data loader. I verified it by running `python3 tools.py` with 3 test queries (with size, with price, with both) and confirmed it returned correctly sorted results.

For `suggest_outfit()` and `create_fit_card()`, I gave Claude the Tool 2 and Tool 3 specs plus the Groq client pattern and verified the LLM calls returned non-empty strings before moving on.

**Milestone 4 — Planning loop and state management:**

I gave Claude the State Management table and the agent.py TODO steps to implement `run_agent()`. I used regex to parse description, size, and max_price from the query string. I verified the full loop by running `python3 agent.py` and checking both the happy path (found item + outfit + fit card) and the no-results path (error message set, no crash).

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query using regex.
- Extracts: `description = "vintage graphic tee"`, `max_price = 30.0`, `size = None`
- Stored in `session["parsed"]`

**Step 2:**
Calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`.
- Loads all 40 listings from `listings.json`
- Filters out listings priced over $30
- Scores remaining listings by keyword overlap with "vintage graphic tee"
- Returns sorted list — e.g. top result: "Y2K Baby Tee — Butterfly Print" at $18
- Stored in `session["search_results"]`; top item stored in `session["selected_item"]`

**Step 3:**
Calls `suggest_outfit(selected_item, wardrobe)` with the Y2K Baby Tee and the example wardrobe (10 items).
- Wardrobe is not empty, so formats wardrobe items into a prompt
- Asks Groq LLM to suggest 1–2 outfits combining the tee with existing wardrobe pieces
- Returns a string like: "Pair the Y2K Baby Tee with your baggy straight-leg jeans and platform boots for a vintage streetwear look..."
- Stored in `session["outfit_suggestion"]`

**Step 4:**
Calls `create_fit_card(outfit_suggestion, selected_item)`.
- Builds a prompt with the item title, price, platform, and outfit suggestion
- Asks Groq LLM to write a casual Instagram caption
- Returns a 2–4 sentence caption
- Stored in `session["fit_card"]`

**Final output to user:**
Three panels appear in the Gradio UI:
- **Panel 1 (Top listing found):** "Y2K Baby Tee — Butterfly Print / Price: $18 / Size: S/M / Condition: excellent / Platform: depop / ..."
- **Panel 2 (Outfit idea):** The full outfit suggestion from the LLM
- **Panel 3 (Your fit card):** The Instagram-style caption from the LLM
