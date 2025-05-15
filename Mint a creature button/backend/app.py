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
    """Fetch XRD balance for a Radix account using the Gateway API."""
    if not account_address:
        print("No account address provided")
        return 0
        
    try:
        # XRD resource address
        xrd_resource = 'resource_rdx1tknxxxxxxxxxradxrdxxxxxxxxx009923554798xxxxxxxxxradxrd'
        
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
            return 0
        
        # Parse the JSON response
        data = response.json()
        
        # Print debugging info
        print(f"Gateway API total_count: {data.get('total_count', 0)}")
        
        # Look for the XRD resource in the items
        items = data.get('items', [])
        print(f"Found {len(items)} resources in the account")
        
        # Look for XRD in the account
        for item in items:
            resource_addr = item.get('resource_address', '')
            amount = item.get('amount', '0')
            
            # Check if this is the XRD resource
            if resource_addr == xrd_resource:
                amount_value = float(amount)
                print(f"FOUND XRD RESOURCE: {amount_value}")
                return amount_value
        
        # If we get here, we didn't find XRD
        return 0
    except Exception as e:
        print(f"Error fetching XRD with Gateway API: {e}")
        traceback.print_exc()
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
    Fetch all NFTs of a specific resource type for a user's account.
    Returns: list of non-fungible IDs or empty list if none found
    """
    if not account_address:
        print("No account address provided")
        return []
        
    try:
        # Use the Gateway API to get all non-fungible tokens of this resource
        url = "https://mainnet.radixdlt.com/state/entity/page/non-fungible-vaults/"
        print(f"Fetching NFTs for {account_address} of resource {resource_address}")
        
        # Prepare request payload
        payload = {
            "address": account_address,
            "resource_address": resource_address,
            "opt_ins": {
                "non_fungible_include_nfids": True
            }
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return []
        
        # Parse the JSON response
        data = response.json()
        
        # Get the vault items
        items = data.get('items', [])
        
        if not items:
            return []
            
        # Extract all NFT IDs from all vaults
        nft_ids = []
        for item in items:
            vault_info = item.get('vault', {})
            vault_non_fungibles = vault_info.get('non_fungible_ids', [])
            if vault_non_fungibles:
                nft_ids.extend(vault_non_fungibles)
        
        return nft_ids
    except Exception as e:
        print(f"Error fetching NFTs with Gateway API: {e}")
        traceback.print_exc()
        return []

def fetch_nft_data(resource_address, non_fungible_ids):
    """
    Fetch data for specific non-fungible tokens.
    Returns: dict of NFT ID to data or empty dict if none found
    """
    if not non_fungible_ids:
        return {}
        
    try:
        # Use the Gateway API to get data for specific NFTs
        url = "https://mainnet.radixdlt.com/state/non-fungible/data"
        print(f"Fetching data for {len(non_fungible_ids)} NFTs of resource {resource_address}")
        
        # Prepare request payload
        payload = {
            "resource_address": resource_address,
            "non_fungible_ids": non_fungible_ids[:100]  # API has a limit of 100 NFTs per request
        }
        
        # Set appropriate headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CorvaxLab Game/1.0'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Gateway API error: Status {response.status_code}")
            return {}
        
        # Parse the JSON response
        data = response.json()
        
        # Get the NFT data
        nft_data = {}
        non_fungible_items = data.get('non_fungible_ids', [])
        
        for nft_item in non_fungible_items:
            nft_id = nft_item.get('non_fungible_id')
            nft_data_value = nft_item.get('data', {}).get('programmatic_json')
            if nft_id and nft_data_value:
                nft_data[nft_id] = nft_data_value
        
        return nft_data
    except Exception as e:
        print(f"Error fetching NFT data with Gateway API: {e}")
        traceback.print_exc()
        return {}

def process_creature_data(nft_id, nft_data):
    """Process raw creature NFT data into the expected format for the frontend."""
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
            return processed_data
            
        # Species information
        species_id = nft_data.get("species_id", 1)
        processed_data["species_id"] = species_id
        
        # Get species information
        species_info = SPECIES_DATA.get(species_id, {"name": "Unknown", "preferred_token": "XRD", "rarity": "Common"})
        processed_data["species_name"] = species_info["name"]
        processed_data["rarity"] = species_info["rarity"]
        processed_data["preferred_token"] = species_info["preferred_token"]
        
        # Form and image URL
        form = nft_data.get("form", 0)
        processed_data["form"] = form
        
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
        
        # Stats
        stats = nft_data.get("stats", {})
        if stats:
            processed_data["stats"] = {
                "energy": int(stats.get("energy", 5)),
                "strength": int(stats.get("strength", 5)),
                "magic": int(stats.get("magic", 5)),
                "stamina": int(stats.get("stamina", 5)),
                "speed": int(stats.get("speed", 5))
            }
        
        # Evolution progress
        evolution_progress = nft_data.get("evolution_progress")
        if evolution_progress:
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
            bonus_stats = nft_data.get("bonus_stats", {})
            if bonus_stats:
                processed_data["bonus_stats"] = {k: int(v) for k, v in bonus_stats.items()}
        
        # Generate display stats string
        stats_str = ", ".join([f"{stat.capitalize()}: {value}" for stat, value in processed_data["stats"].items()])
        processed_data["display_stats"] = stats_str
        
        return processed_data
    except Exception as e:
        print(f"Error processing creature data: {e}")
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

@app.route("/api/machines", methods=["GET"])
def get_machines():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Try with provisional_mint and room columns
            cur.execute("""
                SELECT id, machine_type, x, y, level, last_activated, is_offline, provisional_mint, room
                FROM user_machines
                WHERE user_id=?
            """, (user_id,))
            rows = cur.fetchall()
            
            machines = []
            for r in rows:
                machine = dict(r)
                machines.append(machine)
                
        except sqlite3.OperationalError:
            try:
                # Try with provisional_mint only
                cur.execute("""
                    SELECT id, machine_type, x, y, level, last_activated, is_offline, provisional_mint
                    FROM user_machines
                    WHERE user_id=?
                """, (user_id,))
                rows = cur.fetchall()
                
                machines = []
                for r in rows:
                    machine = dict(r)
                    machine["room"] = 1  # Default room
                    machines.append(machine)
            except sqlite3.OperationalError:
                # Fall back to old schema without provisional_mint and room
                cur.execute("""
                    SELECT id, machine_type, x, y, level, last_activated, is_offline
                    FROM user_machines
                    WHERE user_id=?
                """, (user_id,))
                rows = cur.fetchall()
                
                machines = []
                for r in rows:
                    machine = dict(r)
                    machine["provisionalMint"] = 0  # Default value
                    machine["room"] = 1  # Default room
                    machines.append(machine)

        cur.close()
        conn.close()

        # Convert SQLite row objects to proper dictionaries for JSON
        machine_list = []
        for m in machines:
            machine_dict = {
                "id": m["id"],
                "type": m["machine_type"],
                "x": m["x"],
                "y": m["y"],
                "level": m["level"],
                "lastActivated": m["last_activated"],
                "isOffline": m["is_offline"],
                "room": m.get("room", 1)  # Default to room 1 if not present
            }
            
            if "provisional_mint" in m:
                machine_dict["provisionalMint"] = m["provisional_mint"]
            else:
                machine_dict["provisionalMint"] = 0
                
            machine_list.append(machine_dict)

        return jsonify(machine_list)
    except Exception as e:
        print(f"Error in get_machines: {e}")
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

@app.route("/api/resources", methods=["GET"])
def get_resources():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        tcorvax = row["corvax_count"] if row else 0

        catNips = get_or_create_resource(cur, user_id, 'catNips')
        energy = get_or_create_resource(cur, user_id, 'energy')
        eggs = get_or_create_resource(cur, user_id, 'eggs')

        cur.close()
        conn.close()

        return jsonify({
            "tcorvax": float(tcorvax),
            "catNips": float(catNips),
            "energy": float(energy),
            "eggs": float(eggs)
        })
    except Exception as e:
        print(f"Error in get_resources: {e}")
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

def get_or_create_resource(cursor, user_id, resource_name):
    try:
        cursor.execute("SELECT amount FROM resources WHERE user_id=? AND resource_name=?", (user_id, resource_name))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO resources (user_id, resource_name, amount) VALUES (?, ?, 0)",
                        (user_id, resource_name))
            return 0
        else:
            return row[0]
    except Exception as e:
        print(f"Error in get_or_create_resource: {e}")
        traceback.print_exc()
        return 0

def set_resource_amount(cursor, user_id, resource_name, amount):
    try:
        cursor.execute("SELECT amount FROM resources WHERE user_id=? AND resource_name=?", (user_id, resource_name))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO resources (user_id, resource_name, amount) VALUES (?, ?, ?)",
                        (user_id, resource_name, amount))
        else:
            cursor.execute("UPDATE resources SET amount=? WHERE user_id=? AND resource_name=?",
                        (amount, user_id, resource_name))
    except Exception as e:
        print(f"Error in set_resource_amount: {e}")
        traceback.print_exc()

def update_amplifiers_status(user_id, conn, cur):
    try:
        cur.execute("""
            SELECT id, level, is_offline, next_cost_time
            FROM user_machines
            WHERE user_id=? AND machine_type='amplifier'
        """, (user_id,))
        amps = cur.fetchall()
        if not amps:
            return

        now_ms = int(time.time() * 1000)
        energy_val = get_or_create_resource(cur, user_id, 'energy')

        for amp in amps:
            amp_id = amp["id"]
            level = amp["level"]
            is_offline = amp["is_offline"]
            next_cost = amp["next_cost_time"]

            if next_cost == 0:
                next_cost = now_ms + 24*60*60*1000
                cur.execute("""
                    UPDATE user_machines
                    SET next_cost_time=?
                    WHERE user_id=? AND id=?
                """, (next_cost, user_id, amp_id))
                conn.commit()

            cost = 2 * level
            if is_offline == 0:
                while next_cost <= now_ms:
                    if energy_val >= cost:
                        energy_val -= cost
                        set_resource_amount(cur, user_id, 'energy', energy_val)
                        next_cost += 24*60*60*1000
                    else:
                        is_offline = 1
                        cur.execute("""
                            UPDATE user_machines
                            SET is_offline=1
                            WHERE user_id=? AND id=?
                        """, (user_id, amp_id))
                        conn.commit()
                        break
            else:
                if next_cost <= now_ms:
                    if energy_val >= cost:
                        energy_val -= cost
                        set_resource_amount(cur, user_id, 'energy', energy_val)
                        next_cost = now_ms + 24*60*60*1000
                        is_offline = 0
                        cur.execute("""
                            UPDATE user_machines
                            SET is_offline=0, next_cost_time=?
                            WHERE user_id=? AND id=?
                        """, (next_cost, user_id, amp_id))
                        conn.commit()
                    else:
                        pass

            cur.execute("""
                UPDATE user_machines
                SET next_cost_time=?, is_offline=?
                WHERE user_id=? AND id=?
            """, (next_cost, is_offline, user_id, amp_id))
            conn.commit()
    except Exception as e:
        print(f"Error in update_amplifiers_status: {e}")
        traceback.print_exc()
        
@app.route("/api/saveRadixAccount", methods=["POST"])
def save_radix_account():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        account_address = data.get("accountAddress")
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
            
        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update the user record with the Radix account address
        cur.execute("""
            UPDATE users SET radix_account_address = ?
            WHERE user_id = ?
        """, (account_address, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "ok", "message": "Radix account saved"})
    except Exception as e:
        print(f"Error saving Radix account: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
@app.route("/api/getGameState", methods=["GET"])
def get_game_state():
    try:
        print("=== GET GAME STATE CALLED ===")
        if 'telegram_id' not in session:
            print("No telegram_id in session")
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        print(f"Fetching game state for user: {user_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()

        # Try to update amplifier status
        try:
            update_amplifiers_status(user_id, conn, cur)
        except Exception as e:
            print(f"Error updating amplifier status: {e}")
            # Continue anyway

        # Get tcorvax and seen_room_unlock flag
        has_seen_room_column = True
        try:
            cur.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cur.fetchall()]
            has_seen_room_column = 'seen_room_unlock' in columns
        except:
            has_seen_room_column = False
        
        if has_seen_room_column:
            cur.execute("SELECT corvax_count, seen_room_unlock FROM users WHERE user_id=?", (user_id,))
        else:
            cur.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id,))
            
        row = cur.fetchone()
        tcorvax = row["corvax_count"] if row else 0
        seen_room_unlock = row["seen_room_unlock"] if (row and has_seen_room_column) else 0

        # Get other resources
        catNips = get_or_create_resource(cur, user_id, 'catNips')
        energy = get_or_create_resource(cur, user_id, 'energy')
        eggs = get_or_create_resource(cur, user_id, 'eggs')

        # Check if provisional_mint and room columns exist
        has_provisional_mint = True
        has_room_column = True
        try:
            cur.execute("PRAGMA table_info(user_machines)")
            columns = [column[1] for column in cur.fetchall()]
            has_provisional_mint = 'provisional_mint' in columns
            has_room_column = 'room' in columns
        except:
            has_provisional_mint = False
            has_room_column = False
        
        # Get machines with appropriate query
        machines = []
        try:
            if has_provisional_mint and has_room_column:
                print("Querying with provisional_mint and room columns")
                cur.execute("""
                    SELECT id, machine_type, x, y, level, last_activated, is_offline, provisional_mint, room
                    FROM user_machines
                    WHERE user_id=?
                """, (user_id,))
            elif has_provisional_mint:
                print("Querying with provisional_mint column")
                cur.execute("""
                    SELECT id, machine_type, x, y, level, last_activated, is_offline, provisional_mint
                    FROM user_machines
                    WHERE user_id=?
                """, (user_id,))
            else:
                print("Querying without provisional_mint column")
                cur.execute("""
                    SELECT id, machine_type, x, y, level, last_activated, is_offline
                    FROM user_machines
                    WHERE user_id=?
                """, (user_id,))
                
            rows = cur.fetchall()
            for row in rows:
                # Convert SQLite row to Python dict
                machine = dict(row)
                
                # Prepare proper JSON object
                machine_dict = {
                    "id": machine["id"],
                    "type": machine["machine_type"],
                    "x": machine["x"],
                    "y": machine["y"],
                    "level": machine["level"],
                    "lastActivated": machine["last_activated"],
                    "isOffline": machine["is_offline"]
                }
                
                # Add provisional_mint if available
                if "provisional_mint" in machine:
                    machine_dict["provisionalMint"] = machine["provisional_mint"]
                else:
                    machine_dict["provisionalMint"] = 0
                
                # Add room information if available
                if "room" in machine:
                    machine_dict["room"] = machine["room"]
                else:
                    machine_dict["room"] = 1  # Default to room 1
                    
                machines.append(machine_dict)
            
        except Exception as e:
            print(f"Error fetching machines: {e}")
            traceback.print_exc()

        # Get count of machines by type to determine if second room is unlocked
        room_unlocked = 1  # Default to 1 room
        
        # Check machine counts to determine if room 2 is unlocked
        cur.execute("""
            SELECT machine_type, COUNT(*) as count
            FROM user_machines
            WHERE user_id=?
            GROUP BY machine_type
        """, (user_id,))
        
        machine_counts = {}
        for row in cur.fetchall():
            machine_counts[row['machine_type']] = row['count']
        
        # Room 2 unlocks when player has built 2 cat lairs, 2 reactors, and 1 amplifier
        cat_lair_count = machine_counts.get('catLair', 0)
        reactor_count = machine_counts.get('reactor', 0)
        amplifier_count = machine_counts.get('amplifier', 0)
        
        if cat_lair_count >= 2 and reactor_count >= 2 and amplifier_count >= 1:
            room_unlocked = 2

        # Get pets (NEW)
        pets = []
        try:
            cur.execute("""
                SELECT id, x, y, room, type, parent_machine
                FROM pets
                WHERE user_id=?
            """, (user_id,))
            
            rows = cur.fetchall()
            for row in rows:
                pet = {
                    "id": row["id"],
                    "x": row["x"],
                    "y": row["y"],
                    "room": row["room"],
                    "type": row["type"],
                    "parentMachine": row["parent_machine"]
                }
                pets.append(pet)
                
        except Exception as e:
            print(f"Error fetching pets: {e}")
            traceback.print_exc()
        
        cur.close()
        conn.close()
        
        print(f"Returning game state with {len(machines)} machines, {room_unlocked} rooms unlocked, {len(pets)} pets")
        
        # Return with seen_room_unlock and eggs values
        return jsonify({
            "tcorvax": float(tcorvax),
            "catNips": float(catNips),
            "energy": float(energy),
            "eggs": float(eggs),
            "machines": machines,
            "roomsUnlocked": room_unlocked,
            "seenRoomUnlock": seen_room_unlock,
            "pets": pets  # Add pets to the response
        })
        
    except Exception as e:
        print(f"Error in get_game_state: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

def build_cost(machine_type, how_many_already, user_id=None):
    try:
        if machine_type == "catLair":
            if how_many_already == 0:
                return {"tcorvax": 10}
            elif how_many_already == 1:
                return {"tcorvax": 40}
            else:
                return None

        elif machine_type == "reactor":
            if how_many_already == 0:
                return {"tcorvax": 10, "catNips": 10}
            elif how_many_already == 1:
                return {"tcorvax": 40, "catNips": 40}
            elif how_many_already == 2 and user_id is not None:
                # Check if user can build third reactor
                conn = get_db_connection()
                cur = conn.cursor()
                can_build = can_build_third_reactor(cur, user_id)
                cur.close()
                conn.close()
                
                if can_build:
                    return {"tcorvax": 640, "catNips": 640}
                else:
                    return None
            else:
                return None

        elif machine_type == "amplifier":
            if how_many_already == 0:
                return {"tcorvax": 10, "catNips": 10, "energy": 10}
            else:
                return None
                
        elif machine_type == "incubator":
            if how_many_already == 0:
                return {"tcorvax": 320, "catNips": 320, "energy": 320}
            else:
                return None
        
        # Updated FomoHit machine costs
        elif machine_type == "fomoHit":
            if how_many_already == 0:
                return {"tcorvax": 640, "catNips": 640, "energy": 640}  # Updated cost
            else:
                return None

        return None
    except Exception as e:
        print(f"Error in build_cost: {e}")
        traceback.print_exc()
        return None

def is_second_machine(cur, user_id, machine_type, machine_id):
    try:
        cur.execute("""
            SELECT id FROM user_machines
            WHERE user_id=? AND machine_type=?
            ORDER BY id
        """, (user_id, machine_type))
        machine_ids = [row["id"] for row in cur.fetchall()]
        if machine_id not in machine_ids:
            return False
        index = machine_ids.index(machine_id)
        return (index == 1)
    except Exception as e:
        print(f"Error in is_second_machine: {e}")
        traceback.print_exc()
        return False

def are_first_machine_lvl3(cur, user_id, mtype):
    try:
        cur.execute("""
            SELECT level FROM user_machines
            WHERE user_id=? AND machine_type=?
            ORDER BY id
            LIMIT 1
        """, (user_id, mtype))
        r = cur.fetchone()
        if r and r["level"] >= 3:
            return True
        return False
    except Exception as e:
        print(f"Error in are_first_machine_lvl3: {e}")
        traceback.print_exc()
        return False

def are_two_machines_lvl3(cur, user_id, mtype):
    try:
        cur.execute("""
            SELECT level FROM user_machines
            WHERE user_id=? AND machine_type=?
            ORDER BY id
        """, (user_id, mtype))
        rows = cur.fetchall()
        if len(rows) < 2:
            return False
        if rows[0]["level"] >=3 and rows[1]["level"] >=3:
            return True
        return False
    except Exception as e:
        print(f"Error in are_two_machines_lvl3: {e}")
        traceback.print_exc()
        return False

def check_amplifier_gating(cur, user_id, next_level):
    try:
        if next_level == 4:
            if not are_first_machine_lvl3(cur, user_id, "catLair"):
                return False
            if not are_first_machine_lvl3(cur, user_id, "reactor"):
                return False
            return True
        elif next_level == 5:
            if not are_two_machines_lvl3(cur, user_id, "catLair"):
                return False
            if not are_two_machines_lvl3(cur, user_id, "reactor"):
                return False
            return True
        return True
    except Exception as e:
        print(f"Error in check_amplifier_gating: {e}")
        traceback.print_exc()
        return False

def can_build_incubator(cur, user_id):
    try:
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='catLair'
        """, (user_id,))
        total_cat_lairs = cur.fetchone()[0]
        if total_cat_lairs == 0:
            return False
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='catLair' AND level=3
        """, (user_id,))
        max_level_cat_lairs = cur.fetchone()[0]
        if max_level_cat_lairs < total_cat_lairs:
            return False

        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='reactor'
        """, (user_id,))
        total_reactors = cur.fetchone()[0]
        if total_reactors == 0:
            return False
        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='reactor' AND level=3
        """, (user_id,))
        max_level_reactors = cur.fetchone()[0]
        if max_level_reactors < total_reactors:
            return False

        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type='amplifier' AND level=5
        """, (user_id,))
        max_level_amplifier = cur.fetchone()[0]
        if max_level_amplifier == 0:
            return False

        return True
    except Exception as e:
        print(f"Error in can_build_incubator: {e}")
        traceback.print_exc()
        return False

