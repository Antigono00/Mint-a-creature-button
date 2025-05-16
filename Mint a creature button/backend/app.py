import requests
import os
import time
import hashlib
import hmac
import sqlite3
import json
import random
import base64
import uuid
import traceback

from flask import Flask, request, session, redirect, jsonify, send_from_directory
from config import BOT_TOKEN, SECRET_KEY, DATABASE_PATH

app = Flask(__name__, 
            static_folder='static',  # React build files go here
            static_url_path='')

app.secret_key = SECRET_KEY

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Flag to track if we need to add the provisional_mint column
NEEDS_SCHEMA_UPDATE = False
# Flag to track if we need to add the room column
NEEDS_ROOM_COLUMN = False
# Flag to track if we need to add the seen_room_unlock column
NEEDS_SEEN_ROOM_COLUMN = False
# Flag to track if we need to ensure eggs resource exists for everyone
NEEDS_EGGS_RESOURCE = False
# Flag to track if we need to add the pets table
NEEDS_PETS_TABLE = False
# Flag to track if we need to add the radix_account_address column
NEEDS_RADIX_ADDRESS_COLUMN = False

# Constants for Evolving Creatures integration
EVOLVING_CREATURES_PACKAGE = "package_rdx1p5u8kkr8z77ujmhyzyx36x677jnjkvfwjphu2mxyc0984eqckgmclq"
EVOLVING_CREATURES_COMPONENT = "component_rdx1cr5q55fea4v2yrn5gy3n9uag9ejw3gt2h5pg9tf8rn4egw9lnchx5d"
CREATURE_NFT_RESOURCE = "resource_rdx1ntq7xkr0345fz8hkkappg2xsnepuj94a9wnu287km5tswu3323sjnl"
TOOL_NFT_RESOURCE = "resource_rdx1ntg0wsnuxq05z75f2jy7k20w72tgkt4crmdzcpyfvvgte3uvr9d5f0"
SPELL_NFT_RESOURCE = "resource_rdx1nfjm7ecgxk4m54pyy3mc75wgshh9usmyruy5rx7gkt3w2megc9s8jf"

# Token resource addresses for Evolving Creatures
TOKEN_ADDRESSES = {
    "XRD": "resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd",
    "CVX": "resource_rdx1th04p2c55884yytgj0e8nq79ze9wjnvu4rpg9d7nh3t698cxdt0cr9",
    "REDDICKS": "resource_rdx1t42hpqvsk4t42l6aw09hwphd2axvetp6gvas9ztue0p30f4hzdwxrp",
    "HUG": "resource_rdx1t5kmyj54jt85malva7fxdrnpvgfgs623yt7ywdaval25vrdlmnwe97",
    "EARLY": "resource_rdx1t5xv44c0u99z096q00mv74emwmxwjw26m98lwlzq6ddlpe9f5cuc7s",
    "FLOOP": "resource_rdx1t5pyvlaas0ljxy0wytm5gvyamyv896m69njqdmm2stukr3xexc2up9",
    "DELIVER": "resource_rdx1t466mhd2l2jmmzxr8cg3mkwjqhs7zmjgtder2utnh0ue5msxrhyk3t",
    "ILIS": "resource_rdx1t4r86qqjtzl8620ahvsxuxaf366s6rf6cpy24psdkmrlkdqvzn47c2",
    "OCI": "resource_rdx1t52pvtk5wfhltchwh3rkzls2x0r98fw9cjhpyrf3vsykhkuwrf7jg8",
    "WOWO": "resource_rdx1t4kc5ljyrwlxvg54s6gnctt7nwwgx89h9r2gvrpm369s23yhzyyzlx",
    "MOX": "resource_rdx1thmjcqjnlfm56v7k5g2szfrc44jn22x8tjh7xyczjpswmsnasjl5l9",
    "DAN": "resource_rdx1tk4y4ct50fzgyjygm7j3y6r3cw5rgsatyfnwdz64yp5t388v0atw8w",
    "FOMO": "resource_rdx1t5l954908vmg465pkj7j37z0fn4j33cdjt2g6czavjde406y4uxdy9",
    "DGC": "resource_rdx1t4qfgjm35dkwdrpzl3d8pc053uw9v4pj5wfek0ffuzsp73evye6wu6",
    "HIT": "resource_rdx1t4v2jke9xkcrqra9sf3lzgpxwdr590npkt03vufty4pwuu205q03az",
    "DELAY": "resource_rdx1t4dsaa07eaytq0asfe774maqzhrakfjkpxyng2ud4j6y2tdm5l7a76",
    "EDGE": "resource_rdx1t5vjqccrdtvxruu0p2hwqpts326kpz674grrzulcquly5ue0sg7wxk",
    "CASSIE": "resource_rdx1tk7g72c0uv2g83g3dqtkg6jyjwkre6qnusgjhrtz0cj9u54djgnk3c",
    "RBX": "resource_rdx1t5lenm5rr0p7urmcfjpzq5syt7cpges3wv3hzefckqe49ga6wutrhf"
}

