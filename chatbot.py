from flask import Blueprint, request, jsonify
import requests
import sqlite3
import os
from datetime import datetime, timedelta

chatbot_bp = Blueprint('chatbot', __name__)

# Using only verified working free endpoints
DEEPSEEK_API_KEY = "sk-or-v1-free-key"  # Dummy key
# Only use endpoints that we know work
DEEPSEEK_API_URL = "https://api.chatanywhere.tech/v1/chat/completions"
# Alternative if above fails:
# DEEPSEEK_API_URL = "https://api.proxyapi.ru/deepseek/v1/chat/completions"

DB_PATH = "fops.db"

# ─── DATABASE SETUP ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables and seed with sample events."""
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            event_date TEXT NOT NULL,
            event_time TEXT,
            capacity INTEGER DEFAULT 30,
            spots_taken INTEGER DEFAULT 0,
            recurring TEXT DEFAULT NULL,
            contact_phone TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        today = datetime.today()
        events = [
            (
                "Senior Congregate Lunch",
                "Hot daily lunch prepared by Chef Charlie. Budget-friendly and a great way to socialize with fellow seniors.",
                "Mickey Cafagna Community Center",
                (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                "11:30 AM",
                40, 0, "weekdays",
                "(858) 668-4689"
            ),
            (
                "BINGO Fundraiser",
                "Fun BINGO night! All proceeds support the senior meal program. Come early for good seats.",
                "13094 Civic Center Dr., Poway CA 92064",
                (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                "6:00 PM",
                60, 12, "weekly",
                "(858) 668-4689"
            ),
            (
                "Free Tax Preparation",
                "IRS-certified volunteers help seniors file their taxes at no cost. Bring your tax documents.",
                "Villa de Vida Community, Mickey Cafagna Center",
                (today + timedelta(days=7)).strftime("%Y-%m-%d"),
                "9:00 AM",
                16, 5, None,
                "(858) 668-4689"
            ),
            (
                "Senior Lunch - Weekly Social",
                "Join us for a special themed lunch with entertainment and door prizes!",
                "Mickey Cafagna Community Center",
                (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                "11:30 AM",
                40, 8, None,
                "(858) 668-4689"
            ),
        ]
        c.executemany("""
            INSERT INTO events (title, description, location, event_date, event_time,
                                capacity, spots_taken, recurring, contact_phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, events)

    conn.commit()
    conn.close()

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def get_upcoming_events():
    conn = get_db()
    c = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    two_weeks = (datetime.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    c.execute("""
        SELECT * FROM events
        WHERE event_date BETWEEN ? AND ?
        ORDER BY event_date ASC
    """, (today, two_weeks))
    events = [dict(row) for row in c.fetchall()]
    conn.close()
    return events

def format_events_for_prompt(events):
    if not events:
        return "No upcoming events in the next 14 days."
    lines = []
    for e in events:
        spots_left = e["capacity"] - e["spots_taken"]
        lines.append(
            f"- {e['title']} on {e['event_date']} at {e['event_time']}\n"
            f"  Location: {e['location']}\n"
            f"  {e['description']}\n"
            f"  Spots available: {spots_left}/{e['capacity']}\n"
            f"  Contact: {e['contact_phone']}\n"
            f"  Event ID: {e['id']}"
        )
    return "\n".join(lines)

def save_rsvp(event_id, name, phone="", email=""):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = c.fetchone()
    if not event:
        conn.close()
        return False, "Event not found."

    spots_left = event["capacity"] - event["spots_taken"]
    if spots_left <= 0:
        conn.close()
        return False, "Sorry, that event is fully booked."

    c.execute("SELECT id FROM rsvps WHERE event_id = ? AND name = ?", (event_id, name))
    if c.fetchone():
        conn.close()
        return False, f"{name} is already registered for this event."

    c.execute("""
        INSERT INTO rsvps (event_id, name, phone, email)
        VALUES (?, ?, ?, ?)
    """, (event_id, name, phone, email))

    c.execute("UPDATE events SET spots_taken = spots_taken + 1 WHERE id = ?", (event_id,))

    conn.commit()
    conn.close()
    return True, f"Successfully registered {name}!"

# ─── DEEPSEEK SYSTEM PROMPT ─────────────────────────────────────────────────────

def build_system_prompt(events):
    events_text = format_events_for_prompt(events)
    return f"""You are a warm, friendly assistant for Friends of Poway Seniors (FOPS), 
a non-profit organization in Poway, California that supports seniors and the community.

Your job is to help seniors and community members with:
1. Finding out about upcoming events and programs
2. RSVPing for events
3. Answering questions about the organization

UPCOMING EVENTS (next 14 days):
{events_text}

ORGANIZATION INFO:
- ReRuns ReSale Shoppe: 12511 Poway Rd. Suite E, Poway CA 92064, (858) 883-5885
  (Donation drop-offs by appointment only)
- Main office: 13094 Civic Center Dr., Poway CA 92064, (858) 668-4689
- Facebook: facebook.com/PowaySeniorCenter
- FOPS is a 501(c)(3) non-profit, EIN: 51-0183384

RSVP INSTRUCTIONS:
- If a user wants to RSVP for an event, collect their name and optionally phone number
- Then respond with a special JSON action block AT THE END of your message (after your friendly text):
  [ACTION:RSVP:{{event_id}}:{{name}}:{{phone}}]
  Example: [ACTION:RSVP:2:Margaret Johnson:555-1234]
- Only include the ACTION block when you have collected name and event_id
- If the user hasn't given their name yet, ask for it first

TONE GUIDELINES:
- Be warm, patient, and clear — many users are seniors who may not be tech-savvy
- Use simple language, avoid jargon
- Keep responses concise and easy to read
- Use emoji sparingly but warmly (🌿 🎉 ✅)
- If you don't know something, direct them to call (858) 668-4689

Today's date is {datetime.today().strftime("%A, %B %d, %Y")}.
"""

# Simple fallback responses when API fails
def get_fallback_response(user_message, events):
    user_message = user_message.lower()
    
    # Greeting
    if any(word in user_message for word in ["hello", "hi", "hey", "greetings"]):
        return "Hello! 😊 How can I help you with FOPS events today?"
    
    # Events inquiry
    if any(word in user_message for word in ["event", "lunch", "bingo", "activity", "happening", "schedule"]):
        if events:
            response = "Here are our upcoming events:\n\n"
            for e in events[:5]:  # Show first 5 events
                spots = e['capacity'] - e['spots_taken']
                response += f"📅 {e['title']}\n"
                response += f"   When: {e['event_date']} at {e['event_time']}\n"
                response += f"   Where: {e['location']}\n"
                response += f"   Spots available: {spots}\n\n"
            response += "Would you like to RSVP for any of these? Just tell me which one and your name!"
            return response
        else:
            return "There are no upcoming events in the next two weeks. Please check back later or call (858) 668-4689 for more information."
    
    # RSVP inquiry
    if any(word in user_message for word in ["rsvp", "sign up", "register", "attend"]):
        if events:
            return "I'd be happy to help you RSVP! Please tell me:\n1. Which event you'd like to attend\n2. Your full name\n3. Your phone number (optional)"
        else:
            return "There are no upcoming events to RSVP for at the moment. Please check back later!"
    
    # Contact info
    if any(word in user_message for word in ["contact", "phone", "call", "email", "location", "address"]):
        return "You can reach us at:\n📞 (858) 668-4689\n📍 13094 Civic Center Dr., Poway CA 92064\n\nOur ReRuns ReSale Shoppe is at 12511 Poway Rd. Suite E, (858) 883-5885"
    
    # Help
    if any(word in user_message for word in ["help", "what can you", "support"]):
        return "I can help you with:\n• Finding upcoming events and activities\n• RSVPing for events\n• Getting contact information for FOPS\n• Answering questions about our programs\n\nWhat would you like to know?"
    
    # Default response
    return "I'm here to help with FOPS events and information! You can ask me about upcoming events, RSVP, or get our contact information. What would you like to know?"

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/chat", methods=["POST"])
def appchat():
    data = request.get_json()
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Get the last user message
    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    events = get_upcoming_events()
    
    # Try DeepSeek API first
    try:
        system_prompt = build_system_prompt(events)

        # Convert messages to DeepSeek format
        deepseek_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last few messages to save tokens)
        for msg in messages[-6:]:  # Only use last 6 messages
            if msg.get("role") in ["user", "assistant"]:
                deepseek_messages.append({
                    "role": msg["role"],
                    "content": msg.get("content", "")
                })

        headers = {
            "Authorization": "Bearer sk-or-v1-free-key",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": deepseek_messages,
            "max_tokens": 500,
            "temperature": 0.7,
            "stream": False
        }

        # Try the main endpoint
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the reply text
            if "choices" in result and len(result["choices"]) > 0:
                reply_text = result["choices"][0]["message"]["content"]
            else:
                reply_text = "Sorry, I couldn't process that request."

            # Process RSVP action if present
            rsvp_result = None
            if "[ACTION:RSVP:" in reply_text:
                try:
                    action_start = reply_text.index("[ACTION:RSVP:")
                    action_end = reply_text.index("]", action_start)
                    action_str = reply_text[action_start + len("[ACTION:RSVP:"):action_end]
                    parts = action_str.split(":", 2)
                    event_id = int(parts[0])
                    name = parts[1] if len(parts) > 1 else "Guest"
                    phone = parts[2] if len(parts) > 2 else ""

                    success, msg = save_rsvp(event_id, name, phone)
                    rsvp_result = {"success": success, "message": msg}
                    reply_text = reply_text[:action_start].strip()
                except Exception as e:
                    rsvp_result = {"success": False, "message": str(e)}

            return jsonify({
                "reply": reply_text,
                "rsvp_result": rsvp_result
            })
        else:
            # API failed, use fallback
            print(f"API returned {response.status_code}, using fallback")
            fallback_reply = get_fallback_response(last_user_message, events)
            return jsonify({
                "reply": fallback_reply,
                "rsvp_result": None
            })
            
    except Exception as e:
        # Any error, use fallback
        print(f"Error with DeepSeek API: {str(e)}")
        fallback_reply = get_fallback_response(last_user_message, events)
        return jsonify({
            "reply": fallback_reply,
            "rsvp_result": None
        })


@chatbot_bp.route("/api/events", methods=["GET"])
def get_events():
    events = get_upcoming_events()
    return jsonify(events)


@chatbot_bp.route("/api/rsvps", methods=["GET"])
def get_rsvps():
    event_id = request.args.get("event_id")
    conn = get_db()
    c = conn.cursor()
    if event_id:
        c.execute("""
            SELECT r.*, e.title as event_title
            FROM rsvps r JOIN events e ON r.event_id = e.id
            WHERE r.event_id = ?
            ORDER BY r.created_at DESC
        """, (event_id,))
    else:
        c.execute("""
            SELECT r.*, e.title as event_title
            FROM rsvps r JOIN events e ON r.event_id = e.id
            ORDER BY r.created_at DESC
        """)
    rsvps = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(rsvps)