def upgrade_cost(cur, user_id, machine_type, current_level, machine_id):
    try:
        next_level = current_level + 1
        if machine_type in ("catLair","reactor"):
            if next_level > 3:
                return None
        elif machine_type == "amplifier":
            if next_level > 5:
                return None
            if not check_amplifier_gating(cur, user_id, next_level):
                return None
        # Add support for incubator level 2
        elif machine_type == "incubator":
            if next_level > 2:  # Max level 2
                return None
        else:
            return None

        if machine_type == "amplifier":
            if not check_amplifier_gating(cur, user_id, next_level):
                return None

        if machine_type == "catLair":
            base_for_level1 = {"tcorvax": 10}
        elif machine_type == "reactor":
            base_for_level1 = {"tcorvax": 10, "catNips": 10}
        elif machine_type == "amplifier":
            base_for_level1 = {"tcorvax": 10, "catNips": 10, "energy": 10}
        elif machine_type == "incubator":
            # Set base cost for incubator upgrade - note that this is double the original build cost of 320
            # Ensuring frontend and backend match on this value (640)
            base_for_level1 = {"tcorvax": 640, "catNips": 640, "energy": 640}
            # Return cost directly for incubator without additional multipliers
            return base_for_level1
        else:
            return None

        second = is_second_machine(cur, user_id, machine_type, machine_id)
        mult = 2 ** (next_level - 1)
        cost_out = {}
        for res, val in base_for_level1.items():
            c = val * mult
            if second and (machine_type in ["catLair","reactor"]):
                c *= 4
            cost_out[res] = c

        return cost_out
    except Exception as e:
        print(f"Error in upgrade_cost: {e}")
        traceback.print_exc()
        return None