# Species data for Evolving Creatures
SPECIES_DATA = {
    # Common Creatures (50% chance)
    1: {
        "name": "Bullx",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Common",
        "preferred_token": "RBX",
        "evolution_prices": [50, 100, 200],
        "stat_price": 100,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/bullx"
    },
    2: {
        "name": "Cudoge",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Common",
        "preferred_token": "DGC",
        "evolution_prices": [100000, 200000, 300000],
        "stat_price": 200000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/cudoge"
    },
    3: {
        "name": "Cvxling",
        "specialty_stats": ["speed", "energy"],
        "rarity": "Common",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/cvxling"
    },
    4: {
        "name": "Dan",
        "specialty_stats": ["stamina", "magic"],
        "rarity": "Common",
        "preferred_token": "DAN",
        "evolution_prices": [500000, 1000000, 2000000],
        "stat_price": 1000000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/dan"
    },
    5: {
        "name": "Delayer",
        "specialty_stats": ["magic"],
        "rarity": "Common",
        "preferred_token": "DELAY",
        "evolution_prices": [20000, 40000, 100000],
        "stat_price": 40000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/delayer"
    },
    6: {
        "name": "Delivera",
        "specialty_stats": ["stamina", "strength"],
        "rarity": "Common",
        "preferred_token": "DELIVER",
        "evolution_prices": [1000, 2000, 4000],
        "stat_price": 2000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/delivera"
    },
    7: {
        "name": "Flooper",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Common",
        "preferred_token": "FLOOP",
        "evolution_prices": [0.001, 0.002, 0.003],
        "stat_price": 0.002,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/flooper"
    },
    8: {
        "name": "Hitter",
        "specialty_stats": ["strength", "magic"],
        "rarity": "Common",
        "preferred_token": "HIT",
        "evolution_prices": [20000000, 40000000, 100000000],
        "stat_price": 40000000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/hitter"
    },
    9: {
        "name": "Moxer",
        "specialty_stats": ["speed", "magic"],
        "rarity": "Common",
        "preferred_token": "MOX",
        "evolution_prices": [200, 400, 1000],
        "stat_price": 400,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/moxer"
    },
    10: {
        "name": "Ocipod",
        "specialty_stats": ["energy"],
        "rarity": "Common",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/ocipod"
    },
    # Rare Creatures (30% chance)
    11: {
        "name": "Wowori",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Rare",
        "preferred_token": "WOWO",
        "evolution_prices": [4000, 10000, 20000],
        "stat_price": 10000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/wowori"
    },
    12: {
        "name": "Earlybyte",
        "specialty_stats": ["speed", "energy"],
        "rarity": "Rare",
        "preferred_token": "EARLY",
        "evolution_prices": [1000, 2000, 4000],
        "stat_price": 2000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/earlybyte"
    },
    13: {
        "name": "Edge",
        "specialty_stats": ["strength", "energy"],
        "rarity": "Rare",
        "preferred_token": "EDGE",
        "evolution_prices": [20000000, 40000000, 100000000],
        "stat_price": 40000000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/edge"
    },
    14: {
        "name": "Fomotron",
        "specialty_stats": ["energy", "strength"],
        "rarity": "Rare",
        "preferred_token": "FOMO",
        "evolution_prices": [200, 500, 1000],
        "stat_price": 500,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/fomotron"
    },
    15: {
        "name": "Hodlphant",
        "specialty_stats": ["strength"],
        "rarity": "Rare",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/hodlphant"
    },
    16: {
        "name": "Minermole",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Rare",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/minermole"
    },
    17: {
        "name": "Ocitrup",
        "specialty_stats": ["speed", "strength"],
        "rarity": "Rare",
        "preferred_token": "OCI",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/ocitrup"
    },
    # Epic Creatures (15% chance)
    18: {
        "name": "Etherion",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Epic",
        "preferred_token": "XRD",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/etherion"
    },
    19: {
        "name": "Hugbloom",
        "specialty_stats": ["stamina"],
        "rarity": "Epic",
        "preferred_token": "HUG",
        "evolution_prices": [100000, 300000, 500000],
        "stat_price": 300000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/hugbloom"
    },
    20: {
        "name": "Ilispect",
        "specialty_stats": ["stamina", "magic"],
        "rarity": "Epic",
        "preferred_token": "ILIS",
        "evolution_prices": [200, 400, 1000],
        "stat_price": 400,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/ilispect"
    },
    21: {
        "name": "Reddix",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Epic",
        "preferred_token": "REDDICKS",
        "evolution_prices": [300, 500, 1000],
        "stat_price": 500,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/reddix"
    },
    22: {
        "name": "Satoshium",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Epic",
        "preferred_token": "XRD",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/satoshium"
    },
    # Legendary Creatures (5% chance)
    23: {
        "name": "Cassie",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Legendary",
        "preferred_token": "CASSIE",
        "evolution_prices": [0.004, 0.01, 0.02],
        "stat_price": 0.01,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/cassie"
    },
    24: {
        "name": "Corvax",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Legendary",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/corvax"
    },
    25: {
        "name": "Xerdian",
        "specialty_stats": ["stamina", "energy"],
        "rarity": "Legendary",
        "preferred_token": "XRD",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/xerdian"
    }
}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def check_and_update_schema():
    """Check if the database schema needs updating and update if necessary."""
    global NEEDS_SCHEMA_UPDATE
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the provisional_mint column exists
        cursor.execute("PRAGMA table_info(user_machines)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'provisional_mint' not in columns:
            print("Adding provisional_mint column to user_machines table")
            try:
                cursor.execute("ALTER TABLE user_machines ADD COLUMN provisional_mint INTEGER DEFAULT 0")
                conn.commit()
                print("Column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
                NEEDS_SCHEMA_UPDATE = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking schema: {e}")
        NEEDS_SCHEMA_UPDATE = True

def check_and_update_room_column():
    """Check if the room column exists in user_machines and add if necessary."""
    global NEEDS_ROOM_COLUMN
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the room column exists
        cursor.execute("PRAGMA table_info(user_machines)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'room' not in columns:
            print("Adding room column to user_machines table")
            try:
                cursor.execute("ALTER TABLE user_machines ADD COLUMN room INTEGER DEFAULT 1")
                conn.commit()
                print("Room column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding room column: {e}")
                NEEDS_ROOM_COLUMN = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking room column: {e}")
        NEEDS_ROOM_COLUMN = True

def check_and_update_users_schema():
    """Check if the users table has a radix_account_address column and add it if necessary."""
    global NEEDS_RADIX_ADDRESS_COLUMN
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the radix_account_address column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'radix_account_address' not in columns:
            print("Adding radix_account_address column to users table")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN radix_account_address TEXT")
                conn.commit()
                print("radix_account_address column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding radix_account_address column: {e}")
                NEEDS_RADIX_ADDRESS_COLUMN = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking users schema: {e}")
        NEEDS_RADIX_ADDRESS_COLUMN = True

def check_and_update_seen_room_column():
    """Check if the seen_room_unlock column exists in users and add if necessary."""
    global NEEDS_SEEN_ROOM_COLUMN
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the seen_room_unlock column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'seen_room_unlock' not in columns:
            print("Adding seen_room_unlock column to users table")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN seen_room_unlock INTEGER DEFAULT 0")
                conn.commit()
                print("seen_room_unlock column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding seen_room_unlock column: {e}")
                NEEDS_SEEN_ROOM_COLUMN = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking seen_room_unlock column: {e}")
        NEEDS_SEEN_ROOM_COLUMN = True

def check_and_update_pets_table():
    """Check if the pets table exists and create if necessary."""
    global NEEDS_PETS_TABLE
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the pets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pets'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("Creating pets table")
            try:
                cursor.execute("""
                    CREATE TABLE pets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        x INTEGER NOT NULL,
                        y INTEGER NOT NULL,
                        room INTEGER DEFAULT 1,
                        type TEXT DEFAULT 'cat',
                        parent_machine INTEGER DEFAULT NULL
                    )
                """)
                conn.commit()
                print("Pets table created successfully")
            except sqlite3.Error as e:
                print(f"Error creating pets table: {e}")
                NEEDS_PETS_TABLE = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking pets table: {e}")
        NEEDS_PETS_TABLE = True

def ensure_eggs_resource_exists():
    """Ensure the eggs resource exists for all users."""
    global NEEDS_EGGS_RESOURCE
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all user IDs
        cursor.execute("SELECT user_id FROM users")
        user_ids = [row['user_id'] for row in cursor.fetchall()]
        
        # Check and create eggs resource for each user
        for user_id in user_ids:
            cursor.execute(
                "SELECT COUNT(*) FROM resources WHERE user_id=? AND resource_name='eggs'", 
                (user_id,)
            )
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"Adding eggs resource for user {user_id}")
                cursor.execute(
                    "INSERT INTO resources (user_id, resource_name, amount) VALUES (?, 'eggs', 0)",
                    (user_id,)
                )
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Eggs resource check completed")
    except Exception as e:
        print(f"Error ensuring eggs resource: {e}")
        NEEDS_EGGS_RESOURCE = True

# Run schema checks on startup
check_and_update_schema()
check_and_update_room_column()
check_and_update_seen_room_column()
ensure_eggs_resource_exists()
check_and_update_pets_table()
check_and_update_users_schema()

def fetch_scvx_balance(account_address):
    """Fetch sCVX balance for a Radix account using the Gateway API."""
    if not account_address:
        print("No account address provided")
        return 0
        
    try:
        # sCVX resource address
        scvx_resource = 'resource_rdx1t5q4aa74uxcgzehk0u3hjy6kng9rqyr4uvktnud8ehdqaaez50n693'
        
        # Use the Gateway API
        url = "https://mainnet.radixdlt.com/state/entity/page/fungibles/"
        print(f"Fetching sCVX for {account_address} using Gateway API")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "limit_per_page": 100  # Get a reasonable number of tokens
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        print(f"Making Gateway API request with payload: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        print(f"Gateway API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Print debugging info
        print(f"Gateway API total_count: {data.get('total_count', 0)}")
        
        # Look for the sCVX resource in the items
        items = data.get('items', [])
        print(f"Found {len(items)} resources in the account")
        
        # Dump all resources for debugging
        print("All resources in account:")
        for i, item in enumerate(items):
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            print(f"Resource {i}: {resource_addr} = {amount}")
            
            # Check if this is the sCVX resource
            if resource_addr == scvx_resource:
                amount_value = float(amount)
                print(f"FOUND sCVX RESOURCE: {amount_value}")
                return amount_value
        
        # If we get here, we didn't find the resource - look for partial matches
        print("Trying partial resource address matching...")
        for item in items:
            resource_addr = item.get('resource_address', '')
            if scvx_resource[-8:] in resource_addr:  # Match on last few chars
                amount = float(item.get('amount', '0'))
                print(f"Found potential sCVX match with amount: {amount}")
                return amount
                
        return 0
    except Exception as e:
        print(f"Error fetching sCVX with Gateway API: {e}")
        traceback.print_exc()
        return 0

def fetch_xrd_balance(account_address):
    """Fetch XRD balance for a Radix account using the Gateway API with improved reliability."""
    if not account_address:
        print("No account address provided")
        return 0
        
    try:
        # XRD resource address - This is the canonical XRD address
        xrd_resource = 'resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd'
        xrd_short_identifier = 'radxrd' # A unique identifier for XRD that's part of the address
        
        # Use the Gateway API
        url = "https://mainnet.radixdlt.com/state/entity/page/fungibles/"
        print(f"Fetching XRD for {account_address} using Gateway API")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "limit_per_page": 100  # Get a reasonable number of tokens
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        print(f"Making Gateway API request with payload: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        print(f"Gateway API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            # Try a second time before giving up
            print("Retrying XRD balance check...")
            time.sleep(2)  # Brief delay before retry
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Retry failed with status: {response.status_code}")
                return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Print debugging info
        print(f"Gateway API total_count: {data.get('total_count', 0)}")
        
        # Look for the XRD resource in the items
        items = data.get('items', [])
        print(f"Found {len(items)} resources in the account")
        
        # Print the first few resources to help diagnose issues
        for i, item in enumerate(items[:5]):
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            print(f"Resource {i}: {resource_addr} = {amount}")
        
        # First try exact match
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this is the XRD resource with exact match
            if resource_addr.lower() == xrd_resource.lower():
                amount_value = float(amount)
                print(f"FOUND XRD RESOURCE (exact match): {amount_value}")
                return amount_value
        
        # If exact match fails, try a more flexible approach with the unique identifier
        print("No exact match found for XRD, trying identifier match...")
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this resource address contains the XRD identifier
            if xrd_short_identifier in resource_addr.lower():
                amount_value = float(amount)
                print(f"FOUND XRD RESOURCE (identifier match): {amount_value}")
                return amount_value
        
        # Final fallback: check if there are additional pages of results
        if 'next_cursor' in data and data.get('total_count', 0) > len(items):
            print("Additional pages of tokens exist, but XRD not found in first page")
            # In a full implementation, we would handle pagination here
        
        # If we get here, we didn't find XRD
        print("XRD not found in account fungible tokens")
        return 0
    except Exception as e:
        print(f"Error fetching XRD with Gateway API: {e}")
        traceback.print_exc()
        # Try an alternative approach or display an error rather than silent fail
        return 0

def fetch_token_balance(account_address, token_symbol):
    """
    Fetch balance of a specific token for a Radix account.
    Returns: float balance or 0 if not found
    """
    if not account_address or not token_symbol:
        print(f"Missing account address or token symbol: {account_address}, {token_symbol}")
        return 0
        
    try:
        # Get the resource address for the token
        token_resource = TOKEN_ADDRESSES.get(token_symbol)
        if not token_resource:
            print(f"Unknown token symbol: {token_symbol}")
            return 0
        
        # Use the Gateway API
        url = "https://mainnet.radixdlt.com/state/entity/page/fungibles/"
        print(f"Fetching {token_symbol} for {account_address} using Gateway API")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "limit_per_page": 100  # Get a reasonable number of tokens
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Look for the token resource in the items
        items = data.get('items', [])
        
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this is the requested token
            if resource_addr == token_resource:
                amount_value = float(amount)
                print(f"FOUND {token_symbol} RESOURCE: {amount_value}")
                return amount_value
        
        # If we get here, we didn't find the token
        return 0
    except Exception as e:
        print(f"Error fetching {token_symbol} with Gateway API: {e}")
        traceback.print_exc()
        return 0

def fetch_user_nfts(account_address, resource_address=CREATURE_NFT_RESOURCE):
    """
    Fetch all NFTs of a specific resource type for a user's account with proper 
    ledger state consistency and pagination handling.
    
    Returns: list of non-fungible IDs or empty list if none found
    """
    if not account_address:
        print("No account address provided")
        return []
        
    try:
        # Use consistent Gateway API URL
        gateway_url = "https://mainnet.radixdlt.com"
        
        # First, get the current ledger state to maintain consistency across requests
        status_url = f"{gateway_url}/status/current"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        status_response = requests.post(
            status_url,
            headers=headers,
            json={},
            timeout=15
        )
        
        if status_response.status_code != 200:
            print(f"Failed to get current ledger state: {status_response.text[:200]}")
            return []
            
        # Extract the ledger state for consistency
        ledger_state = status_response.json().get("ledger_state")
        print(f"Using ledger state: {ledger_state}")
        
        # Use the entity/page/non-fungible-vaults endpoint with proper parameters
        url = f"{gateway_url}/state/entity/page/non-fungible-vaults/"
        print(f"Fetching NFTs for {account_address} of resource {resource_address}")
        
        all_nft_ids = []
        next_cursor = None
        
        # Implement proper pagination loop
        while True:
            # Prepare request payload with correct opt-ins and ledger state
            payload = {
                "address": account_address,
                "resource_address": resource_address,
                "at_ledger_state": ledger_state,  # Use consistent ledger state
                "opt_ins": {
                    "non_fungible_include_nfids": True,
                    "ancestor_identities": True
                },
                "limit_per_page": 100
            }
            
            # Add cursor for pagination if we have one
            if next_cursor:
                payload["cursor"] = next_cursor
            
            print(f"Making API request with payload: {json.dumps(payload)}")
            
            # Implement retry logic with exponential backoff for rate limiting
            max_retries = 3
            retry_delay = 1
            
            for retry in range(max_retries):
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=15)
                    
                    # Check if we hit rate limiting
                    if response.status_code == 429:
                        if retry < max_retries - 1:
                            sleep_time = retry_delay * (2 ** retry)
                            print(f"Rate limited, retrying in {sleep_time} seconds...")
                            time.sleep(sleep_time)
                            continue
                    
                    break  # Success or non-retry error
                except requests.exceptions.RequestException as e:
                    if retry < max_retries - 1:
                        sleep_time = retry_delay * (2 ** retry)
                        print(f"Request failed, retrying in {sleep_time} seconds: {e}")
                        time.sleep(sleep_time)
                    else:
                        raise
            
            if response.status_code != 200:
                print(f"Gateway API error: Status {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return all_nft_ids  # Return what we have so far
            
            # Print raw response for debugging
            print(f"Raw response (first 300 chars): {response.text[:300]}")
            
            # Parse the JSON response
            data = response.json()
            
            # Get the vault items
            items = data.get('items', [])
            
            if not items:
                print("No items returned from API")
                break
                
            # Extract all NFT IDs from all vaults
            # Using the updated approach for new Gateway API format
            for item in items:
                # New location: IDs live directly under 'items'
                nfid_list = item.get("items", [])

                # Fallback for very old Gateway versions
                if not nfid_list and "vault" in item:
                    nfid_list = item["vault"].get("non_fungible_ids", [])

                if nfid_list:
                    all_nft_ids.extend(nfid_list)
                    
                # Debug output
                if nfid_list:
                    print(f"Found {len(nfid_list)} NFIDs in this item")
                else:
                    print("No NFIDs found in this item. Keys:", list(item.keys()))
            
            # Check if there are more pages with proper cursor handling
            next_cursor = data.get('next_cursor')
            if not next_cursor:
                break
                
            print(f"Found {len(all_nft_ids)} NFTs so far, fetching next page with cursor")
        
        print(f"Total NFTs found: {len(all_nft_ids)}")
        return all_nft_ids
        
    except Exception as e:
        print(f"Error fetching NFTs with Gateway API: {e}")
        traceback.print_exc()
        return []

def fetch_user_nfts_simplified(account_address, resource_address=CREATURE_NFT_RESOURCE):
    """
    Simplified version that uses the global non-fungibles endpoint to fetch all NFTs
    without worrying about vault structure.
    
    Returns: list of non-fungible IDs or empty list if none found
    """
    if not account_address:
        print("No account address provided")
        return []
        
    try:
        # Use consistent Gateway API URL
        gateway_url = "https://mainnet.radixdlt.com"
        
        # First, get the current ledger state to maintain consistency across requests
        status_url = f"{gateway_url}/status/current"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        status_response = requests.post(
            status_url,
            headers=headers,
            json={},
            timeout=15
        )
        
        if status_response.status_code != 200:
            print(f"Failed to get current ledger state: {status_response.text[:200]}")
            return []
            
        # Extract the ledger state for consistency
        ledger_state = status_response.json().get("ledger_state")
        print(f"Using ledger state: {ledger_state}")
        
        # Use the entity/page/non-fungibles endpoint with global aggregation
        url = f"{gateway_url}/state/entity/page/non-fungibles/"
        print(f"Fetching NFTs for {account_address} of resource {resource_address}")
        
        all_nft_ids = []
        next_cursor = None
        
        # Implement proper pagination loop
        while True:
            # Prepare request payload with correct opt-ins and ledger state
            payload = {
                "address": account_address,
                "resource_address": resource_address,
                "at_ledger_state": ledger_state,
                "aggregation_level": "Global",  # Global aggregation to get all NFTs regardless of vault
                "opt_ins": {
                    "non_fungible_include_nfids": True
                },
                "limit_per_page": 100
            }
            
            # Add cursor for pagination if we have one
            if next_cursor:
                payload["cursor"] = next_cursor
            
            print(f"Making API request with payload: {json.dumps(payload)}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"Gateway API error: Status {response.status_code}")
                print(f"Response: {response.text[:300]}...")
                return all_nft_ids  # Return what we have so far
            
            # Print raw response for debugging
            print(f"Raw response (first 300 chars): {response.text[:300]}")
            
            # Parse the JSON response
            data = response.json()
            
            # Get the items
            items = data.get('items', [])
            
            if not items:
                print("No items returned from API")
                break
                
            # Extract all NFT IDs directly from the items
            for item in items:
                nfid_list = item.get("non_fungible_ids", [])
                if nfid_list:
                    all_nft_ids.extend(nfid_list)
                    print(f"Found {len(nfid_list)} NFIDs in this item")
            
            # Check if there are more pages with proper cursor handling
            next_cursor = data.get('next_cursor')
            if not next_cursor:
                break
                
            print(f"Found {len(all_nft_ids)} NFTs so far, fetching next page with cursor")
        
        print(f"Total NFTs found: {len(all_nft_ids)}")
        return all_nft_ids
        
    except Exception as e:
        print(f"Error fetching NFTs with Gateway API: {e}")
        traceback.print_exc()
        return []

def fetch_nft_data(resource_address, non_fungible_ids):
    """
    Fetch data for specific non-fungible tokens with proper 
    error handling and batch processing.
    
    Returns: dict of NFT ID to data or empty dict if none found
    """
    if not non_fungible_ids:
        return {}
        
    try:
        gateway_url = "https://mainnet.radixdlt.com"
        url = f"{gateway_url}/state/non-fungible/data"
        
        print(f"Fetching data for {len(non_fungible_ids)} NFTs of resource {resource_address}")
        
        # For consistency, first get current ledger state
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        status_response = requests.post(
            f"{gateway_url}/status/current",
            headers=headers,
            json={},
            timeout=15
        )
        
        if status_response.status_code != 200:
            print(f"Failed to get current ledger state: {status_response.text[:200]}")
            return {}
            
        ledger_state = status_response.json().get("ledger_state")
        print(f"Using ledger state for NFT data: {ledger_state}")
        
        # Need to batch requests if we have more than 100 NFTs (API limit)
        all_nft_data = {}
        batch_size = 100  # API limits to around 100 IDs per request
        
        for i in range(0, len(non_fungible_ids), batch_size):
            batch = non_fungible_ids[i:min(i+batch_size, len(non_fungible_ids))]
            print(f"Processing batch {i//batch_size + 1} with {len(batch)} NFTs")
            
            # Prepare request payload with ledger state for consistency
            payload = {
                "resource_address": resource_address,
                "non_fungible_ids": batch,
                "at_ledger_state": ledger_state
            }
            
            # Implement retry with exponential backoff
            max_retries = 3
            retry_delay = 1
            
            for retry in range(max_retries):
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=20)
                    
                    if response.status_code == 429:  # Rate limited
                        if retry < max_retries - 1:
                            sleep_time = retry_delay * (2 ** retry)
                            print(f"Rate limited, retrying in {sleep_time} seconds...")
                            time.sleep(sleep_time)
                            continue
                    
                    break  # Success or non-retry error
                except requests.exceptions.RequestException as e:
                    if retry < max_retries - 1:
                        sleep_time = retry_delay * (2 ** retry)
                        print(f"Request failed, retrying in {sleep_time} seconds: {e}")
                        time.sleep(sleep_time)
                    else:
                        raise
            
            if response.status_code != 200:
                print(f"Gateway API error: Status {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                continue  # Try next batch instead of failing completely
            
            # Parse the JSON response
            data = response.json()
            
            # The response format changed slightly in different Gateway API versions
            # Handle both older and newer formats
            if 'non_fungible_ids' in data:
                # Newer format - directly contains the data
                for nft_id, nft_data in data['non_fungible_ids'].items():
                    all_nft_data[nft_id] = nft_data.get('data', {})
            else:
                # Older format or different structure
                items = data.get('items', [])
                for item in items:
                    nft_id = item.get('non_fungible_id')
                    if nft_id:
                        all_nft_data[nft_id] = item.get('data', {})
            
            print(f"Processed {len(batch)} NFTs in batch {i//batch_size + 1}")
        
        print(f"Total NFTs data retrieved: {len(all_nft_data)}")
        return all_nft_data
        
    except Exception as e:
        print(f"Error fetching NFT data with Gateway API: {e}")
        traceback.print_exc()
        return {}

def process_creature_data(nft_id, nft_data):
    """
    Process raw creature NFT data into the expected format for the frontend with
    better error handling and data validation.
    """
    try:
        # Default values in case some fields are missing
        processed_data = {
            "id": nft_id,
            "species_id": 1,
            "species_name": "Unknown",
            "form": 0,
            "key_image_url": "",
            "image_url": "",
            "rarity": "Common",
            "stats": {
                "energy": 5,
                "strength": 5,
                "magic": 5,
                "stamina": 5,
                "speed": 5
            },
            "evolution_progress": {
                "stat_upgrades_completed": 0,
                "total_points_allocated": 0,
                "energy_allocated": 0,
                "strength_allocated": 0,
                "magic_allocated": 0,
                "stamina_allocated": 0,
                "speed_allocated": 0
            },
            "final_form_upgrades": 0,
            "version": 1,
            "combination_level": 0,
            "bonus_stats": {},
            "display_form": "Egg",
            "display_stats": "",
            "display_combination": "",
            "preferred_token": "XRD"
        }
        
        # Update with actual data if available
        if not nft_data:
            print(f"No data for NFT {nft_id}")
            return processed_data
            
        # Handle different possible data structures
        if isinstance(nft_data, str):
            try:
                # Sometimes the data may be a JSON string
                nft_data = json.loads(nft_data)
            except json.JSONDecodeError:
                print(f"Could not parse NFT data as JSON: {nft_data[:100]}...")
                # Try to extract from programmatic_json if it's there
                if "programmatic_json" in nft_data:
                    try:
                        nft_data = json.loads(nft_data["programmatic_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        # Try to handle various structures in the Radix Gateway API response
        if "programmatic_json" in nft_data:
            try:
                programmatic_data = json.loads(nft_data["programmatic_json"])
                if isinstance(programmatic_data, dict):
                    nft_data = programmatic_data
            except (json.JSONDecodeError, TypeError):
                pass
                
        # Debug output to find where the data is
        print(f"NFT Data structure for {nft_id}: {type(nft_data)}")
        if isinstance(nft_data, dict):
            print(f"Keys in nft_data: {list(nft_data.keys())}")
            
        # Species information
        species_id = 1  # Default
        if "species_id" in nft_data:
            species_id = int(nft_data["species_id"])
            processed_data["species_id"] = species_id
        
        # Get species information from SPECIES_DATA
        species_info = SPECIES_DATA.get(species_id, {"name": "Unknown", "preferred_token": "XRD", "rarity": "Common"})
        processed_data["species_name"] = species_info.get("name", "Unknown")
        processed_data["rarity"] = species_info.get("rarity", "Common")
        processed_data["preferred_token"] = species_info.get("preferred_token", "XRD")
        
        # Add specialty stats if available
        if "specialty_stats" in species_info:
            processed_data["specialty_stats"] = species_info["specialty_stats"]
        
        # Form and image URL
        if "form" in nft_data:
            form = int(nft_data["form"])
            processed_data["form"] = form
        else:
            form = 0  # Default to egg form
        
        # Determine form name for display
        if form == 0:
            processed_data["display_form"] = "Egg"
        elif form == 1:
            processed_data["display_form"] = "Form 1"
        elif form == 2:
            processed_data["display_form"] = "Form 2"
        elif form == 3:
            processed_data["display_form"] = "Form 3 (Final)"
        
        # Generate image URLs based on form
        base_url = species_info.get("base_url", "https://cvxlab.net/assets/evolving_creatures/bullx")
        if form == 0:
            image_url = f"{base_url}_egg.png"
        elif form == 1:
            image_url = f"{base_url}_form1.png"
        elif form == 2:
            image_url = f"{base_url}_form2.png"
        elif form == 3:
            image_url = f"{base_url}_form3.png"
        else:
            image_url = f"{base_url}_egg.png"
            
        processed_data["key_image_url"] = image_url
        processed_data["image_url"] = image_url
        
        # Stats with proper type conversion
        if "stats" in nft_data:
            stats = nft_data["stats"]
            processed_data["stats"] = {
                "energy": int(stats.get("energy", 5)),
                "strength": int(stats.get("strength", 5)),
                "magic": int(stats.get("magic", 5)),
                "stamina": int(stats.get("stamina", 5)),
                "speed": int(stats.get("speed", 5))
            }
        
        # Evolution progress
        if "evolution_progress" in nft_data:
            evolution_progress = nft_data["evolution_progress"]
            processed_data["evolution_progress"] = {
                "stat_upgrades_completed": int(evolution_progress.get("stat_upgrades_completed", 0)),
                "total_points_allocated": int(evolution_progress.get("total_points_allocated", 0)),
                "energy_allocated": int(evolution_progress.get("energy_allocated", 0)),
                "strength_allocated": int(evolution_progress.get("strength_allocated", 0)),
                "magic_allocated": int(evolution_progress.get("magic_allocated", 0)),
                "stamina_allocated": int(evolution_progress.get("stamina_allocated", 0)),
                "speed_allocated": int(evolution_progress.get("speed_allocated", 0))
            }
        elif form == 3:
            # Form 3 creatures don't have evolution progress
            processed_data["evolution_progress"] = None
        
        # Final form upgrades
        if "final_form_upgrades" in nft_data:
            processed_data["final_form_upgrades"] = int(nft_data["final_form_upgrades"])
        
        # Version
        if "version" in nft_data:
            processed_data["version"] = int(nft_data["version"])
        
        # Combination level and bonus stats
        if "combination_level" in nft_data:
            combination_level = int(nft_data["combination_level"])
            processed_data["combination_level"] = combination_level
            
            if combination_level > 0:
                processed_data["display_combination"] = f"Fusion Level {combination_level}"
                
            # Bonus stats if available
            if "bonus_stats" in nft_data and nft_data["bonus_stats"]:
                bonus_stats = nft_data["bonus_stats"]
                processed_data["bonus_stats"] = {k: int(v) for k, v in bonus_stats.items()}
        
        # Generate display stats string
        stats_str = ", ".join([f"{stat.capitalize()}: {value}" for stat, value in processed_data["stats"].items()])
        processed_data["display_stats"] = stats_str
        
        return processed_data
        
    except Exception as e:
        print(f"Error processing creature data for NFT {nft_id}: {e}")
        traceback.print_exc()
        return {
            "id": nft_id,
            "species_name": "Error",
            "form": 0,
            "image_url": "https://cvxlab.net/assets/evolving_creatures/bullx_egg.png",
            "rarity": "Common",
            "error": str(e)
        }

def calculate_upgrade_cost(creature, energy=0, strength=0, magic=0, stamina=0, speed=0):
    """
    Calculate the cost for upgrading stats for a creature.
    Returns: dict with token and amount
    """
    try:
        # First try to use the provided creature data
        if creature:
            # Get species info
            species_id = creature.get("species_id", 1)
            species_info = SPECIES_DATA.get(species_id, {})
            
            # Get preferred token
            token_symbol = species_info.get("preferred_token", "XRD")
            
            # Get form
            form = creature.get("form", 0)
            
            # Default stat price if not specified
            stat_price = species_info.get("stat_price", 50)
            
            # For final form (form 3), cost is stat_price * total points
            if form == 3:
                total_points = energy + strength + magic + stamina + speed
                return {
                    "token": token_symbol,
                    "amount": stat_price * total_points
                }
            
            # For forms 0-2, cost depends on which upgrade it is
            evolution_progress = creature.get("evolution_progress", {})
            if not evolution_progress:
                return {
                    "token": token_symbol,
                    "amount": 0
                }
                
            upgrades_completed = evolution_progress.get("stat_upgrades_completed", 0)
            
            # Cost increases with each upgrade (10%, 20%, 30% of evolution price)
            evolution_prices = species_info.get("evolution_prices", [50, 100, 200])
            if form < len(evolution_prices):
                evolution_price = evolution_prices[form]
            else:
                evolution_price = evolution_prices[-1]
                
            # Calculate percentage based on upgrade number
            percentage = 0.1 * (upgrades_completed + 1)  # 0.1, 0.2, 0.3
            upgrade_cost = evolution_price * percentage
            
            return {
                "token": token_symbol,
                "amount": upgrade_cost
            }
        else:
            # If no creature data provided, we need to fetch it from the blockchain
            # This should be rare since we typically have the creature data already
            return {
                "token": "XRD",  # Default to XRD
                "amount": 100    # Default amount
            }
    except Exception as e:
        print(f"Error calculating upgrade cost: {e}")
        traceback.print_exc()
        return {
            "token": "XRD",
            "amount": 0
        }

def calculate_evolution_cost(creature):
    """
    Calculate the cost for evolving a creature to the next form.
    Returns: dict with token and amount
    """
    try:
        if not creature:
            return {
                "token": "XRD",
                "amount": 0,
                "can_evolve": False,
                "reason": "Invalid creature data"
            }
            
        # Get species info
        species_id = creature.get("species_id", 1)
        species_info = SPECIES_DATA.get(species_id, {})
        
        # Get preferred token
        token_symbol = species_info.get("preferred_token", "XRD")
        
        # Get form
        form = creature.get("form", 0)
        
        # Check if creature can evolve (must be form 0-2)
        if form >= 3:
            return {
                "token": token_symbol,
                "amount": 0,
                "can_evolve": False,
                "reason": "Already at max form"
            }
        
        # Check if creature has completed 3 stat upgrades
        evolution_progress = creature.get("evolution_progress", {})
        if not evolution_progress:
            return {
                "token": token_symbol,
                "amount": 0,
                "can_evolve": False,
                "reason": "No evolution progress data"
            }
                
        upgrades_completed = evolution_progress.get("stat_upgrades_completed", 0)
        if upgrades_completed < 3:
            return {
                "token": token_symbol,
                "amount": 0,
                "can_evolve": False,
                "reason": f"Need 3 stat upgrades, only has {upgrades_completed}"
            }
        
        # Get evolution price for current form
        evolution_prices = species_info.get("evolution_prices", [50, 100, 200])
        if form < len(evolution_prices):
            evolution_price = evolution_prices[form]
        else:
            evolution_price = evolution_prices[-1]
                
        # Calculate total already paid in upgrades
        # Typically 10% + 20% + 30% = 60% of full evolution price
        paid_percentage = 0.6  # 0.1 + 0.2 + 0.3
        remaining_cost = evolution_price * (1 - paid_percentage)
        
        return {
            "token": token_symbol,
            "amount": remaining_cost,
            "can_evolve": True
        }
    except Exception as e:
        print(f"Error calculating evolution cost: {e}")
        traceback.print_exc()
        return {
            "token": "XRD",
            "amount": 0,
            "can_evolve": False,
            "reason": f"Error: {str(e)}"
        }

def can_build_fomo_hit(cur, user_id):
    """Check if user has built and fully operational all other machine types."""
    print(f"Checking FOMO HIT prerequisites for user_id: {user_id}")
    try:
        # 1. Check if they've built all required machine types
        required_types = ['catLair', 'reactor', 'amplifier', 'incubator']
        for machine_type in required_types:
            cur.execute("""
                SELECT COUNT(*) as count FROM user_machines
                WHERE user_id=? AND machine_type=?
            """, (user_id, machine_type))
            row = cur.fetchone()
            count = row[0] if row else 0
            print(f"  Machine type {machine_type}: {count} found")
            if count == 0:
                print(f"  Missing required machine: {machine_type}")
                return False
        
        # 2. For cat lairs and reactors, check ALL are at max level (3)
        # First, get total count of each type
        for machine_type in ['catLair', 'reactor']:
            # Get total number of this machine type
            cur.execute("""
                SELECT COUNT(*) as total FROM user_machines
                WHERE user_id=? AND machine_type=?
            """, (user_id, machine_type))
            total_row = cur.fetchone()
            total = total_row[0] if total_row else 0
            
            # Get how many are at max level
            cur.execute("""
                SELECT COUNT(*) as max_count FROM user_machines 
                WHERE user_id=? AND machine_type=? AND level>=3
            """, (user_id, machine_type))
            max_row = cur.fetchone()
            max_count = max_row[0] if max_row else 0
            
            print(f"  {machine_type}: {max_count}/{total} at max level")
            
            # For now, as long as one machine is at max level for each type, that counts as success
            if max_count == 0:
                print(f"  No {machine_type} machines at max level")
                return False
        
        # 3. For amplifier, check it's at max level (5)
        cur.execute("""
            SELECT MAX(level) as max_level FROM user_machines
            WHERE user_id=? AND machine_type='amplifier'
        """, (user_id,))
        max_level_row = cur.fetchone()
        max_level = max_level_row[0] if max_level_row else 0
        print(f"  Amplifier max level: {max_level}/5")
        
        # For now, level 3 amplifier is ok as a prerequisite 
        if max_level < 3:
            print(f"  Amplifier not at required level")
            return False
        
        # 4. Check that incubator is operational (not offline)
        cur.execute("""
            SELECT is_offline FROM user_machines
            WHERE user_id=? AND machine_type='incubator'
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        is_offline = row[0] if row else 1
        print(f"  Incubator offline status: {is_offline}")
        
        # For testing, let's ignore the incubator online check
        # Remove this if-statement in production
        if is_offline == 1:
            print(f"  Incubator is offline but we'll allow FOMO HIT for testing")
            # return False  # Comment this out for easier testing
            
        print("✅ All FOMO HIT prerequisites met!")
        return True
    except Exception as e:
        print(f"Error in can_build_fomo_hit: {e}")
        import traceback
        traceback.print_exc()
        return False

def can_build_third_reactor(cur, user_id):
    """Check if user can build a third reactor (has incubator and fomoHit)."""
    try:
        # Check if incubator exists
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='incubator'
        """, (user_id,))
        has_incubator = cur.fetchone()[0] > 0
        
        # Check if fomoHit exists
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='fomoHit'
        """, (user_id,))
        has_fomo_hit = cur.fetchone()[0] > 0
        
        # Count current reactors
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='reactor'
        """, (user_id,))
        reactor_count = cur.fetchone()[0]
        
        # Can build third reactor if:
        # 1. Has both incubator and fomoHit
        # 2. Currently has 2 reactors (this would be the third)
        return has_incubator and has_fomo_hit and reactor_count == 2
    except Exception as e:
        print(f"Error in can_build_third_reactor: {e}")
        traceback.print_exc()
        return False

def create_nft_mint_manifest(account_address):
    """Create the Radix transaction manifest for NFT minting."""
    try:
        # Generate a random ID for the NFT
        nft_id = str(uuid.uuid4())[:8]
        
        # Simple manifest that calls a component to mint an NFT
        # The component address should be your actual minting component
        manifest = f"""
CALL_METHOD
    Address("component_rdx1cqpv4nfsgfk9c2r9ymnqyksfkjsg07mfc49m9qw3dpgzrmjmsuuquv")
    "mint_user_nft"
;
CALL_METHOD
    Address("{account_address}")
    "try_deposit_batch_or_abort"
    Expression("ENTIRE_WORKTOP")
    None
;
"""
        return manifest
    except Exception as e:
        print(f"Error creating NFT mint manifest: {e}")
        traceback.print_exc()
        return None

def create_evolving_creature_manifest(account_address):
    """Create the Radix transaction manifest for minting an evolving creature egg."""
    try:
        # XRD resource address
        xrd_resource = "resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd"
        # Component address for the Evolving Creatures package
        component_address = "component_rdx1cr5q55fea4v2yrn5gy3n9uag9ejw3gt2h5pg9tf8rn4egw9lnchx5d"
        
        # Create manifest to mint an egg
        manifest = f"""
CALL_METHOD
    Address("{account_address}")
    "withdraw"
    Address("{xrd_resource}")
    Decimal("250");
TAKE_FROM_WORKTOP
    Address("{xrd_resource}")
    Decimal("250")
    Bucket("payment");
CALL_METHOD
    Address("{component_address}")
    "mint_egg"
    Bucket("payment");
CALL_METHOD
    Address("{account_address}")
    "try_deposit_batch_or_abort"
    Expression("ENTIRE_WORKTOP")
    None;
"""
        return manifest

    except Exception as e:
        print(f"Error creating evolving creature mint manifest: {e}")
        traceback.print_exc()
        return None

def create_upgrade_stats_manifest(account_address, creature_id, energy=0, strength=0, magic=0, stamina=0, speed=0, token_resource=None, token_amount=0):
    """
    Create the Radix transaction manifest for upgrading stats of a creature.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_id: The ID of the creature NFT
    - energy, strength, magic, stamina, speed: The stat points to allocate
    - token_resource: The resource address of the payment token
    - token_amount: The amount of tokens to pay
    
    Returns: The transaction manifest as a string
    """
    try:
        # Use XRD as fallback if no token specified
        if not token_resource:
            token_resource = TOKEN_ADDRESSES["XRD"]
            
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("nft");
CALL_METHOD
    Address("{account_address}") 
    "withdraw" 
    Address("{token_resource}") 
    Decimal("{token_amount}");
TAKE_FROM_WORKTOP
    Address("{token_resource}")
    Decimal("{token_amount}")
    Bucket("payment");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "upgrade_stats"
    Bucket("nft")
    Bucket("payment")
    {energy}u8     # Energy increase
    {strength}u8   # Strength increase
    {magic}u8      # Magic increase
    {stamina}u8    # Stamina increase
    {speed}u8;     # Speed increase
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating upgrade stats manifest: {e}")
        traceback.print_exc()
        return None

def create_evolve_manifest(account_address, creature_id, token_resource=None, token_amount=0):
    """
    Create the Radix transaction manifest for evolving a creature to the next form.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_id: The ID of the creature NFT
    - token_resource: The resource address of the payment token
    - token_amount: The amount of tokens to pay
    
    Returns: The transaction manifest as a string
    """
    try:
        # Use XRD as fallback if no token specified
        if not token_resource:
            token_resource = TOKEN_ADDRESSES["XRD"]
            
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("nft");
CALL_METHOD
    Address("{account_address}") 
    "withdraw" 
    Address("{token_resource}") 
    Decimal("{token_amount}");
TAKE_FROM_WORKTOP
    Address("{token_resource}")
    Decimal("{token_amount}")
    Bucket("payment");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "evolve_to_next_form"
    Bucket("nft")
    Bucket("payment");
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating evolve manifest: {e}")
        traceback.print_exc()
        return None

def create_level_up_manifest(account_address, creature_id, energy=0, strength=0, magic=0, stamina=0, speed=0, token_resource=None, token_amount=0):
    """
    Create the Radix transaction manifest for leveling up stats of a form 3 creature.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_id: The ID of the creature NFT
    - energy, strength, magic, stamina, speed: The stat points to allocate
    - token_resource: The resource address of the payment token
    - token_amount: The amount of tokens to pay
    
    Returns: The transaction manifest as a string
    """
    try:
        # Use XRD as fallback if no token specified
        if not token_resource:
            token_resource = TOKEN_ADDRESSES["XRD"]
            
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("nft");
CALL_METHOD
    Address("{account_address}") 
    "withdraw" 
    Address("{token_resource}") 
    Decimal("{token_amount}");
TAKE_FROM_WORKTOP
    Address("{token_resource}")
    Decimal("{token_amount}")
    Bucket("payment");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "level_up_stats"
    Bucket("nft")
    Bucket("payment")
    {energy}u8     # Energy increase
    {strength}u8   # Strength increase
    {magic}u8      # Magic increase
    {stamina}u8    # Stamina increase
    {speed}u8;     # Speed increase
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating level up manifest: {e}")
        traceback.print_exc()
        return None

def create_combine_creatures_manifest(account_address, creature_a_id, creature_b_id):
    """
    Create the Radix transaction manifest for combining two creatures.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_a_id: The ID of the primary creature NFT
    - creature_b_id: The ID of the secondary creature NFT to be combined and burned
    
    Returns: The transaction manifest as a string
    """
    try:
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_a_id}"),
        NonFungibleLocalId("{creature_b_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("creature_a");
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("creature_b");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "combine_creatures"
    Bucket("creature_a")
    Bucket("creature_b");
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating combine creatures manifest: {e}")
        traceback.print_exc()
        return None

def create_buy_energy_manifest(account_address):
    """Create the Radix transaction manifest for buying energy with CVX."""
    try:
        cvx_resource        = "resource_rdx1th04p2c55884yytgj0e8nq79ze9wjnvu4rpg9d7nh3t698cxdt0cr9"
        destination_account = "account_rdx16ya2ncwya20j2w0k8d49us5ksvzepjhhh7cassx9jp9gz6hw69mhks"
        cvx_amount          = "200.0"

        manifest = f"""
CALL_METHOD
    Address("{account_address}")
    "withdraw"
    Address("{cvx_resource}")
    Decimal("{cvx_amount}")
;
CALL_METHOD
    Address("{destination_account}")
    "try_deposit_batch_or_abort"
    Expression("ENTIRE_WORKTOP")
    None
;
"""
        print(f"Generated manifest:\n{manifest}")
        return manifest

    except Exception as e:
        print(f"Error creating energy purchase manifest: {e}")
        traceback.print_exc()
        return None

def get_transaction_status(intent_hash):
    """Check the status of a transaction using the Gateway API."""
    try:
        url = "https://mainnet.radixdlt.com/transaction/status"
        payload = {"intent_hash": intent_hash}
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return {"status": "Unknown", "error": f"HTTP {response.status_code}"}
        
        data = response.json()
        return {
            "status": data.get("status", "Unknown"),
            "intent_status": data.get("intent_status", "Unknown"),
            "error_message": data.get("error_message", "")
        }
    except Exception as e:
        print(f"Error checking transaction status: {e}")
        traceback.print_exc()
        return {"status": "Error", "error": str(e)}

# Function to fetch NFT details from transaction
def get_minted_nfts_from_transaction(intent_hash):
    """
    Get minted NFTs from a transaction using the Gateway API.
    Returns: Tuple of (creature_nft, bonus_item) with complete data
    """
    try:
        # NFT resource addresses
        creature_resource = "resource_rdx1ntq7xkr0345fz8hkkappg2xsnepuj94a9wnu287km5tswu3323sjnl"
        tool_resource = "resource_rdx1ntg0wsnuxq05z75f2jy7k20w72tgkt4crmdzcpyfvvgte3uvr9d5f0"
        spell_resource = "resource_rdx1nfjm7ecgxk4m54pyy3mc75wgshh9usmyruy5rx7gkt3w2megc9s8jf"
        
        # Check if transaction is committed
        status_data = get_transaction_status(intent_hash)
        if status_data.get("status") != "CommittedSuccess":
            print(f"Transaction not completed yet: {status_data}")
            return None, None
        
        # Get transaction details
        url = "https://mainnet.radixdlt.com/transaction/committed-details"
        payload = {
            "intent_hash": intent_hash,
            "opt_ins": {
                "balance_changes": True,
                "non_fungible_changes": True
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return None, None
        
        data = response.json()
        
        # Extract NFT IDs from non-fungible changes
        creature_nft = None
        bonus_item = None
        non_fungible_changes = data.get("non_fungible_changes", [])
        
        creature_id = None
        bonus_item_id = None
        bonus_item_type = None
        
        # First, find the NFT IDs
        for change in non_fungible_changes:
            resource_address = change.get("resource_address")
            operation = change.get("operation")
            
            # Only look at deposit operations (NFTs being received)
            if operation != "DEPOSIT":
                continue
                
            if resource_address == creature_resource:
                # This is a creature NFT
                nft_ids = change.get("non_fungible_ids", [])
                if nft_ids:
                    creature_id = nft_ids[0]
            
            elif resource_address == tool_resource:
                # This is a tool NFT
                nft_ids = change.get("non_fungible_ids", [])
                if nft_ids:
                    bonus_item_id = nft_ids[0]
                    bonus_item_type = "tool"
                    
            elif resource_address == spell_resource:
                # This is a spell NFT
                nft_ids = change.get("non_fungible_ids", [])
                if nft_ids:
                    bonus_item_id = nft_ids[0]
                    bonus_item_type = "spell"
        
        # Now, fetch the actual NFT data for the creature
        if creature_id:
            creature_data = fetch_nft_data(creature_resource, [creature_id])
            if creature_data and creature_id in creature_data:
                raw_data = creature_data[creature_id]
                creature_nft = process_creature_data(creature_id, raw_data)
        
        # Fetch the bonus item data
        if bonus_item_id and bonus_item_type:
            resource_address = tool_resource if bonus_item_type == "tool" else spell_resource
            bonus_data = fetch_nft_data(resource_address, [bonus_item_id])
            
            if bonus_data and bonus_item_id in bonus_data:
                raw_bonus_data = bonus_data[bonus_item_id]
                
                # Process tool or spell data
                if bonus_item_type == "tool":
                    image_url = raw_bonus_data.get("key_image_url", "")
                    name = raw_bonus_data.get("tool_name", "Unknown Tool")
                    tool_type = raw_bonus_data.get("tool_type", "")
                    tool_effect = raw_bonus_data.get("tool_effect", "")
                    
                    bonus_item = {
                        "id": bonus_item_id,
                        "name": name,
                        "type": "tool",
                        "image_url": image_url,
                        "tool_type": tool_type,
                        "tool_effect": tool_effect
                    }
                else:  # spell
                    image_url = raw_bonus_data.get("key_image_url", "")
                    name = raw_bonus_data.get("spell_name", "Unknown Spell")
                    spell_type = raw_bonus_data.get("spell_type", "")
                    spell_effect = raw_bonus_data.get("spell_effect", "")
                    
                    bonus_item = {
                        "id": bonus_item_id,
                        "name": name,
                        "type": "spell",
                        "image_url": image_url,
                        "spell_type": spell_type,
                        "spell_effect": spell_effect
                    }
                
        # If we couldn't get the actual data, create fallback data
        if not creature_nft and creature_id:
            creature_nft = {
                "id": creature_id,
                "species_name": "Random Creature",
                "rarity": "Unknown",
                "image_url": "https://cvxlab.net/assets/evolving_creatures/bullx_egg.png"
            }
            
        if not bonus_item and bonus_item_id:
            bonus_item = {
                "id": bonus_item_id,
                "name": f"Mystery {bonus_item_type.capitalize() if bonus_item_type else 'Item'}",
                "type": bonus_item_type or "unknown",
                "image_url": "https://cvxlab.net/assets/tools/babylon_keystone.png"
            }
            
        return creature_nft, bonus_item
    
    except Exception as e:
        print(f"Error getting minted NFTs: {e}")
        traceback.print_exc()
        return None, None

def verify_telegram_login(query_dict, bot_token):
    try:
        their_hash = query_dict.pop("hash", None)
        if not their_hash:
            return False
        secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
        sorted_kv = sorted(query_dict.items(), key=lambda x: x[0])
        data_check_str = "\n".join([f"{k}={v}" for k, v in sorted_kv])
        calc_hash_bytes = hmac.new(secret_key, data_check_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return calc_hash_bytes == their_hash
    except Exception as e:
        print(f"Error in verify_telegram_login: {e}")
        traceback.print_exc()
        return False

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    try:
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"Error serving path {path}: {e}")
        traceback.print_exc()
        return "Server error", 500

@app.route("/callback")
def telegram_login_callback():
    print("=== Telegram Callback Called ===")
    try:
        args = request.args.to_dict()
        print(f"Args received: {args}")
        
        user_id = args.get("id")
        tg_hash = args.get("hash")
        auth_date = args.get("auth_date")
        
        if not user_id or not tg_hash or not auth_date:
            print("Missing login data!")
            return "<h3>Missing Telegram login data!</h3>", 400

        if not verify_telegram_login(args, BOT_TOKEN):
            print(f"Invalid hash! Data: {args}")
            return "<h3>Invalid hash - data might be forged!</h3>", 403

        print(f"Login successful for user {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            user_id_int = int(user_id)
        except ValueError:
            user_id_int = user_id

        cursor.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id_int,))
        row = cursor.fetchone()
        if row is None:
            first_name = args.get("first_name", "Unknown")
            print(f"Creating new user: {first_name}")
            cursor.execute(
                "INSERT INTO users (user_id, first_name, corvax_count, seen_room_unlock) VALUES (?, ?, 0, 0)",
                (user_id_int, first_name)
            )
            conn.commit()
            
            # Also create initial eggs resource for new user
            cursor.execute(
                "INSERT INTO resources (user_id, resource_name, amount) VALUES (?, 'eggs', 0)",
                (user_id_int,)
            )
            conn.commit()

        cursor.close()
        conn.close()

        session['telegram_id'] = str(user_id_int)
        print(f"Session set, redirecting to homepage")
        return redirect("https://cvxlab.net/")
    except Exception as e:
        print(f"Error in telegram_login_callback: {e}")
        traceback.print_exc()
        return "<h3>Server error</h3>", 500

@app.route("/api/whoami")
def whoami():
    try:
        print("=== WHOAMI CALLED ===")
        if 'telegram_id' not in session:
            print("User not logged in")
            return jsonify({"loggedIn": False}), 200

        user_id = session['telegram_id']
        print(f"User logged in with ID: {user_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT first_name FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return jsonify({"loggedIn": True, "firstName": row[0]})
        else:
            return jsonify({"loggedIn": True, "firstName": "Unknown"})
    except Exception as e:
        print(f"Error in whoami: {e}")
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500
import requests
import os
import time
import hashlib
import hmac
import sqlite3
import json
import random
import base64
import uuid
import traceback

from flask import Flask, request, session, redirect, jsonify, send_from_directory
from config import BOT_TOKEN, SECRET_KEY, DATABASE_PATH

app = Flask(__name__, 
            static_folder='static',  # React build files go here
            static_url_path='')

app.secret_key = SECRET_KEY

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Flag to track if we need to add the provisional_mint column
NEEDS_SCHEMA_UPDATE = False
# Flag to track if we need to add the room column
NEEDS_ROOM_COLUMN = False
# Flag to track if we need to add the seen_room_unlock column
NEEDS_SEEN_ROOM_COLUMN = False
# Flag to track if we need to ensure eggs resource exists for everyone
NEEDS_EGGS_RESOURCE = False
# Flag to track if we need to add the pets table
NEEDS_PETS_TABLE = False
# Flag to track if we need to add the radix_account_address column
NEEDS_RADIX_ADDRESS_COLUMN = False

# Constants for Evolving Creatures integration
EVOLVING_CREATURES_PACKAGE = "package_rdx1p5u8kkr8z77ujmhyzyx36x677jnjkvfwjphu2mxyc0984eqckgmclq"
EVOLVING_CREATURES_COMPONENT = "component_rdx1cr5q55fea4v2yrn5gy3n9uag9ejw3gt2h5pg9tf8rn4egw9lnchx5d"
CREATURE_NFT_RESOURCE = "resource_rdx1ntq7xkr0345fz8hkkappg2xsnepuj94a9wnu287km5tswu3323sjnl"
TOOL_NFT_RESOURCE = "resource_rdx1ntg0wsnuxq05z75f2jy7k20w72tgkt4crmdzcpyfvvgte3uvr9d5f0"
SPELL_NFT_RESOURCE = "resource_rdx1nfjm7ecgxk4m54pyy3mc75wgshh9usmyruy5rx7gkt3w2megc9s8jf"

# Token resource addresses for Evolving Creatures
TOKEN_ADDRESSES = {
    "XRD": "resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd",
    "CVX": "resource_rdx1th04p2c55884yytgj0e8nq79ze9wjnvu4rpg9d7nh3t698cxdt0cr9",
    "REDDICKS": "resource_rdx1t42hpqvsk4t42l6aw09hwphd2axvetp6gvas9ztue0p30f4hzdwxrp",
    "HUG": "resource_rdx1t5kmyj54jt85malva7fxdrnpvgfgs623yt7ywdaval25vrdlmnwe97",
    "EARLY": "resource_rdx1t5xv44c0u99z096q00mv74emwmxwjw26m98lwlzq6ddlpe9f5cuc7s",
    "FLOOP": "resource_rdx1t5pyvlaas0ljxy0wytm5gvyamyv896m69njqdmm2stukr3xexc2up9",
    "DELIVER": "resource_rdx1t466mhd2l2jmmzxr8cg3mkwjqhs7zmjgtder2utnh0ue5msxrhyk3t",
    "ILIS": "resource_rdx1t4r86qqjtzl8620ahvsxuxaf366s6rf6cpy24psdkmrlkdqvzn47c2",
    "OCI": "resource_rdx1t52pvtk5wfhltchwh3rkzls2x0r98fw9cjhpyrf3vsykhkuwrf7jg8",
    "WOWO": "resource_rdx1t4kc5ljyrwlxvg54s6gnctt7nwwgx89h9r2gvrpm369s23yhzyyzlx",
    "MOX": "resource_rdx1thmjcqjnlfm56v7k5g2szfrc44jn22x8tjh7xyczjpswmsnasjl5l9",
    "DAN": "resource_rdx1tk4y4ct50fzgyjygm7j3y6r3cw5rgsatyfnwdz64yp5t388v0atw8w",
    "FOMO": "resource_rdx1t5l954908vmg465pkj7j37z0fn4j33cdjt2g6czavjde406y4uxdy9",
    "DGC": "resource_rdx1t4qfgjm35dkwdrpzl3d8pc053uw9v4pj5wfek0ffuzsp73evye6wu6",
    "HIT": "resource_rdx1t4v2jke9xkcrqra9sf3lzgpxwdr590npkt03vufty4pwuu205q03az",
    "DELAY": "resource_rdx1t4dsaa07eaytq0asfe774maqzhrakfjkpxyng2ud4j6y2tdm5l7a76",
    "EDGE": "resource_rdx1t5vjqccrdtvxruu0p2hwqpts326kpz674grrzulcquly5ue0sg7wxk",
    "CASSIE": "resource_rdx1tk7g72c0uv2g83g3dqtkg6jyjwkre6qnusgjhrtz0cj9u54djgnk3c",
    "RBX": "resource_rdx1t5lenm5rr0p7urmcfjpzq5syt7cpges3wv3hzefckqe49ga6wutrhf"
}

# Species data for Evolving Creatures
SPECIES_DATA = {
    # Common Creatures (50% chance)
    1: {
        "name": "Bullx",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Common",
        "preferred_token": "RBX",
        "evolution_prices": [50, 100, 200],
        "stat_price": 100,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/bullx"
    },
    2: {
        "name": "Cudoge",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Common",
        "preferred_token": "DGC",
        "evolution_prices": [100000, 200000, 300000],
        "stat_price": 200000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/cudoge"
    },
    3: {
        "name": "Cvxling",
        "specialty_stats": ["speed", "energy"],
        "rarity": "Common",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/cvxling"
    },
    4: {
        "name": "Dan",
        "specialty_stats": ["stamina", "magic"],
        "rarity": "Common",
        "preferred_token": "DAN",
        "evolution_prices": [500000, 1000000, 2000000],
        "stat_price": 1000000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/dan"
    },
    5: {
        "name": "Delayer",
        "specialty_stats": ["magic"],
        "rarity": "Common",
        "preferred_token": "DELAY",
        "evolution_prices": [20000, 40000, 100000],
        "stat_price": 40000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/delayer"
    },
    6: {
        "name": "Delivera",
        "specialty_stats": ["stamina", "strength"],
        "rarity": "Common",
        "preferred_token": "DELIVER",
        "evolution_prices": [1000, 2000, 4000],
        "stat_price": 2000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/delivera"
    },
    7: {
        "name": "Flooper",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Common",
        "preferred_token": "FLOOP",
        "evolution_prices": [0.001, 0.002, 0.003],
        "stat_price": 0.002,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/flooper"
    },
    8: {
        "name": "Hitter",
        "specialty_stats": ["strength", "magic"],
        "rarity": "Common",
        "preferred_token": "HIT",
        "evolution_prices": [20000000, 40000000, 100000000],
        "stat_price": 40000000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/hitter"
    },
    9: {
        "name": "Moxer",
        "specialty_stats": ["speed", "magic"],
        "rarity": "Common",
        "preferred_token": "MOX",
        "evolution_prices": [200, 400, 1000],
        "stat_price": 400,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/moxer"
    },
    10: {
        "name": "Ocipod",
        "specialty_stats": ["energy"],
        "rarity": "Common",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/ocipod"
    },
    # Rare Creatures (30% chance)
    11: {
        "name": "Wowori",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Rare",
        "preferred_token": "WOWO",
        "evolution_prices": [4000, 10000, 20000],
        "stat_price": 10000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/wowori"
    },
    12: {
        "name": "Earlybyte",
        "specialty_stats": ["speed", "energy"],
        "rarity": "Rare",
        "preferred_token": "EARLY",
        "evolution_prices": [1000, 2000, 4000],
        "stat_price": 2000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/earlybyte"
    },
    13: {
        "name": "Edge",
        "specialty_stats": ["strength", "energy"],
        "rarity": "Rare",
        "preferred_token": "EDGE",
        "evolution_prices": [20000000, 40000000, 100000000],
        "stat_price": 40000000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/edge"
    },
    14: {
        "name": "Fomotron",
        "specialty_stats": ["energy", "strength"],
        "rarity": "Rare",
        "preferred_token": "FOMO",
        "evolution_prices": [200, 500, 1000],
        "stat_price": 500,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/fomotron"
    },
    15: {
        "name": "Hodlphant",
        "specialty_stats": ["strength"],
        "rarity": "Rare",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/hodlphant"
    },
    16: {
        "name": "Minermole",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Rare",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/minermole"
    },
    17: {
        "name": "Ocitrup",
        "specialty_stats": ["speed", "strength"],
        "rarity": "Rare",
        "preferred_token": "OCI",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/ocitrup"
    },
    # Epic Creatures (15% chance)
    18: {
        "name": "Etherion",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Epic",
        "preferred_token": "XRD",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/etherion"
    },
    19: {
        "name": "Hugbloom",
        "specialty_stats": ["stamina"],
        "rarity": "Epic",
        "preferred_token": "HUG",
        "evolution_prices": [100000, 300000, 500000],
        "stat_price": 300000,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/hugbloom"
    },
    20: {
        "name": "Ilispect",
        "specialty_stats": ["stamina", "magic"],
        "rarity": "Epic",
        "preferred_token": "ILIS",
        "evolution_prices": [200, 400, 1000],
        "stat_price": 400,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/ilispect"
    },
    21: {
        "name": "Reddix",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Epic",
        "preferred_token": "REDDICKS",
        "evolution_prices": [300, 500, 1000],
        "stat_price": 500,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/reddix"
    },
    22: {
        "name": "Satoshium",
        "specialty_stats": ["strength", "stamina"],
        "rarity": "Epic",
        "preferred_token": "XRD",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/satoshium"
    },
    # Legendary Creatures (5% chance)
    23: {
        "name": "Cassie",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Legendary",
        "preferred_token": "CASSIE",
        "evolution_prices": [0.004, 0.01, 0.02],
        "stat_price": 0.01,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/cassie"
    },
    24: {
        "name": "Corvax",
        "specialty_stats": ["magic", "energy"],
        "rarity": "Legendary",
        "preferred_token": "CVX",
        "evolution_prices": [20, 50, 100],
        "stat_price": 50,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/corvax"
    },
    25: {
        "name": "Xerdian",
        "specialty_stats": ["stamina", "energy"],
        "rarity": "Legendary",
        "preferred_token": "XRD",
        "evolution_prices": [100, 200, 400],
        "stat_price": 200,
        "base_url": "https://cvxlab.net/assets/evolving_creatures/xerdian"
    }
}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def check_and_update_schema():
    """Check if the database schema needs updating and update if necessary."""
    global NEEDS_SCHEMA_UPDATE
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the provisional_mint column exists
        cursor.execute("PRAGMA table_info(user_machines)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'provisional_mint' not in columns:
            print("Adding provisional_mint column to user_machines table")
            try:
                cursor.execute("ALTER TABLE user_machines ADD COLUMN provisional_mint INTEGER DEFAULT 0")
                conn.commit()
                print("Column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
                NEEDS_SCHEMA_UPDATE = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking schema: {e}")
        NEEDS_SCHEMA_UPDATE = True

def check_and_update_room_column():
    """Check if the room column exists in user_machines and add if necessary."""
    global NEEDS_ROOM_COLUMN
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the room column exists
        cursor.execute("PRAGMA table_info(user_machines)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'room' not in columns:
            print("Adding room column to user_machines table")
            try:
                cursor.execute("ALTER TABLE user_machines ADD COLUMN room INTEGER DEFAULT 1")
                conn.commit()
                print("Room column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding room column: {e}")
                NEEDS_ROOM_COLUMN = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking room column: {e}")
        NEEDS_ROOM_COLUMN = True

def check_and_update_users_schema():
    """Check if the users table has a radix_account_address column and add it if necessary."""
    global NEEDS_RADIX_ADDRESS_COLUMN
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the radix_account_address column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'radix_account_address' not in columns:
            print("Adding radix_account_address column to users table")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN radix_account_address TEXT")
                conn.commit()
                print("radix_account_address column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding radix_account_address column: {e}")
                NEEDS_RADIX_ADDRESS_COLUMN = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking users schema: {e}")
        NEEDS_RADIX_ADDRESS_COLUMN = True

def check_and_update_seen_room_column():
    """Check if the seen_room_unlock column exists in users and add if necessary."""
    global NEEDS_SEEN_ROOM_COLUMN
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the seen_room_unlock column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'seen_room_unlock' not in columns:
            print("Adding seen_room_unlock column to users table")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN seen_room_unlock INTEGER DEFAULT 0")
                conn.commit()
                print("seen_room_unlock column added successfully")
            except sqlite3.Error as e:
                print(f"Error adding seen_room_unlock column: {e}")
                NEEDS_SEEN_ROOM_COLUMN = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking seen_room_unlock column: {e}")
        NEEDS_SEEN_ROOM_COLUMN = True

def check_and_update_pets_table():
    """Check if the pets table exists and create if necessary."""
    global NEEDS_PETS_TABLE
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the pets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pets'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("Creating pets table")
            try:
                cursor.execute("""
                    CREATE TABLE pets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        x INTEGER NOT NULL,
                        y INTEGER NOT NULL,
                        room INTEGER DEFAULT 1,
                        type TEXT DEFAULT 'cat',
                        parent_machine INTEGER DEFAULT NULL
                    )
                """)
                conn.commit()
                print("Pets table created successfully")
            except sqlite3.Error as e:
                print(f"Error creating pets table: {e}")
                NEEDS_PETS_TABLE = True
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking pets table: {e}")
        NEEDS_PETS_TABLE = True

def ensure_eggs_resource_exists():
    """Ensure the eggs resource exists for all users."""
    global NEEDS_EGGS_RESOURCE
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all user IDs
        cursor.execute("SELECT user_id FROM users")
        user_ids = [row['user_id'] for row in cursor.fetchall()]
        
        # Check and create eggs resource for each user
        for user_id in user_ids:
            cursor.execute(
                "SELECT COUNT(*) FROM resources WHERE user_id=? AND resource_name='eggs'", 
                (user_id,)
            )
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"Adding eggs resource for user {user_id}")
                cursor.execute(
                    "INSERT INTO resources (user_id, resource_name, amount) VALUES (?, 'eggs', 0)",
                    (user_id,)
                )
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Eggs resource check completed")
    except Exception as e:
        print(f"Error ensuring eggs resource: {e}")
        NEEDS_EGGS_RESOURCE = True

# Run schema checks on startup
check_and_update_schema()
check_and_update_room_column()
check_and_update_seen_room_column()
ensure_eggs_resource_exists()
check_and_update_pets_table()
check_and_update_users_schema()

def fetch_scvx_balance(account_address):
    """Fetch sCVX balance for a Radix account using the Gateway API."""
    if not account_address:
        print("No account address provided")
        return 0
        
    try:
        # sCVX resource address
        scvx_resource = 'resource_rdx1t5q4aa74uxcgzehk0u3hjy6kng9rqyr4uvktnud8ehdqaaez50n693'
        
        # Use the Gateway API
        url = "https://mainnet.radixdlt.com/state/entity/page/fungibles/"
        print(f"Fetching sCVX for {account_address} using Gateway API")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "limit_per_page": 100  # Get a reasonable number of tokens
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        print(f"Making Gateway API request with payload: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        print(f"Gateway API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Print debugging info
        print(f"Gateway API total_count: {data.get('total_count', 0)}")
        
        # Look for the sCVX resource in the items
        items = data.get('items', [])
        print(f"Found {len(items)} resources in the account")
        
        # Dump all resources for debugging
        print("All resources in account:")
        for i, item in enumerate(items):
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            print(f"Resource {i}: {resource_addr} = {amount}")
            
            # Check if this is the sCVX resource
            if resource_addr == scvx_resource:
                amount_value = float(amount)
                print(f"FOUND sCVX RESOURCE: {amount_value}")
                return amount_value
        
        # If we get here, we didn't find the resource - look for partial matches
        print("Trying partial resource address matching...")
        for item in items:
            resource_addr = item.get('resource_address', '')
            if scvx_resource[-8:] in resource_addr:  # Match on last few chars
                amount = float(item.get('amount', '0'))
                print(f"Found potential sCVX match with amount: {amount}")
                return amount
                
        return 0
    except Exception as e:
        print(f"Error fetching sCVX with Gateway API: {e}")
        traceback.print_exc()
        return 0

def fetch_xrd_balance(account_address):
    """Fetch XRD balance for a Radix account using the Gateway API with improved reliability."""
    if not account_address:
        print("No account address provided")
        return 0
        
    try:
        # XRD resource address - This is the canonical XRD address
        xrd_resource = 'resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd'
        xrd_short_identifier = 'radxrd' # A unique identifier for XRD that's part of the address
        
        # Use the Gateway API
        url = "https://mainnet.radixdlt.com/state/entity/page/fungibles/"
        print(f"Fetching XRD for {account_address} using Gateway API")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "limit_per_page": 100  # Get a reasonable number of tokens
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        print(f"Making Gateway API request with payload: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        print(f"Gateway API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            # Try a second time before giving up
            print("Retrying XRD balance check...")
            time.sleep(2)  # Brief delay before retry
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Retry failed with status: {response.status_code}")
                return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Print debugging info
        print(f"Gateway API total_count: {data.get('total_count', 0)}")
        
        # Look for the XRD resource in the items
        items = data.get('items', [])
        print(f"Found {len(items)} resources in the account")
        
        # Print the first few resources to help diagnose issues
        for i, item in enumerate(items[:5]):
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            print(f"Resource {i}: {resource_addr} = {amount}")
        
        # First try exact match
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this is the XRD resource with exact match
            if resource_addr.lower() == xrd_resource.lower():
                amount_value = float(amount)
                print(f"FOUND XRD RESOURCE (exact match): {amount_value}")
                return amount_value
        
        # If exact match fails, try a more flexible approach with the unique identifier
        print("No exact match found for XRD, trying identifier match...")
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this resource address contains the XRD identifier
            if xrd_short_identifier in resource_addr.lower():
                amount_value = float(amount)
                print(f"FOUND XRD RESOURCE (identifier match): {amount_value}")
                return amount_value
        
        # Final fallback: check if there are additional pages of results
        if 'next_cursor' in data and data.get('total_count', 0) > len(items):
            print("Additional pages of tokens exist, but XRD not found in first page")
            # In a full implementation, we would handle pagination here
        
        # If we get here, we didn't find XRD
        print("XRD not found in account fungible tokens")
        return 0
    except Exception as e:
        print(f"Error fetching XRD with Gateway API: {e}")
        traceback.print_exc()
        # Try an alternative approach or display an error rather than silent fail
        return 0

def fetch_token_balance(account_address, token_symbol):
    """
    Fetch balance of a specific token for a Radix account.
    Returns: float balance or 0 if not found
    """
    if not account_address or not token_symbol:
        print(f"Missing account address or token symbol: {account_address}, {token_symbol}")
        return 0
        
    try:
        # Get the resource address for the token
        token_resource = TOKEN_ADDRESSES.get(token_symbol)
        if not token_resource:
            print(f"Unknown token symbol: {token_symbol}")
            return 0
        
        # Use the Gateway API
        url = "https://mainnet.radixdlt.com/state/entity/page/fungibles/"
        print(f"Fetching {token_symbol} for {account_address} using Gateway API")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "limit_per_page": 100  # Get a reasonable number of tokens
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Look for the token resource in the items
        items = data.get('items', [])
        
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this is the requested token
            if resource_addr == token_resource:
                amount_value = float(amount)
                print(f"FOUND {token_symbol} RESOURCE: {amount_value}")
                return amount_value
        
        # If we get here, we didn't find the token
        return 0
    except Exception as e:
        print(f"Error fetching {token_symbol} with Gateway API: {e}")
        traceback.print_exc()
        return 0


def fetch_nft_data(resource_address, non_fungible_ids):
    """
    Fetch data for specific non-fungible tokens with proper 
    error handling and batch processing.
    
    Returns: dict of NFT ID to data or empty dict if none found
    """
    if not non_fungible_ids:
        return {}
        
    try:
        gateway_url = "https://mainnet.radixdlt.com"
        url = f"{gateway_url}/state/non-fungible/data"
        
        print(f"Fetching data for {len(non_fungible_ids)} NFTs of resource {resource_address}")
        
        # For consistency, first get current ledger state
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        status_response = requests.post(
            f"{gateway_url}/status/current",
            headers=headers,
            json={},
            timeout=15
        )
        
        if status_response.status_code != 200:
            print(f"Failed to get current ledger state: {status_response.text[:200]}")
            return {}
            
        ledger_state = status_response.json().get("ledger_state")
        print(f"Using ledger state for NFT data: {ledger_state}")
        
        # Need to batch requests if we have more than 100 NFTs (API limit)
        all_nft_data = {}
        batch_size = 100  # API limits to around 100 IDs per request
        
        for i in range(0, len(non_fungible_ids), batch_size):
            batch = non_fungible_ids[i:min(i+batch_size, len(non_fungible_ids))]
            print(f"Processing batch {i//batch_size + 1} with {len(batch)} NFTs")
            
            # Prepare request payload with ledger state for consistency
            payload = {
                "resource_address": resource_address,
                "non_fungible_ids": batch,
                "at_ledger_state": ledger_state
            }
            
            # Implement retry with exponential backoff
            max_retries = 3
            retry_delay = 1
            
            for retry in range(max_retries):
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=20)
                    
                    if response.status_code == 429:  # Rate limited
                        if retry < max_retries - 1:
                            sleep_time = retry_delay * (2 ** retry)
                            print(f"Rate limited, retrying in {sleep_time} seconds...")
                            time.sleep(sleep_time)
                            continue
                    
                    break  # Success or non-retry error
                except requests.exceptions.RequestException as e:
                    if retry < max_retries - 1:
                        sleep_time = retry_delay * (2 ** retry)
                        print(f"Request failed, retrying in {sleep_time} seconds: {e}")
                        time.sleep(sleep_time)
                    else:
                        raise
            
            if response.status_code != 200:
                print(f"Gateway API error: Status {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                continue  # Try next batch instead of failing completely
            
            # Parse the JSON response
            data = response.json()
            
            # The response format changed slightly in different Gateway API versions
            # Handle both older and newer formats
            if 'non_fungible_ids' in data:
                # Newer format - directly contains the data
                for nft_id, nft_data in data['non_fungible_ids'].items():
                    all_nft_data[nft_id] = nft_data.get('data', {})
            else:
                # Older format or different structure
                items = data.get('items', [])
                for item in items:
                    nft_id = item.get('non_fungible_id')
                    if nft_id:
                        all_nft_data[nft_id] = item.get('data', {})
            
            print(f"Processed {len(batch)} NFTs in batch {i//batch_size + 1}")
        
        print(f"Total NFTs data retrieved: {len(all_nft_data)}")
        return all_nft_data
        
    except Exception as e:
        print(f"Error fetching NFT data with Gateway API: {e}")
        traceback.print_exc()
        return {}

def process_creature_data(nft_id, nft_data):
    """
    Process raw creature NFT data into the expected format for the frontend with
    better error handling and data validation.
    """
    try:
        # Default values in case some fields are missing
        processed_data = {
            "id": nft_id,
            "species_id": 1,
            "species_name": "Unknown",
            "form": 0,
            "key_image_url": "",
            "image_url": "",
            "rarity": "Common",
            "stats": {
                "energy": 5,
                "strength": 5,
                "magic": 5,
                "stamina": 5,
                "speed": 5
            },
            "evolution_progress": {
                "stat_upgrades_completed": 0,
                "total_points_allocated": 0,
                "energy_allocated": 0,
                "strength_allocated": 0,
                "magic_allocated": 0,
                "stamina_allocated": 0,
                "speed_allocated": 0
            },
            "final_form_upgrades": 0,
            "version": 1,
            "combination_level": 0,
            "bonus_stats": {},
            "display_form": "Egg",
            "display_stats": "",
            "display_combination": "",
            "preferred_token": "XRD"
        }
        
        # Update with actual data if available
        if not nft_data:
            print(f"No data for NFT {nft_id}")
            return processed_data
            
        # Handle different possible data structures
        if isinstance(nft_data, str):
            try:
                # Sometimes the data may be a JSON string
                nft_data = json.loads(nft_data)
            except json.JSONDecodeError:
                print(f"Could not parse NFT data as JSON: {nft_data[:100]}...")
                # Try to extract from programmatic_json if it's there
                if "programmatic_json" in nft_data:
                    try:
                        nft_data = json.loads(nft_data["programmatic_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        # Try to handle various structures in the Radix Gateway API response
        if "programmatic_json" in nft_data:
            try:
                programmatic_data = json.loads(nft_data["programmatic_json"])
                if isinstance(programmatic_data, dict):
                    nft_data = programmatic_data
            except (json.JSONDecodeError, TypeError):
                pass
                
        # Debug output to find where the data is
        print(f"NFT Data structure for {nft_id}: {type(nft_data)}")
        if isinstance(nft_data, dict):
            print(f"Keys in nft_data: {list(nft_data.keys())}")
            
        # Species information
        species_id = 1  # Default
        if "species_id" in nft_data:
            species_id = int(nft_data["species_id"])
            processed_data["species_id"] = species_id
        
        # Get species information from SPECIES_DATA
        species_info = SPECIES_DATA.get(species_id, {"name": "Unknown", "preferred_token": "XRD", "rarity": "Common"})
        processed_data["species_name"] = species_info.get("name", "Unknown")
        processed_data["rarity"] = species_info.get("rarity", "Common")
        processed_data["preferred_token"] = species_info.get("preferred_token", "XRD")
        
        # Add specialty stats if available
        if "specialty_stats" in species_info:
            processed_data["specialty_stats"] = species_info["specialty_stats"]
        
        # Form and image URL
        if "form" in nft_data:
            form = int(nft_data["form"])
            processed_data["form"] = form
        else:
            form = 0  # Default to egg form
        
        # Determine form name for display
        if form == 0:
            processed_data["display_form"] = "Egg"
        elif form == 1:
            processed_data["display_form"] = "Form 1"
        elif form == 2:
            processed_data["display_form"] = "Form 2"
        elif form == 3:
            processed_data["display_form"] = "Form 3 (Final)"
        
        # Generate image URLs based on form
        base_url = species_info.get("base_url", "https://cvxlab.net/assets/evolving_creatures/bullx")
        if form == 0:
            image_url = f"{base_url}_egg.png"
        elif form == 1:
            image_url = f"{base_url}_form1.png"
        elif form == 2:
            image_url = f"{base_url}_form2.png"
        elif form == 3:
            image_url = f"{base_url}_form3.png"
        else:
            image_url = f"{base_url}_egg.png"
            
        processed_data["key_image_url"] = image_url
        processed_data["image_url"] = image_url
        
        # Stats with proper type conversion
        if "stats" in nft_data:
            stats = nft_data["stats"]
            processed_data["stats"] = {
                "energy": int(stats.get("energy", 5)),
                "strength": int(stats.get("strength", 5)),
                "magic": int(stats.get("magic", 5)),
                "stamina": int(stats.get("stamina", 5)),
                "speed": int(stats.get("speed", 5))
            }
        
        # Evolution progress
        if "evolution_progress" in nft_data:
            evolution_progress = nft_data["evolution_progress"]
            processed_data["evolution_progress"] = {
                "stat_upgrades_completed": int(evolution_progress.get("stat_upgrades_completed", 0)),
                "total_points_allocated": int(evolution_progress.get("total_points_allocated", 0)),
                "energy_allocated": int(evolution_progress.get("energy_allocated", 0)),
                "strength_allocated": int(evolution_progress.get("strength_allocated", 0)),
                "magic_allocated": int(evolution_progress.get("magic_allocated", 0)),
                "stamina_allocated": int(evolution_progress.get("stamina_allocated", 0)),
                "speed_allocated": int(evolution_progress.get("speed_allocated", 0))
            }
        elif form == 3:
            # Form 3 creatures don't have evolution progress
            processed_data["evolution_progress"] = None
        
        # Final form upgrades
        if "final_form_upgrades" in nft_data:
            processed_data["final_form_upgrades"] = int(nft_data["final_form_upgrades"])
        
        # Version
        if "version" in nft_data:
            processed_data["version"] = int(nft_data["version"])
        
        # Combination level and bonus stats
        if "combination_level" in nft_data:
            combination_level = int(nft_data["combination_level"])
            processed_data["combination_level"] = combination_level
            
            if combination_level > 0:
                processed_data["display_combination"] = f"Fusion Level {combination_level}"
                
            # Bonus stats if available
            if "bonus_stats" in nft_data and nft_data["bonus_stats"]:
                bonus_stats = nft_data["bonus_stats"]
                processed_data["bonus_stats"] = {k: int(v) for k, v in bonus_stats.items()}
        
        # Generate display stats string
        stats_str = ", ".join([f"{stat.capitalize()}: {value}" for stat, value in processed_data["stats"].items()])
        processed_data["display_stats"] = stats_str
        
        return processed_data
        
    except Exception as e:
        print(f"Error processing creature data for NFT {nft_id}: {e}")
        traceback.print_exc()
        return {
            "id": nft_id,
            "species_name": "Error",
            "form": 0,
            "image_url": "https://cvxlab.net/assets/evolving_creatures/bullx_egg.png",
            "rarity": "Common",
            "error": str(e)
        }

def calculate_upgrade_cost(creature, energy=0, strength=0, magic=0, stamina=0, speed=0):
    """
    Calculate the cost for upgrading stats for a creature.
    Returns: dict with token and amount
    """
    try:
        # First try to use the provided creature data
        if creature:
            # Get species info
            species_id = creature.get("species_id", 1)
            species_info = SPECIES_DATA.get(species_id, {})
            
            # Get preferred token
            token_symbol = species_info.get("preferred_token", "XRD")
            
            # Get form
            form = creature.get("form", 0)
            
            # Default stat price if not specified
            stat_price = species_info.get("stat_price", 50)
            
            # For final form (form 3), cost is stat_price * total points
            if form == 3:
                total_points = energy + strength + magic + stamina + speed
                return {
                    "token": token_symbol,
                    "amount": stat_price * total_points
                }
            
            # For forms 0-2, cost depends on which upgrade it is
            evolution_progress = creature.get("evolution_progress", {})
            if not evolution_progress:
                return {
                    "token": token_symbol,
                    "amount": 0
                }
                
            upgrades_completed = evolution_progress.get("stat_upgrades_completed", 0)
            
            # Cost increases with each upgrade (10%, 20%, 30% of evolution price)
            evolution_prices = species_info.get("evolution_prices", [50, 100, 200])
            if form < len(evolution_prices):
                evolution_price = evolution_prices[form]
            else:
                evolution_price = evolution_prices[-1]
                
            # Calculate percentage based on upgrade number
            percentage = 0.1 * (upgrades_completed + 1)  # 0.1, 0.2, 0.3
            upgrade_cost = evolution_price * percentage
            
            return {
                "token": token_symbol,
                "amount": upgrade_cost
            }
        else:
            # If no creature data provided, we need to fetch it from the blockchain
            # This should be rare since we typically have the creature data already
            return {
                "token": "XRD",  # Default to XRD
                "amount": 100    # Default amount
            }
    except Exception as e:
        print(f"Error calculating upgrade cost: {e}")
        traceback.print_exc()
        return {
            "token": "XRD",
            "amount": 0
        }

def calculate_evolution_cost(creature):
    """
    Calculate the cost for evolving a creature to the next form.
    Returns: dict with token and amount
    """
    try:
        if not creature:
            return {
                "token": "XRD",
                "amount": 0,
                "can_evolve": False,
                "reason": "Invalid creature data"
            }
            
        # Get species info
        species_id = creature.get("species_id", 1)
        species_info = SPECIES_DATA.get(species_id, {})
        
        # Get preferred token
        token_symbol = species_info.get("preferred_token", "XRD")
        
        # Get form
        form = creature.get("form", 0)
        
        # Check if creature can evolve (must be form 0-2)
        if form >= 3:
            return {
                "token": token_symbol,
                "amount": 0,
                "can_evolve": False,
                "reason": "Already at max form"
            }
        
        # Check if creature has completed 3 stat upgrades
        evolution_progress = creature.get("evolution_progress", {})
        if not evolution_progress:
            return {
                "token": token_symbol,
                "amount": 0,
                "can_evolve": False,
                "reason": "No evolution progress data"
            }
                
        upgrades_completed = evolution_progress.get("stat_upgrades_completed", 0)
        if upgrades_completed < 3:
            return {
                "token": token_symbol,
                "amount": 0,
                "can_evolve": False,
                "reason": f"Need 3 stat upgrades, only has {upgrades_completed}"
            }
        
        # Get evolution price for current form
        evolution_prices = species_info.get("evolution_prices", [50, 100, 200])
        if form < len(evolution_prices):
            evolution_price = evolution_prices[form]
        else:
            evolution_price = evolution_prices[-1]
                
        # Calculate total already paid in upgrades
        # Typically 10% + 20% + 30% = 60% of full evolution price
        paid_percentage = 0.6  # 0.1 + 0.2 + 0.3
        remaining_cost = evolution_price * (1 - paid_percentage)
        
        return {
            "token": token_symbol,
            "amount": remaining_cost,
            "can_evolve": True
        }
    except Exception as e:
        print(f"Error calculating evolution cost: {e}")
        traceback.print_exc()
        return {
            "token": "XRD",
            "amount": 0,
            "can_evolve": False,
            "reason": f"Error: {str(e)}"
        }

def can_build_fomo_hit(cur, user_id):
    """Check if user has built and fully operational all other machine types."""
    print(f"Checking FOMO HIT prerequisites for user_id: {user_id}")
    try:
        # 1. Check if they've built all required machine types
        required_types = ['catLair', 'reactor', 'amplifier', 'incubator']
        for machine_type in required_types:
            cur.execute("""
                SELECT COUNT(*) as count FROM user_machines
                WHERE user_id=? AND machine_type=?
            """, (user_id, machine_type))
            row = cur.fetchone()
            count = row[0] if row else 0
            print(f"  Machine type {machine_type}: {count} found")
            if count == 0:
                print(f"  Missing required machine: {machine_type}")
                return False
        
        # 2. For cat lairs and reactors, check ALL are at max level (3)
        # First, get total count of each type
        for machine_type in ['catLair', 'reactor']:
            # Get total number of this machine type
            cur.execute("""
                SELECT COUNT(*) as total FROM user_machines
                WHERE user_id=? AND machine_type=?
            """, (user_id, machine_type))
            total_row = cur.fetchone()
            total = total_row[0] if total_row else 0
            
            # Get how many are at max level
            cur.execute("""
                SELECT COUNT(*) as max_count FROM user_machines 
                WHERE user_id=? AND machine_type=? AND level>=3
            """, (user_id, machine_type))
            max_row = cur.fetchone()
            max_count = max_row[0] if max_row else 0
            
            print(f"  {machine_type}: {max_count}/{total} at max level")
            
            # For now, as long as one machine is at max level for each type, that counts as success
            if max_count == 0:
                print(f"  No {machine_type} machines at max level")
                return False
        
        # 3. For amplifier, check it's at max level (5)
        cur.execute("""
            SELECT MAX(level) as max_level FROM user_machines
            WHERE user_id=? AND machine_type='amplifier'
        """, (user_id,))
        max_level_row = cur.fetchone()
        max_level = max_level_row[0] if max_level_row else 0
        print(f"  Amplifier max level: {max_level}/5")
        
        # For now, level 3 amplifier is ok as a prerequisite 
        if max_level < 3:
            print(f"  Amplifier not at required level")
            return False
        
        # 4. Check that incubator is operational (not offline)
        cur.execute("""
            SELECT is_offline FROM user_machines
            WHERE user_id=? AND machine_type='incubator'
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        is_offline = row[0] if row else 1
        print(f"  Incubator offline status: {is_offline}")
        
        # For testing, let's ignore the incubator online check
        # Remove this if-statement in production
        if is_offline == 1:
            print(f"  Incubator is offline but we'll allow FOMO HIT for testing")
            # return False  # Comment this out for easier testing
            
        print("✅ All FOMO HIT prerequisites met!")
        return True
    except Exception as e:
        print(f"Error in can_build_fomo_hit: {e}")
        import traceback
        traceback.print_exc()
        return False

def can_build_third_reactor(cur, user_id):
    """Check if user can build a third reactor (has incubator and fomoHit)."""
    try:
        # Check if incubator exists
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='incubator'
        """, (user_id,))
        has_incubator = cur.fetchone()[0] > 0
        
        # Check if fomoHit exists
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='fomoHit'
        """, (user_id,))
        has_fomo_hit = cur.fetchone()[0] > 0
        
        # Count current reactors
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='reactor'
        """, (user_id,))
        reactor_count = cur.fetchone()[0]
        
        # Can build third reactor if:
        # 1. Has both incubator and fomoHit
        # 2. Currently has 2 reactors (this would be the third)
        return has_incubator and has_fomo_hit and reactor_count == 2
    except Exception as e:
        print(f"Error in can_build_third_reactor: {e}")
        traceback.print_exc()
        return False

def create_nft_mint_manifest(account_address):
    """Create the Radix transaction manifest for NFT minting."""
    try:
        # Generate a random ID for the NFT
        nft_id = str(uuid.uuid4())[:8]
        
        # Simple manifest that calls a component to mint an NFT
        # The component address should be your actual minting component
        manifest = f"""
CALL_METHOD
    Address("component_rdx1cqpv4nfsgfk9c2r9ymnqyksfkjsg07mfc49m9qw3dpgzrmjmsuuquv")
    "mint_user_nft"
;
CALL_METHOD
    Address("{account_address}")
    "try_deposit_batch_or_abort"
    Expression("ENTIRE_WORKTOP")
    None
;
"""
        return manifest
    except Exception as e:
        print(f"Error creating NFT mint manifest: {e}")
        traceback.print_exc()
        return None

def create_evolving_creature_manifest(account_address):
    """Create the Radix transaction manifest for minting an evolving creature egg."""
    try:
        # XRD resource address
        xrd_resource = "resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd"
        # Component address for the Evolving Creatures package
        component_address = "component_rdx1cr5q55fea4v2yrn5gy3n9uag9ejw3gt2h5pg9tf8rn4egw9lnchx5d"
        
        # Create manifest to mint an egg
        manifest = f"""
CALL_METHOD
    Address("{account_address}")
    "withdraw"
    Address("{xrd_resource}")
    Decimal("250");
TAKE_FROM_WORKTOP
    Address("{xrd_resource}")
    Decimal("250")
    Bucket("payment");
CALL_METHOD
    Address("{component_address}")
    "mint_egg"
    Bucket("payment");
CALL_METHOD
    Address("{account_address}")
    "try_deposit_batch_or_abort"
    Expression("ENTIRE_WORKTOP")
    None;
"""
        return manifest

    except Exception as e:
        print(f"Error creating evolving creature mint manifest: {e}")
        traceback.print_exc()
        return None

def create_upgrade_stats_manifest(account_address, creature_id, energy=0, strength=0, magic=0, stamina=0, speed=0, token_resource=None, token_amount=0):
    """
    Create the Radix transaction manifest for upgrading stats of a creature.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_id: The ID of the creature NFT
    - energy, strength, magic, stamina, speed: The stat points to allocate
    - token_resource: The resource address of the payment token
    - token_amount: The amount of tokens to pay
    
    Returns: The transaction manifest as a string
    """
    try:
        # Use XRD as fallback if no token specified
        if not token_resource:
            token_resource = TOKEN_ADDRESSES["XRD"]
            
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("nft");
CALL_METHOD
    Address("{account_address}") 
    "withdraw" 
    Address("{token_resource}") 
    Decimal("{token_amount}");
TAKE_FROM_WORKTOP
    Address("{token_resource}")
    Decimal("{token_amount}")
    Bucket("payment");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "upgrade_stats"
    Bucket("nft")
    Bucket("payment")
    {energy}u8     # Energy increase
    {strength}u8   # Strength increase
    {magic}u8      # Magic increase
    {stamina}u8    # Stamina increase
    {speed}u8;     # Speed increase
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating upgrade stats manifest: {e}")
        traceback.print_exc()
        return None

def create_evolve_manifest(account_address, creature_id, token_resource=None, token_amount=0):
    """
    Create the Radix transaction manifest for evolving a creature to the next form.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_id: The ID of the creature NFT
    - token_resource: The resource address of the payment token
    - token_amount: The amount of tokens to pay
    
    Returns: The transaction manifest as a string
    """
    try:
        # Use XRD as fallback if no token specified
        if not token_resource:
            token_resource = TOKEN_ADDRESSES["XRD"]
            
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("nft");
CALL_METHOD
    Address("{account_address}") 
    "withdraw" 
    Address("{token_resource}") 
    Decimal("{token_amount}");
TAKE_FROM_WORKTOP
    Address("{token_resource}")
    Decimal("{token_amount}")
    Bucket("payment");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "evolve_to_next_form"
    Bucket("nft")
    Bucket("payment");
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating evolve manifest: {e}")
        traceback.print_exc()
        return None

def create_level_up_manifest(account_address, creature_id, energy=0, strength=0, magic=0, stamina=0, speed=0, token_resource=None, token_amount=0):
    """
    Create the Radix transaction manifest for leveling up stats of a form 3 creature.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_id: The ID of the creature NFT
    - energy, strength, magic, stamina, speed: The stat points to allocate
    - token_resource: The resource address of the payment token
    - token_amount: The amount of tokens to pay
    
    Returns: The transaction manifest as a string
    """
    try:
        # Use XRD as fallback if no token specified
        if not token_resource:
            token_resource = TOKEN_ADDRESSES["XRD"]
            
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("nft");
CALL_METHOD
    Address("{account_address}") 
    "withdraw" 
    Address("{token_resource}") 
    Decimal("{token_amount}");
TAKE_FROM_WORKTOP
    Address("{token_resource}")
    Decimal("{token_amount}")
    Bucket("payment");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "level_up_stats"
    Bucket("nft")
    Bucket("payment")
    {energy}u8     # Energy increase
    {strength}u8   # Strength increase
    {magic}u8      # Magic increase
    {stamina}u8    # Stamina increase
    {speed}u8;     # Speed increase
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating level up manifest: {e}")
        traceback.print_exc()
        return None

def create_combine_creatures_manifest(account_address, creature_a_id, creature_b_id):
    """
    Create the Radix transaction manifest for combining two creatures.
    
    Parameters:
    - account_address: The user's Radix account address
    - creature_a_id: The ID of the primary creature NFT
    - creature_b_id: The ID of the secondary creature NFT to be combined and burned
    
    Returns: The transaction manifest as a string
    """
    try:
        # Create the manifest
        manifest = f"""
CALL_METHOD
    Address("{account_address}") 
    "withdraw_non_fungibles" 
    Address("{CREATURE_NFT_RESOURCE}") 
    Array<NonFungibleLocalId>(
        NonFungibleLocalId("{creature_a_id}"),
        NonFungibleLocalId("{creature_b_id}")
    );
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("creature_a");
TAKE_FROM_WORKTOP
    Address("{CREATURE_NFT_RESOURCE}")
    Decimal("1")
    Bucket("creature_b");
CALL_METHOD
    Address("{EVOLVING_CREATURES_COMPONENT}")
    "combine_creatures"
    Bucket("creature_a")
    Bucket("creature_b");
CALL_METHOD
    Address("{account_address}")
    "deposit_batch"
    Expression("ENTIRE_WORKTOP");
"""
        return manifest
    except Exception as e:
        print(f"Error creating combine creatures manifest: {e}")
        traceback.print_exc()
        return None

def create_buy_energy_manifest(account_address):
    """Create the Radix transaction manifest for buying energy with CVX."""
    try:
        cvx_resource        = "resource_rdx1th04p2c55884yytgj0e8nq79ze9wjnvu4rpg9d7nh3t698cxdt0cr9"
        destination_account = "account_rdx16ya2ncwya20j2w0k8d49us5ksvzepjhhh7cassx9jp9gz6hw69mhks"
        cvx_amount          = "200.0"

        manifest = f"""
CALL_METHOD
    Address("{account_address}")
    "withdraw"
    Address("{cvx_resource}")
    Decimal("{cvx_amount}")
;
CALL_METHOD
    Address("{destination_account}")
    "try_deposit_batch_or_abort"
    Expression("ENTIRE_WORKTOP")
    None
;
"""
        print(f"Generated manifest:\n{manifest}")
        return manifest

    except Exception as e:
        print(f"Error creating energy purchase manifest: {e}")
        traceback.print_exc()
        return None

def get_transaction_status(intent_hash):
    """Check the status of a transaction using the Gateway API."""
    try:
        url = "https://mainnet.radixdlt.com/transaction/status"
        payload = {"intent_hash": intent_hash}
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return {"status": "Unknown", "error": f"HTTP {response.status_code}"}
        
        data = response.json()
        return {
            "status": data.get("status", "Unknown"),
            "intent_status": data.get("intent_status", "Unknown"),
            "error_message": data.get("error_message", "")
        }
    except Exception as e:
        print(f"Error checking transaction status: {e}")
        traceback.print_exc()
        return {"status": "Error", "error": str(e)}

# Function to fetch NFT details from transaction
def get_minted_nfts_from_transaction(intent_hash):
    """
    Get minted NFTs from a transaction using the Gateway API.
    Returns: Tuple of (creature_nft, bonus_item) with complete data
    """
    try:
        # NFT resource addresses
        creature_resource = "resource_rdx1ntq7xkr0345fz8hkkappg2xsnepuj94a9wnu287km5tswu3323sjnl"
        tool_resource = "resource_rdx1ntg0wsnuxq05z75f2jy7k20w72tgkt4crmdzcpyfvvgte3uvr9d5f0"
        spell_resource = "resource_rdx1nfjm7ecgxk4m54pyy3mc75wgshh9usmyruy5rx7gkt3w2megc9s8jf"
        
        # Check if transaction is committed
        status_data = get_transaction_status(intent_hash)
        if status_data.get("status") != "CommittedSuccess":
            print(f"Transaction not completed yet: {status_data}")
            return None, None
        
        # Get transaction details
        url = "https://mainnet.radixdlt.com/transaction/committed-details"
        payload = {
            "intent_hash": intent_hash,
            "opt_ins": {
                "balance_changes": True,
                "non_fungible_changes": True
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return None, None
        
        data = response.json()
        
        # Extract NFT IDs from non-fungible changes
        creature_nft = None
        bonus_item = None
        non_fungible_changes = data.get("non_fungible_changes", [])
        
        creature_id = None
        bonus_item_id = None
        bonus_item_type = None
        
        # First, find the NFT IDs
        for change in non_fungible_changes:
            resource_address = change.get("resource_address")
            operation = change.get("operation")
            
            # Only look at deposit operations (NFTs being received)
            if operation != "DEPOSIT":
                continue
                
            if resource_address == creature_resource:
                # This is a creature NFT
                nft_ids = change.get("non_fungible_ids", [])
                if nft_ids:
                    creature_id = nft_ids[0]
            
            elif resource_address == tool_resource:
                # This is a tool NFT
                nft_ids = change.get("non_fungible_ids", [])
                if nft_ids:
                    bonus_item_id = nft_ids[0]
                    bonus_item_type = "tool"
                    
            elif resource_address == spell_resource:
                # This is a spell NFT
                nft_ids = change.get("non_fungible_ids", [])
                if nft_ids:
                    bonus_item_id = nft_ids[0]
                    bonus_item_type = "spell"
        
        # Now, fetch the actual NFT data for the creature
        if creature_id:
            creature_data = fetch_nft_data(creature_resource, [creature_id])
            if creature_data and creature_id in creature_data:
                raw_data = creature_data[creature_id]
                creature_nft = process_creature_data(creature_id, raw_data)
        
        # Fetch the bonus item data
        if bonus_item_id and bonus_item_type:
            resource_address = tool_resource if bonus_item_type == "tool" else spell_resource
            bonus_data = fetch_nft_data(resource_address, [bonus_item_id])
            
            if bonus_data and bonus_item_id in bonus_data:
                raw_bonus_data = bonus_data[bonus_item_id]
                
                # Process tool or spell data
                if bonus_item_type == "tool":
                    image_url = raw_bonus_data.get("key_image_url", "")
                    name = raw_bonus_data.get("tool_name", "Unknown Tool")
                    tool_type = raw_bonus_data.get("tool_type", "")
                    tool_effect = raw_bonus_data.get("tool_effect", "")
                    
                    bonus_item = {
                        "id": bonus_item_id,
                        "name": name,
                        "type": "tool",
                        "image_url": image_url,
                        "tool_type": tool_type,
                        "tool_effect": tool_effect
                    }
                else:  # spell
                    image_url = raw_bonus_data.get("key_image_url", "")
                    name = raw_bonus_data.get("spell_name", "Unknown Spell")
                    spell_type = raw_bonus_data.get("spell_type", "")
                    spell_effect = raw_bonus_data.get("spell_effect", "")
                    
                    bonus_item = {
                        "id": bonus_item_id,
                        "name": name,
                        "type": "spell",
                        "image_url": image_url,
                        "spell_type": spell_type,
                        "spell_effect": spell_effect
                    }
                
        # If we couldn't get the actual data, create fallback data
        if not creature_nft and creature_id:
            creature_nft = {
                "id": creature_id,
                "species_name": "Random Creature",
                "rarity": "Unknown",
                "image_url": "https://cvxlab.net/assets/evolving_creatures/bullx_egg.png"
            }
            
        if not bonus_item and bonus_item_id:
            bonus_item = {
                "id": bonus_item_id,
                "name": f"Mystery {bonus_item_type.capitalize() if bonus_item_type else 'Item'}",
                "type": bonus_item_type or "unknown",
                "image_url": "https://cvxlab.net/assets/tools/babylon_keystone.png"
            }
            
        return creature_nft, bonus_item
    
    except Exception as e:
        print(f"Error getting minted NFTs: {e}")
        traceback.print_exc()
        return None, None

def verify_telegram_login(query_dict, bot_token):
    try:
        their_hash = query_dict.pop("hash", None)
        if not their_hash:
            return False
        secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
        sorted_kv = sorted(query_dict.items(), key=lambda x: x[0])
        data_check_str = "\n".join([f"{k}={v}" for k, v in sorted_kv])
        calc_hash_bytes = hmac.new(secret_key, data_check_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return calc_hash_bytes == their_hash
    except Exception as e:
        print(f"Error in verify_telegram_login: {e}")
        traceback.print_exc()
        return False

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    try:
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"Error serving path {path}: {e}")
        traceback.print_exc()
        return "Server error", 500

@app.route("/api/getCreatureNfts", methods=["GET", "POST"])
def get_creature_nfts():
    """
    API endpoint to get all creatures for a user - serving the frontend's expected endpoint.
    This implementation uses the updated NFT fetching function.
    """
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        
        # Get account address - prioritize different sources
        account_address = None
        
        # 1. First try request body (POST)
        if request.method == "POST" and request.is_json:
            data = request.get_json(silent=True) or {}
            account_address = data.get("accountAddress")
            print(f"Using account address from POST body: {account_address}")
            
        # 2. Then try query parameters (GET)
        if not account_address and request.args:
            account_address = request.args.get("accountAddress")
            print(f"Using account address from URL params: {account_address}")
            
        # 3. Finally try stored account
        if not account_address:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT radix_account_address FROM users 
                WHERE user_id = ? AND radix_account_address IS NOT NULL
            """, (user_id,))
            
            row = cur.fetchone()
            if row:
                account_address = row['radix_account_address']
                print(f"Using stored account address: {account_address}")
            
            cur.close()
            conn.close()
        
        # If still no account address, return empty list
        if not account_address:
            print(f"No Radix account address found for user {user_id}")
            return jsonify({"creatures": []})
        
        # Get XRD balance for context (using the original function that works)
        xrd_balance = fetch_xrd_balance(account_address)
        print(f"XRD balance: {xrd_balance}")
        
        # Try the simplified approach first
        # This should be more reliable since it uses the global non-fungibles endpoint
        nft_ids = fetch_user_nfts_simplified(account_address, CREATURE_NFT_RESOURCE)
        
        # If that failed, fall back to the updated original approach
        if not nft_ids:
            print("Simplified method returned no NFTs, trying original method with fix...")
            nft_ids = fetch_user_nfts(account_address, CREATURE_NFT_RESOURCE)
        
        if not nft_ids:
            print(f"No creature NFTs found for account {account_address}")
            return jsonify({
                "creatures": [],
                "xrd_balance": xrd_balance
            })
            
        print(f"Found {len(nft_ids)} creature NFTs for account {account_address}")
        
        # Fetch NFT data for all IDs
        nft_data_map = fetch_nft_data(CREATURE_NFT_RESOURCE, nft_ids)
        
        if not nft_data_map:
            print("Could not retrieve NFT data")
            return jsonify({
                "creatures": [],
                "xrd_balance": xrd_balance
            })
        
        # Process each creature's data
        all_creatures = []
        for nft_id, raw_data in nft_data_map.items():
            processed_data = process_creature_data(nft_id, raw_data)
            all_creatures.append(processed_data)
                
        print(f"Processed {len(all_creatures)} creatures for account {account_address}")
        
        # Sort creatures by rarity and form (highest first)
        def get_rarity_score(creature):
            rarity = creature.get("rarity", "Common")
            if rarity == "Legendary":
                return 4
            elif rarity == "Epic":
                return 3
            elif rarity == "Rare":
                return 2
            else:
                return 1
                
        all_creatures.sort(
            key=lambda c: (get_rarity_score(c), c.get("form", 0)), 
            reverse=True
        )
        
        return jsonify({
            "creatures": all_creatures,
            "xrd_balance": xrd_balance
        })
        
    except Exception as e:
        print(f"Error in get_creature_nfts: {e}")
        traceback.print_exc()
        return jsonify({
            "creatures": [],
            "error": str(e)
        })

@app.route("/callback")
def telegram_login_callback():
    print("=== Telegram Callback Called ===")
    try:
        args = request.args.to_dict()
        print(f"Args received: {args}")
        
        user_id = args.get("id")
        tg_hash = args.get("hash")
        auth_date = args.get("auth_date")
        
        if not user_id or not tg_hash or not auth_date:
            print("Missing login data!")
            return "<h3>Missing Telegram login data!</h3>", 400

        if not verify_telegram_login(args, BOT_TOKEN):
            print(f"Invalid hash! Data: {args}")
            return "<h3>Invalid hash - data might be forged!</h3>", 403

        print(f"Login successful for user {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            user_id_int = int(user_id)
        except ValueError:
            user_id_int = user_id

        cursor.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id_int,))
        row = cursor.fetchone()
        if row is None:
            first_name = args.get("first_name", "Unknown")
            print(f"Creating new user: {first_name}")
            cursor.execute(
                "INSERT INTO users (user_id, first_name, corvax_count, seen_room_unlock) VALUES (?, ?, 0, 0)",
                (user_id_int, first_name)
            )
            conn.commit()
            
            # Also create initial eggs resource for new user
            cursor.execute(
                "INSERT INTO resources (user_id, resource_name, amount) VALUES (?, 'eggs', 0)",
                (user_id_int,)
            )
            conn.commit()

        cursor.close()
        conn.close()

        session['telegram_id'] = str(user_id_int)
        print(f"Session set, redirecting to homepage")
        return redirect("https://cvxlab.net/")
    except Exception as e:
        print(f"Error in telegram_login_callback: {e}")
        traceback.print_exc()
        return "<h3>Server error</h3>", 500

@app.route("/api/whoami")
def whoami():
    try:
        print("=== WHOAMI CALLED ===")
        if 'telegram_id' not in session:
            print("User not logged in")
            return jsonify({"loggedIn": False}), 200

        user_id = session['telegram_id']
        print(f"User logged in with ID: {user_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT first_name FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return jsonify({"loggedIn": True, "firstName": row[0]})
        else:
            return jsonify({"loggedIn": True, "firstName": "Unknown"})
    except Exception as e:
        print(f"Error in whoami: {e}")
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500
