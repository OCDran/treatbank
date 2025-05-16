# config.py

# Stellar Network Configuration
# Use 'TESTNET' for testing or 'PUBLIC' for the live network
STELLAR_NETWORK = "TESTNET"  # Or "PUBLIC"

# Horizon server URLs
HORIZON_TESTNET_URL = "https://horizon-testnet.stellar.org"
HORIZON_PUBLIC_URL = "https://horizon.stellar.org"

# Determine Horizon URL based on selected network
HORIZON_URL = HORIZON_TESTNET_URL if STELLAR_NETWORK == "TESTNET" else HORIZON_PUBLIC_URL

# --- Account Configuration ---
# In a real application, NEVER hardcode secret keys.
# Use environment variables or a secure secrets manager.

# For this example, we'll generate them or you can fill them in if you have existing ones.
# These will be populated by the application or you can pre-fill them.

# Issuer Account: This account creates and issues the custom asset.
ISSUER_SECRET_KEY = None  # Example: 'SA******************************************************'
ISSUER_PUBLIC_KEY = None  # Example: 'GA******************************************************'

# Distributor Account: This account will receive and distribute the custom asset.
# It needs to trust the issuer's asset before it can hold it.
DISTRIBUTOR_SECRET_KEY = None # Example: 'SD******************************************************'
DISTRIBUTOR_PUBLIC_KEY = None # Example: 'GD******************************************************'

# Custom Asset Details
ASSET_CODE = "MYTOKEN" # 1-12 alphanumeric characters
# The ASSET_ISSUER will be the ISSUER_PUBLIC_KEY

# --- Friendbot (for Testnet only) ---
FRIENDBOT_URL = "https://friendbot.stellar.org"

# --- Smart Contract (Soroban) ---
# For actual Soroban smart contracts, you'd have:
# RPC_SERVER_URL = "https://soroban-testnet.stellar.org:443" # Example for Testnet
# PASSPHRASE = "Test SDF Network ; September 2015" # For Testnet
# For this "basic" example, we are focusing on asset issuance, not a full Soroban deployment.