@app.route("/api/dismissRoomUnlock", methods=["POST"])
def dismiss_room_unlock():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        # Update the seen_room_unlock flag
        cur.execute("""
            UPDATE users
            SET seen_room_unlock=1
            WHERE user_id=?
        """, (user_id,))
        
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error in dismiss_room_unlock: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/buildMachine", methods=["POST"])
def build_machine():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        machine_type = data.get("machineType")
        x_coord = data.get("x", 0)
        y_coord = data.get("y", 0)
        room = data.get("room", 1)  # Default to room 1 if not specified
        
        print(f"=== BUILD MACHINE REQUEST ===")
        print(f"Machine type: {machine_type}")
        print(f"Coordinates: x={x_coord}, y={y_coord}")
        print(f"Room: {room}")

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        update_amplifiers_status(user_id, conn, cur)

        cur.execute("""
            SELECT COUNT(*) FROM user_machines
            WHERE user_id=? AND machine_type=?
        """, (user_id, machine_type))
        how_many = cur.fetchone()[0]
        print(f"Existing machines of type {machine_type}: {how_many}")

        cost_dict = build_cost(machine_type, how_many, user_id)
        if cost_dict is None:
            print(f"Cannot build more machines of type {machine_type}")
            cur.close()
            conn.close()
            return jsonify({"error": "Cannot build more of this machine type."}), 400

        # Add special prerequisite checks with detailed logging
        if machine_type == "incubator":
            can_build = can_build_incubator(cur, user_id)
            print(f"Can build incubator check: {can_build}")
            if not can_build:
                cur.close()
                conn.close()
                return jsonify({"error": "All machines must be at max level to build Incubator."}), 400
        
        # Add check for fomoHit prerequisites with simplified requirements
        elif machine_type == "fomoHit":
            print("Checking FOMO HIT prerequisites...")
            
            # Check if user has at least one of each required machine type
            required_types = ['catLair', 'reactor', 'amplifier', 'incubator']
            for req_type in required_types:
                cur.execute("""
                    SELECT COUNT(*) FROM user_machines
                    WHERE user_id=? AND machine_type=?
                """, (user_id, req_type))
                count = cur.fetchone()[0]
                print(f"  - Has {req_type}: {count > 0}")
                if count == 0:
                    cur.close()
                    conn.close()
                    return jsonify({"error": f"Must build {req_type} first."}), 400
                    
            print("All FOMO HIT prerequisites satisfied")
            
        # Add check for third reactor
        elif machine_type == "reactor" and how_many == 2:
            if not can_build_third_reactor(cur, user_id):
                cur.close()
                conn.close()
                return jsonify({"error": "You need to build both Incubator and FOMO HIT before building a third Reactor."}), 400

        # Check resource costs
        cur.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404
            
        tcorvax_val = float(row["corvax_count"])
        catNips_val = float(get_or_create_resource(cur, user_id, 'catNips'))
        energy_val  = float(get_or_create_resource(cur, user_id, 'energy'))
        
        print(f"Resources - TCorvax: {tcorvax_val}, CatNips: {catNips_val}, Energy: {energy_val}")
        print(f"Cost - {cost_dict}")

        if (tcorvax_val < cost_dict.get("tcorvax",0) or
            catNips_val < cost_dict.get("catNips",0) or
            energy_val < cost_dict.get("energy",0)):
            print("Not enough resources")
            cur.close()
            conn.close()
            return jsonify({"error": "Not enough resources"}), 400

        machine_size = 128
        max_x = 800 - machine_size
        max_y = 600 - machine_size
        if x_coord < 0 or x_coord > max_x or y_coord < 0 or y_coord > max_y:
            cur.close()
            conn.close()
            return jsonify({"error": "Cannot build outside map boundaries."}), 400

        # Check for collision with other machines IN THE SAME ROOM
        cur.execute("SELECT x, y, room FROM user_machines WHERE user_id=?", (user_id,))
        all_m = cur.fetchall()
        for m in all_m:
            # Only check collision if in the same room
            if m["room"] == room:
                dx = abs(m["x"] - x_coord)
                dy = abs(m["y"] - y_coord)
                if dx < machine_size and dy < machine_size:
                    cur.close()
                    conn.close()
                    return jsonify({"error": "Cannot build here!"}), 400

        tcorvax_val -= cost_dict.get("tcorvax",0)
        catNips_val -= cost_dict.get("catNips",0)
        energy_val  -= cost_dict.get("energy",0)

        cur.execute("""
            UPDATE users SET corvax_count=?
            WHERE user_id=?
        """, (tcorvax_val, user_id))
        set_resource_amount(cur, user_id, 'catNips', catNips_val)
        set_resource_amount(cur, user_id, 'energy', energy_val)

        is_offline = 1 if machine_type == "incubator" else 0
        
        # Check if both provisional_mint and room columns exist
        has_provisional_mint = True
        has_room_column = True
        try:
            cur.execute("PRAGMA table_info(user_machines)")
            columns = [column[1] for column in cursor.fetchall()]
            has_provisional_mint = 'provisional_mint' in columns
            has_room_column = 'room' in columns
        except:
            has_provisional_mint = False
            has_room_column = False
            
        # Insert with appropriate columns
        if has_provisional_mint and has_room_column:
            cur.execute("""
                INSERT INTO user_machines
                (user_id, machine_type, x, y, level, last_activated, is_offline, next_cost_time, provisional_mint, room)
                VALUES (?, ?, ?, ?, 1, 0, ?, 0, 0, ?)
            """, (user_id, machine_type, x_coord, y_coord, is_offline, room))
        elif has_provisional_mint:
            cur.execute("""
                INSERT INTO user_machines
                (user_id, machine_type, x, y, level, last_activated, is_offline, next_cost_time, provisional_mint)
                VALUES (?, ?, ?, ?, 1, 0, ?, 0, 0)
            """, (user_id, machine_type, x_coord, y_coord, is_offline))
        else:
            cur.execute("""
                INSERT INTO user_machines
                (user_id, machine_type, x, y, level, last_activated, is_offline, next_cost_time)
                VALUES (?, ?, ?, ?, 1, 0, ?, 0)
            """, (user_id, machine_type, x_coord, y_coord, is_offline))

        conn.commit()
        
        # Check if room 2 is newly unlocked
        room_unlocked = 1
        
        # Count machines by type
        cur.execute("""
            SELECT machine_type, COUNT(*) as count
            FROM user_machines
            WHERE user_id=?
            GROUP BY machine_type
        """, (user_id,))
        
        machine_counts = {}
        for row in cur.fetchall():
            machine_counts[row['machine_type']] = row['count']
        
        # Room 2 unlocks when player has built 2 cat lairs, 2 reactors, and 1 amplifier
        cat_lair_count = machine_counts.get('catLair', 0)
        reactor_count = machine_counts.get('reactor', 0)
        amplifier_count = machine_counts.get('amplifier', 0)
        
        if cat_lair_count >= 2 and reactor_count >= 2 and amplifier_count >= 1:
            room_unlocked = 2
            
        print(f"Machine built successfully, rooms unlocked: {room_unlocked}")
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "machineType": machine_type,
            "newResources": {
                "tcorvax": tcorvax_val,
                "catNips": catNips_val,
                "energy": energy_val
            },
            "roomsUnlocked": room_unlocked
        })
    except Exception as e:
        print(f"Error in build_machine: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/moveMachine", methods=["POST"])
def move_machine():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        machine_id = data.get("machineId")
        new_x = data.get("x", 0)
        new_y = data.get("y", 0)
        new_room = data.get("room", 1)  # Default to room 1 if not specified
        
        if not machine_id:
            return jsonify({"error": "Missing machineId"}), 400

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        # Verify the machine exists and belongs to the user
        cur.execute("""
            SELECT id, machine_type, room FROM user_machines
            WHERE user_id=? AND id=?
        """, (user_id, machine_id))
        
        machine = cur.fetchone()
        if not machine:
            cur.close()
            conn.close()
            return jsonify({"error": "Machine not found"}), 404
        
        # Check if user has enough TCorvax (50)
        movement_cost = 50
        
        cur.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404
            
        tcorvax_val = float(row["corvax_count"])
        
        if tcorvax_val < movement_cost:
            cur.close()
            conn.close()
            return jsonify({"error": "Not enough TCorvax (50 required)"}), 400

        # Validate the new position
        machine_size = 128
        max_x = 800 - machine_size
        max_y = 600 - machine_size
        
        if new_x < 0 or new_x > max_x or new_y < 0 or new_y > max_y:
            cur.close()
            conn.close()
            return jsonify({"error": "Cannot move outside map boundaries."}), 400

        # Check for collision with other machines IN THE SAME ROOM
        cur.execute("SELECT id, x, y, room FROM user_machines WHERE user_id=? AND id != ?", 
                  (user_id, machine_id))
        
        other_machines = cur.fetchall()
        for m in other_machines:
            # Only check collision if in the same room
            if m["room"] == new_room:
                dx = abs(m["x"] - new_x)
                dy = abs(m["y"] - new_y)
                if dx < machine_size and dy < machine_size:
                    cur.close()
                    conn.close()
                    return jsonify({"error": "Cannot move here due to collision with another machine!"}), 400

        # Deduct TCorvax cost
        tcorvax_val -= movement_cost
        cur.execute("""
            UPDATE users
            SET corvax_count=?
            WHERE user_id=?
        """, (tcorvax_val, user_id))

        # Update machine position and room
        cur.execute("""
            UPDATE user_machines
            SET x=?, y=?, room=?
            WHERE user_id=? AND id=?
        """, (new_x, new_y, new_room, user_id, machine_id))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "machineId": machine_id,
            "newPosition": {
                "x": new_x,
                "y": new_y,
                "room": new_room
            },
            "newResources": {
                "tcorvax": tcorvax_val
            }
        })
    except Exception as e:
        print(f"Error in move_machine: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/upgradeMachine", methods=["POST"])
def upgrade_machine():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        machine_id = data.get("machineId")
        if not machine_id:
            return jsonify({"error": "Missing machineId"}), 400

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        update_amplifiers_status(user_id, conn, cur)

        cur.execute("""
            SELECT id, machine_type, level
            FROM user_machines
            WHERE user_id=? AND id=?
        """, (user_id, machine_id))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Machine not found"}), 404

        machine_type = row["machine_type"]
        current_level = row["level"]

        cost_dict = upgrade_cost(cur, user_id, machine_type, current_level, machine_id)
        if cost_dict is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Cannot upgrade further or gating not met."}), 400

        cur.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id,))
        urow = cur.fetchone()
        if not urow:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404

        tcorvax_val = float(urow["corvax_count"])
        catNips_val = float(get_or_create_resource(cur, user_id, 'catNips'))
        energy_val  = float(get_or_create_resource(cur, user_id, 'energy'))

        if (tcorvax_val < cost_dict.get("tcorvax",0) or
            catNips_val < cost_dict.get("catNips",0) or
            energy_val < cost_dict.get("energy",0)):
            cur.close()
            conn.close()
            return jsonify({"error": "Not enough resources"}), 400

        new_level = current_level + 1
        cur.execute("""
            UPDATE user_machines
            SET level=?
            WHERE user_id=? AND id=?
        """, (new_level, user_id, machine_id))

        tcorvax_val -= cost_dict.get("tcorvax",0)
        catNips_val -= cost_dict.get("catNips",0)
        energy_val  -= cost_dict.get("energy",0)

        cur.execute("""
            UPDATE users
            SET corvax_count=?
            WHERE user_id=?
        """, (tcorvax_val, user_id))
        set_resource_amount(cur, user_id, 'catNips', catNips_val)
        set_resource_amount(cur, user_id, 'energy', energy_val)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "machineId": machine_id,
            "newLevel": new_level,
            "newResources": {
                "tcorvax": tcorvax_val,
                "catNips": catNips_val,
                "energy": energy_val
            }
        })
    except Exception as e:
        print(f"Error in upgrade_machine: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/checkMintStatus", methods=["POST"])
def check_mint_status():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401
            
        data = request.json or {}
        intent_hash = data.get("intentHash")
        machine_id = data.get("machineId")
        
        if not intent_hash or not machine_id:
            return jsonify({"error": "Missing intentHash or machineId"}), 400
            
        # Get the transaction status
        status_data = get_transaction_status(intent_hash)
        
        # If the transaction is committed successfully, update the machine
        if status_data.get("status") == "CommittedSuccess":
            user_id = session['telegram_id']
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if provisional_mint column exists
            has_provisional_mint = True
            try:
                cur.execute("PRAGMA table_info(user_machines)")
                columns = [column[1] for column in cur.fetchall()]
                has_provisional_mint = 'provisional_mint' in columns
            except:
                has_provisional_mint = False
                
            if has_provisional_mint:
                try:
                    # Update the machine to show successful mint
                    cur.execute("""
                        UPDATE user_machines
                        SET provisional_mint=0
                        WHERE user_id=? AND id=?
                    """, (user_id, machine_id))
                    conn.commit()
                except Exception as e:
                    print(f"Error updating provisional_mint: {e}")
            
            cur.close()
            conn.close()
            
        return jsonify({
            "status": "ok",
            "transactionStatus": status_data
        })
    except Exception as e:
        print(f"Error in check_mint_status: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/activateMachine", methods=["POST"])
def activate_machine():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        # Log the incoming request for debugging
        print(f"=== ACTIVATE MACHINE REQUEST ===")
        try:
            data = request.get_json(silent=True) or {}
            print(f"Request data: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"Error parsing request JSON: {e}")
            data = request.form or {}
            print(f"Form data: {data}")
            
        machine_id = data.get("machineId")
        if machine_id is None:
            return jsonify({"error": "Missing machineId"}), 400

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        update_amplifiers_status(user_id, conn, cur)

        # Check if the provisional_mint column exists
        has_provisional_mint = True
        try:
            cur.execute("PRAGMA table_info(user_machines)")
            columns = [column[1] for column in cur.fetchall()]
            has_provisional_mint = 'provisional_mint' in columns
        except:
            has_provisional_mint = False
            
        # Build the query based on column existence
        if has_provisional_mint:
            query = """
                SELECT machine_type, level, last_activated, is_offline, provisional_mint, room
                FROM user_machines
                WHERE user_id=? AND id=?
            """
        else:
            query = """
                SELECT machine_type, level, last_activated, is_offline, room
                FROM user_machines
                WHERE user_id=? AND id=?
            """
            
        cur.execute(query, (user_id, machine_id))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Machine not found"}), 404

        # Convert row to dictionary to avoid sqlite3.Row.get() issue
        machine_data = dict(row)
        
        machine_type = machine_data["machine_type"]
        machine_level = machine_data["level"]
        last_activated = machine_data["last_activated"] or 0
        is_offline = machine_data["is_offline"]
        provisional_mint = machine_data.get("provisional_mint", 0) if has_provisional_mint else 0
        room = machine_data.get("room", 1)  # Default to room 1 if not present

        COOL_MS = 3600*1000
        now_ms = int(time.time()*1000)
        elapsed = now_ms - last_activated
        if elapsed < COOL_MS:
            remain = COOL_MS - elapsed
            cur.close()
            conn.close()
            return jsonify({"error":"Cooldown not finished","remainingMs":remain}), 400

        cur.execute("SELECT corvax_count FROM users WHERE user_id=?", (user_id,))
        urow = cur.fetchone()
        if not urow:
            cur.close()
            conn.close()
            return jsonify({"error":"User not found"}), 404

        tcorvax_val = float(urow["corvax_count"])
        catNips_val = float(get_or_create_resource(cur, user_id, 'catNips'))
        energy_val = float(get_or_create_resource(cur, user_id, 'energy'))
        eggs_val = float(get_or_create_resource(cur, user_id, 'eggs'))

        if machine_type == "amplifier":
            status = "Online" if is_offline==0 else "Offline"
            cur.close()
            conn.close()
            return jsonify({"status":"ok","message":status})

        if machine_type == "incubator":
            if last_activated == 0:
                print("First incubator activation - setting online and checking sCVX rewards")
                
                # Get account address from request
                account_address = data.get("accountAddress")
                print(f"Got account address from request: {account_address}")
                
                # Ensure we have an account address
                if not account_address:
                    print("No account address provided for sCVX lookup")
                    staked_cvx = 0
                else:
                    print(f"Fetching sCVX for account: {account_address}")
                    # Use the server-side fetch function
                    staked_cvx = fetch_scvx_balance(account_address)
                    
                print(f"Final sCVX value: {staked_cvx}")
                
                # Calculate rewards based on level
                machine_level = machine_level or 1
                
                # Base reward (level 1): 1 token per 100 sCVX, max 10
                base_reward = min(10, int(staked_cvx // 100))
                
                # Bonus reward (level 2): additional 1 token per 1000 sCVX, no max
                bonus_reward = 0
                if machine_level >= 2:
                    bonus_reward = int(staked_cvx // 1000)
                
                total_reward = base_reward + bonus_reward
                
                # Award eggs (1 egg per 500 sCVX)
                eggs_reward = int(staked_cvx // 500)
                
                # Update resources
                tcorvax_val += total_reward
                eggs_val += eggs_reward
                
                print(f"sCVX rewards calculated: Base {base_reward}, Bonus {bonus_reward}, Eggs {eggs_reward}")

                # Update user's resources
                cur.execute("""
                    UPDATE users
                    SET corvax_count=?
                    WHERE user_id=?
                """, (tcorvax_val, user_id))
                
                # Update eggs resource
                set_resource_amount(cur, user_id, 'eggs', eggs_val)

                # Set incubator to online and update activation time
                cur.execute("""
                    UPDATE user_machines
                    SET is_offline=0, last_activated=?
                    WHERE user_id=? AND id=?
                """, (now_ms, user_id, machine_id))

                conn.commit()
                cur.close()
                conn.close()

                # Return detailed response with rewards
                return jsonify({
                    "status": "ok",
                    "machineId": machine_id,
                    "machineType": machine_type,
                    "newLastActivated": now_ms,
                    "stakedCVX": staked_cvx,
                    "baseReward": base_reward,
                    "bonusReward": bonus_reward,
                    "eggsReward": eggs_reward,
                    "updatedResources": {
                        "tcorvax": tcorvax_val,
                        "catNips": catNips_val,
                        "energy": energy_val,
                        "eggs": eggs_val
                    }
                })
            else:
                # Get account address from request
                account_address = data.get("accountAddress")
                print(f"Got account address from request: {account_address}")
                
                # Ensure we have an account address
                if not account_address:
                    print("No account address provided for sCVX lookup")
                    staked_cvx = 0
                else:
                    print(f"Fetching sCVX for account: {account_address}")
                    # Use the server-side fetch function
                    staked_cvx = fetch_scvx_balance(account_address)
                    
                print(f"Final sCVX value: {staked_cvx}")
                
                # Calculate rewards based on level
                machine_level = machine_level or 1
                
                # Base reward (level 1): 1 token per 100 sCVX, max 10
                base_reward = min(10, int(staked_cvx // 100))
                
                # Bonus reward (level 2): additional 1 token per 1000 sCVX, no max
                bonus_reward = 0
                if machine_level >= 2:
                    bonus_reward = int(staked_cvx // 1000)
                
                total_reward = base_reward + bonus_reward
                
                # Award eggs (1 egg per 500 sCVX)
                eggs_reward = int(staked_cvx // 500)
                
                # Update resources
                tcorvax_val += total_reward
                eggs_val += eggs_reward
                
                print(f"sCVX rewards calculated: Base {base_reward}, Bonus {bonus_reward}, Eggs {eggs_reward}")

                cur.execute("""
                    UPDATE users
                    SET corvax_count=?
                    WHERE user_id=?
                """, (tcorvax_val, user_id))
                
                # Update eggs resource
                set_resource_amount(cur, user_id, 'eggs', eggs_val)

                cur.execute("""
                    UPDATE user_machines
                    SET last_activated=?
                    WHERE user_id=? AND id=?
                """, (now_ms, user_id, machine_id))

                conn.commit()
                cur.close()
                conn.close()

                return jsonify({
                    "status": "ok",
                    "machineId": machine_id,
                    "machineType": machine_type,
                    "newLastActivated": now_ms,
                    "stakedCVX": staked_cvx,
                    "baseReward": base_reward,
                    "bonusReward": bonus_reward,
                    "eggsReward": eggs_reward,
                    "updatedResources": {
                        "tcorvax": tcorvax_val,
                        "catNips": catNips_val,
                        "energy": energy_val,
                        "eggs": eggs_val
                    }
                })
        
        elif machine_type == "fomoHit":
            print(f"Handling FOMO HIT activation for machine ID: {machine_id}")
            
            # First activation - mint NFT
            if last_activated == 0:
                # Get account address from request
                account_address = data.get("accountAddress")
                print(f"Got account address for NFT mint: {account_address}")
                
                # Ensure we have an account address
                if not account_address:
                    print("No account address provided for NFT mint")
                    cur.close()
                    conn.close()
                    return jsonify({"error": "No wallet address provided"}), 400
                    
                # Create the mint manifest
                mint_manifest = create_nft_mint_manifest(account_address)
                print(f"Created mint manifest")
                
                # Set provisional mint status if the column exists
                if has_provisional_mint:
                    try:
                        cur.execute("""
                            UPDATE user_machines
                            SET provisional_mint=1
                            WHERE user_id=? AND id=?
                        """, (user_id, machine_id))
                    except sqlite3.OperationalError:
                        print("Could not update provisional_mint (column missing)")
                
                # Store current time as activation time
                cur.execute("""
                    UPDATE user_machines
                    SET last_activated=?
                    WHERE user_id=? AND id=?
                """, (now_ms, user_id, machine_id))
                
                conn.commit()
                
                # Return the mint manifest for the frontend to process
                cur.close()
                conn.close()
                return jsonify({
                    "status": "ok",
                    "requiresMint": True,
                    "machineId": machine_id,
                    "machineType": machine_type,
                    "manifest": mint_manifest,
                    "newLastActivated": now_ms
                })
            else:
                # Subsequent activations - produce TCorvax
                reward = 5  # Produces 5 TCorvax on subsequent activations
                tcorvax_val += reward
                
                # Update resources
                cur.execute("""
                    UPDATE users
                    SET corvax_count=?
                    WHERE user_id=?
                """, (tcorvax_val, user_id))
                
                # Update activation time
                cur.execute("""
                    UPDATE user_machines
                    SET last_activated=?
                    WHERE user_id=? AND id=?
                """, (now_ms, user_id, machine_id))
                
                conn.commit()
                cur.close()
                conn.close()
                
                return jsonify({
                    "status": "ok",
                    "machineId": machine_id,
                    "machineType": machine_type,
                    "newLastActivated": now_ms,
                    "reward": reward,
                    "updatedResources": {
                        "tcorvax": tcorvax_val,
                        "catNips": catNips_val,
                        "energy": energy_val,
                        "eggs": eggs_val
                    }
                })

        if machine_type == "catLair":
            gained = 5 + (machine_level - 1)
            catNips_val += gained
        elif machine_type == "reactor":
            if catNips_val < 3:
                cur.close()
                conn.close()
                return jsonify({"error":"Not enough Cat Nips to run the Reactor!"}), 400
            catNips_val -= 3
            if machine_level == 1:
                base_t = 1.0
            elif machine_level == 2:
                base_t = 1.5
            elif machine_level == 3:
                base_t = 2.0
            else:
                base_t = 1.0

            cur.execute("""
                SELECT level, is_offline
                FROM user_machines
                WHERE user_id=? AND machine_type='amplifier'
            """,(user_id,))
            amp = cur.fetchone()
            if amp and amp["is_offline"] == 0:
                amp_level = amp["level"]
                base_t += 0.5 * amp_level

            base_e = 2
            tcorvax_val += base_t
            energy_val  += base_e

        cur.execute("""
            UPDATE user_machines
            SET last_activated=?
            WHERE user_id=? AND id=?
        """,(now_ms,user_id,machine_id))

        cur.execute("""
            UPDATE users
            SET corvax_count=?
            WHERE user_id=?
        """,(tcorvax_val,user_id))
        set_resource_amount(cur, user_id,'catNips',catNips_val)
        set_resource_amount(cur, user_id,'energy', energy_val)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status":"ok",
            "machineId":machine_id,
            "machineType":machine_type,
            "newLastActivated":now_ms,
            "updatedResources":{
                "tcorvax": tcorvax_val,
                "catNips": catNips_val,
                "energy": energy_val,
                "eggs": eggs_val
            }
        })
    except Exception as e:
        print(f"Error in activate_machine: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getPets", methods=["GET"])
def get_pets():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, x, y, room, type, parent_machine
            FROM pets
            WHERE user_id=?
        """, (user_id,))
        
        rows = cur.fetchall()
        pets = []
        
        for row in rows:
            pet = {
                "id": row["id"],
                "x": row["x"],
                "y": row["y"],
                "room": row["room"],
                "type": row["type"],
                "parentMachine": row["parent_machine"]
            }
            pets.append(pet)

        cur.close()
        conn.close()

        return jsonify(pets)
    except Exception as e:
        print(f"Error in get_pets: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/buyPet", methods=["POST"])
def buy_pet():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        pet_type = data.get("petType", "cat")
        x_coord = data.get("x", 0)
        y_coord = data.get("y", 0)
        room = data.get("room", 1)
        parent_machine = data.get("parentMachine")
        
        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if user already has a pet of this type
        cur.execute("""
            SELECT COUNT(*) FROM pets
            WHERE user_id=? AND type=?
        """, (user_id, pet_type))
        
        pet_count = cur.fetchone()[0]
        
        # Currently only allow one pet per type
        if pet_count > 0:
            cur.close()
            conn.close()
            return jsonify({"error": "You already have this type of pet"}), 400

        # Check if user has enough catnips
        catNips_val = float(get_or_create_resource(cur, user_id, 'catNips'))
        
        if catNips_val < 1500:
            cur.close()
            conn.close()
            return jsonify({"error": "Not enough Cat Nips (1500 required)"}), 400

        # Deduct catnips
        catNips_val -= 1500
        set_resource_amount(cur, user_id, 'catNips', catNips_val)

        # Create the pet
        cur.execute("""
            INSERT INTO pets (user_id, x, y, room, type, parent_machine)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, x_coord, y_coord, room, pet_type, parent_machine))

        pet_id = cur.lastrowid
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "petId": pet_id,
            "petType": pet_type,
            "position": {
                "x": x_coord,
                "y": y_coord,
                "room": room
            },
            "newResources": {
                "catNips": catNips_val
            }
        })
    except Exception as e:
        print(f"Error in buy_pet: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/movePet", methods=["POST"])
def move_pet():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        pet_id = data.get("petId")
        new_x = data.get("x", 0)
        new_y = data.get("y", 0)
        new_room = data.get("room", 1)
        
        if not pet_id:
            return jsonify({"error": "Missing petId"}), 400

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        # Verify the pet exists and belongs to the user
        cur.execute("""
            SELECT id FROM pets
            WHERE user_id=? AND id=?
        """, (user_id, pet_id))
        
        pet = cur.fetchone()
        if not pet:
            cur.close()
            conn.close()
            return jsonify({"error": "Pet not found"}), 404

        # Update pet position
        cur.execute("""
            UPDATE pets
            SET x=?, y=?, room=?
            WHERE user_id=? AND id=?
        """, (new_x, new_y, new_room, user_id, pet_id))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "petId": pet_id,
            "newPosition": {
                "x": new_x,
                "y": new_y,
                "room": new_room
            }
        })
    except Exception as e:
        print(f"Error in move_pet: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/buyEnergy", methods=["POST"])
def buy_energy():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401
        user_id = session['telegram_id']
        data = request.json or {}
        account_address = data.get("accountAddress")
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        print(f"Generating energy purchase manifest for account: {account_address}")    
        # Create transaction manifest for buying energy
        manifest = create_buy_energy_manifest(account_address)
        
        if manifest is None:
            return jsonify({"error": "Failed to create transaction manifest"}), 500
        
        print(f"Returning manifest: {manifest}")    
        return jsonify({
            "status": "ok",
            "manifest": manifest,
            "energyAmount": 500,
            "cvxCost": 200.0,  # Update this value to 200
            "message": "Please ensure you have at least 200.0 CVX plus transaction fees in your wallet"
        })
    except Exception as e:
        print(f"Error in buy_energy: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/confirmEnergyPurchase", methods=["POST"])
def confirm_energy_purchase():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        data = request.json or {}
        intent_hash = data.get("intentHash")
        
        if not intent_hash:
            return jsonify({"error": "Missing transaction intent hash"}), 400
            
        # Get transaction status
        status_data = get_transaction_status(intent_hash)
        
        # If transaction is committed successfully, add energy
        if status_data.get("status") == "CommittedSuccess":
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get current energy
            energy_val = float(get_or_create_resource(cur, user_id, 'energy'))
            
            # Add 500 energy
            energy_val += 500
            
            # Update energy resource
            set_resource_amount(cur, user_id, 'energy', energy_val)
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                "status": "ok", 
                "transactionStatus": status_data,
                "newEnergy": energy_val
            })
        
        # Return transaction status even if not successful
        return jsonify({
            "status": "pending",
            "transactionStatus": status_data
        })
    except Exception as e:
        print(f"Error in confirm_energy_purchase: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/syncLayout", methods=["POST"])
def sync_layout():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error":"Not logged in"}), 401

        data = request.json or {}
        machine_list = data.get("machines", [])

        user_id = session['telegram_id']
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if room column exists
        has_room_column = True
        try:
            cur.execute("PRAGMA table_info(user_machines)")
            columns = [column[1] for column in cur.fetchall()]
            has_room_column = 'room' in columns
        except:
            has_room_column = False

        for m in machine_list:
            mid = m.get("id")
            mx = m.get("x", 0)
            my = m.get("y", 0)
            mroom = m.get("room", 1)  # Default to room 1
            
            if has_room_column:
                cur.execute("""
                    UPDATE user_machines
                    SET x=?, y=?, room=?
                    WHERE user_id=? AND id=?
                """, (mx, my, mroom, user_id, mid))
            else:
                cur.execute("""
                    UPDATE user_machines
                    SET x=?, y=?
                    WHERE user_id=? AND id=?
                """, (mx, my, user_id, mid))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status":"ok","message":"Layout updated"})
    except Exception as e:
        print(f"Error in sync_layout: {e}")
        traceback.print_exc() 
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# New endpoints for Evolving Creatures

@app.route("/api/checkXrdBalance", methods=["POST"])
def check_xrd_balance():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        account_address = data.get("accountAddress")
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        print(f"Checking XRD balance for account: {account_address}")
        
        # Fetch XRD balance using the Gateway API
        xrd_balance = fetch_xrd_balance(account_address)
        
        # Check if the user has enough XRD (250 XRD required for minting)
        has_enough_xrd = xrd_balance >= 250
        
        return jsonify({
            "status": "ok",
            "xrdBalance": xrd_balance,
            "hasEnoughXrd": has_enough_xrd
        })
    except Exception as e:
        print(f"Error checking XRD balance: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getCreatureMintManifest", methods=["POST"])
def get_creature_mint_manifest():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        account_address = data.get("accountAddress")
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        print(f"Generating evolving creature mint manifest for account: {account_address}")
        
        # Create transaction manifest for minting an evolving creature egg
        manifest = create_evolving_creature_manifest(account_address)
        
        if manifest is None:
            return jsonify({"error": "Failed to create transaction manifest"}), 500
        
        return jsonify({
            "status": "ok",
            "manifest": manifest,
            "price": 250.0,  # XRD cost
            "message": "Please ensure you have at least 250.0 XRD plus transaction fees in your wallet"
        })
    except Exception as e:
        print(f"Error creating creature mint manifest: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/checkCreatureMintStatus", methods=["POST"])
def check_creature_mint_status():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        intent_hash = data.get("intentHash")
        
        if not intent_hash:
            return jsonify({"error": "Missing transaction intent hash"}), 400
        
        # Get transaction status
        status_data = get_transaction_status(intent_hash)
        
        # If transaction is committed successfully, try to get NFT details
        creature_nft = None
        bonus_item = None
        
        if status_data.get("status") == "CommittedSuccess":
            # Try to get NFT details from the transaction
            creature_nft, bonus_item = get_minted_nfts_from_transaction(intent_hash)
            
            # If we couldn't get the actual NFTs, create placeholder data
            if not creature_nft:
                creature_nft = {
                    "id": f"simulated_{uuid.uuid4().hex[:8]}",
                    "species_name": "Mystery Creature",
                    "rarity": "Unknown",
                    "image_url": "https://cvxlab.net/assets/evolving_creatures/bullx_egg.png"
                }
            
            if not bonus_item:
                bonus_item = {
                    "id": f"simulated_{uuid.uuid4().hex[:8]}",
                    "name": "Mystery Tool",
                    "type": "tool",
                    "image_url": "https://cvxlab.net/assets/tools/babylon_keystone.png"
                }
        
        return jsonify({
            "status": "ok",
            "transactionStatus": status_data,
            "creatureNft": creature_nft,
            "bonusItem": bonus_item
        })
    except Exception as e:
        print(f"Error checking creature mint status: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getUserCreatures", methods=["GET", "POST"])
def get_user_creatures():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['telegram_id']
        
        # Get account address - prioritize different sources
        account_address = None
        
        # 1. First try request body (POST)
        if request.method == "POST" and request.json:
            account_address = request.json.get("accountAddress")
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
        
        # Fetch NFT IDs owned by this account
        print(f"Fetching creature NFTs for account: {account_address}")
        nft_ids = fetch_user_nfts(account_address, CREATURE_NFT_RESOURCE)
        
        if not nft_ids:
            print(f"No creature NFTs found for account {account_address}")
            return jsonify({"creatures": []})
            
        print(f"Found {len(nft_ids)} creature NFTs for account {account_address}")
        
        # Fetch NFT data for all IDs
        # We may need to batch this if there are many NFTs
        batch_size = 50  # Gateway API typically limits to 100, using 50 to be safe
        all_creatures = []
        
        for i in range(0, len(nft_ids), batch_size):
            batch_ids = nft_ids[i:i+batch_size]
            nft_data_map = fetch_nft_data(CREATURE_NFT_RESOURCE, batch_ids)
            
            if not nft_data_map:
                continue
                
            # Process each creature's data
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
        
        return jsonify({"creatures": all_creatures})
    except Exception as e:
        print(f"Error in get_user_creatures: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getUpgradeStatsManifest", methods=["POST"])
def get_upgrade_stats_manifest():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        account_address = data.get("accountAddress")
        creature_id = data.get("creatureId")
        energy = int(data.get("energy", 0))
        strength = int(data.get("strength", 0))
        magic = int(data.get("magic", 0))
        stamina = int(data.get("stamina", 0))
        speed = int(data.get("speed", 0))
        
        # Additional data for calculating cost
        creature_data = data.get("creatureData", {})
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        if not creature_id:
            return jsonify({"error": "No creature ID provided"}), 400
        
        # Calculate cost based on creature data
        # In a full implementation, we'd lookup the creature's data in the blockchain
        # and calculate the cost based on that
        
        # For now, use the provided creature data
        cost = calculate_upgrade_cost(creature_data, energy, strength, magic, stamina, speed)
        
        # Get token resource address
        token_symbol = cost.get("token", "XRD")
        token_amount = cost.get("amount", 0)
        token_resource = TOKEN_ADDRESSES.get(token_symbol, TOKEN_ADDRESSES["XRD"])
        
        # Create the manifest
        manifest = create_upgrade_stats_manifest(
            account_address, 
            creature_id, 
            energy, 
            strength, 
            magic, 
            stamina, 
            speed, 
            token_resource, 
            token_amount
        )
        
        if not manifest:
            return jsonify({"error": "Failed to create transaction manifest"}), 500
        
        return jsonify({
            "status": "ok",
            "manifest": manifest,
            "cost": {
                "token": token_symbol,
                "amount": token_amount
            }
        })
    except Exception as e:
        print(f"Error in get_upgrade_stats_manifest: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getEvolveManifest", methods=["POST"])
def get_evolve_manifest():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        account_address = data.get("accountAddress")
        creature_id = data.get("creatureId")
        creature_data = data.get("creatureData", {})
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        if not creature_id:
            return jsonify({"error": "No creature ID provided"}), 400
        
        # Calculate evolution cost
        evolution_cost = calculate_evolution_cost(creature_data)
        
        if not evolution_cost.get("can_evolve", False):
            reason = evolution_cost.get("reason", "Cannot evolve at this time")
            return jsonify({"error": reason}), 400
        
        # Get token details
        token_symbol = evolution_cost.get("token", "XRD")
        token_amount = evolution_cost.get("amount", 0)
        token_resource = TOKEN_ADDRESSES.get(token_symbol, TOKEN_ADDRESSES["XRD"])
        
        # Create the manifest
        manifest = create_evolve_manifest(
            account_address,
            creature_id,
            token_resource,
            token_amount
        )
        
        if not manifest:
            return jsonify({"error": "Failed to create transaction manifest"}), 500
        
        return jsonify({
            "status": "ok",
            "manifest": manifest,
            "cost": {
                "token": token_symbol,
                "amount": token_amount
            }
        })
    except Exception as e:
        print(f"Error in get_evolve_manifest: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getLevelUpStatsManifest", methods=["POST"])
def get_level_up_stats_manifest():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        account_address = data.get("accountAddress")
        creature_id = data.get("creatureId")
        energy = int(data.get("energy", 0))
        strength = int(data.get("strength", 0))
        magic = int(data.get("magic", 0))
        stamina = int(data.get("stamina", 0))
        speed = int(data.get("speed", 0))
        creature_data = data.get("creatureData", {})
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        if not creature_id:
            return jsonify({"error": "No creature ID provided"}), 400
        
        # Check that the creature is form 3
        form = creature_data.get("form", 0)
        if form != 3:
            return jsonify({"error": "Only Form 3 creatures can level up stats"}), 400
        
        # Check that the creature hasn't exceeded max upgrades
        final_form_upgrades = creature_data.get("final_form_upgrades", 0)
        if final_form_upgrades >= 3:
            return jsonify({"error": "Creature has already reached maximum level ups"}), 400
        
        # Calculate cost
        cost = calculate_upgrade_cost(creature_data, energy, strength, magic, stamina, speed)
        
        # Get token resource address
        token_symbol = cost.get("token", "XRD")
        token_amount = cost.get("amount", 0)
        token_resource = TOKEN_ADDRESSES.get(token_symbol, TOKEN_ADDRESSES["XRD"])
        
        # Create the manifest
        manifest = create_level_up_manifest(
            account_address, 
            creature_id, 
            energy, 
            strength, 
            magic, 
            stamina, 
            speed, 
            token_resource, 
            token_amount
        )
        
        if not manifest:
            return jsonify({"error": "Failed to create transaction manifest"}), 500
        
        return jsonify({
            "status": "ok",
            "manifest": manifest,
            "cost": {
                "token": token_symbol,
                "amount": token_amount
            }
        })
    except Exception as e:
        print(f"Error in get_level_up_stats_manifest: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/getCombineCreaturesManifest", methods=["POST"])
def get_combine_creatures_manifest():
    try:
        if 'telegram_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        data = request.json or {}
        account_address = data.get("accountAddress")
        creature_a_id = data.get("creatureAId")
        creature_b_id = data.get("creatureBId")
        creature_a_data = data.get("creatureAData", {})
        creature_b_data = data.get("creatureBData", {})
        
        if not account_address:
            return jsonify({"error": "No account address provided"}), 400
        
        if not creature_a_id or not creature_b_id:
            return jsonify({"error": "Two creature IDs are required"}), 400
        
        # Check that both creatures are the same species
        species_a = creature_a_data.get("species_id")
        species_b = creature_b_data.get("species_id")
        
        if species_a != species_b:
            return jsonify({"error": "Can only combine creatures of the same species"}), 400
        
        # Check that both creatures have the same combination level
        combo_a = creature_a_data.get("combination_level", 0)
        combo_b = creature_b_data.get("combination_level", 0)
        
        if combo_a != combo_b:
            return jsonify({"error": "Can only combine creatures of the same combination level"}), 400
        
        # Check that the combination level is not at max (3)
        if combo_a >= 3:
            return jsonify({"error": "Creatures have already reached maximum combination level"}), 400
        
        # Create the manifest
        manifest = create_combine_creatures_manifest(
            account_address,
            creature_a_id,
            creature_b_id
        )
        
        if not manifest:
            return jsonify({"error": "Failed to create transaction manifest"}), 500
        
        return jsonify({
            "status": "ok",
            "manifest": manifest,
            "newCombinationLevel": combo_a + 1
        })
    except Exception as e:
        print(f"Error in get_combine_creatures_manifest: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
