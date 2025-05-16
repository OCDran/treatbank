import os
from flask import Flask, jsonify, request
import stellar_operations
from config import ASSET_CODE

# These will hold the keys after setup.
# In a real app, you'd manage this state more carefully or retrieve from config.
# For simplicity, we use global variables here, updated by stellar_operations.
# This relies on stellar_operations.py modifying its global ISSUER_PUBLIC_KEY etc.
# or directly accessing them from the config module after they've been set.

app = Flask(__name__)

# --- Global variables to store keys after setup ---
# These will be populated from stellar_operations or config after setup_accounts is called.
# This is a simplification for demonstration.
app_issuer_public_key = None
app_issuer_secret_key = None # Be cautious exposing secrets, even in local dev.
app_distributor_public_key = None
app_distributor_secret_key = None


@app.route('/')
def home():
    return jsonify({
        "message": "Stellar Basic Smart Contract (Asset Issuance) API",
        "endpoints": {
            "/setup-accounts": "GET - Generates and funds (Testnet) Issuer and Distributor accounts.",
            "/issue-asset": "POST - {'amount': '1000'} - Issues the custom asset from Issuer to Distributor.",
            "/check-balance/<account_id>": "GET - Checks the balance of the custom asset for the specified account ID.",
            "/check-xlm-balance/<account_id>": "GET - Checks the XLM balance for the specified account ID."
        },
        "notes": "Run /setup-accounts first if you haven't configured keys in config.py."
    })

@app.route('/setup-accounts', methods=['GET'])
def setup_accounts_route():
    """
    Endpoint to generate and fund (on Testnet) new Stellar accounts for issuer and distributor.
    If keys are already in config.py, it will report them as pre-configured.
    """
    global app_issuer_public_key, app_issuer_secret_key, app_distributor_public_key, app_distributor_secret_key

    result = stellar_operations.setup_stellar_accounts()

    if result.get("status") == "success" or \
       (stellar_operations.ISSUER_PUBLIC_KEY and stellar_operations.DISTRIBUTOR_PUBLIC_KEY) :
        # Update app-level globals with the keys used/generated
        app_issuer_public_key = stellar_operations.ISSUER_PUBLIC_KEY
        app_issuer_secret_key = stellar_operations.ISSUER_SECRET_KEY
        app_distributor_public_key = stellar_operations.DISTRIBUTOR_PUBLIC_KEY
        app_distributor_secret_key = stellar_operations.DISTRIBUTOR_SECRET_KEY

        # Return a slightly cleaner response, not exposing secrets directly in API response if possible
        # The stellar_operations.setup_stellar_accounts() already prints secrets if generated.
        # For an API, it's better to confirm setup without echoing secrets.
        api_response = {
            "status": "success",
            "message": "Accounts configured. Check console for generated keys if new.",
            "issuer_public_key": app_issuer_public_key,
            "distributor_public_key": app_distributor_public_key,
            "issuer_funding_status": result.get("issuer_funding", "N/A"),
            "distributor_funding_status": result.get("distributor_funding", "N/A")
        }
        return jsonify(api_response), 200
    else:
        return jsonify(result), 500


@app.route('/issue-asset', methods=['POST'])
def issue_asset_route():
    """
    Endpoint to issue the custom asset.
    Requires 'amount' in JSON payload.
    Assumes accounts are set up (either from config.py or via /setup-accounts).
    """
    global app_issuer_public_key, app_issuer_secret_key, app_distributor_public_key, app_distributor_secret_key

    # Ensure keys are loaded if they were pre-configured and not set via /setup-accounts
    if not app_issuer_public_key and stellar_operations.ISSUER_PUBLIC_KEY:
        app_issuer_public_key = stellar_operations.ISSUER_PUBLIC_KEY
        app_issuer_secret_key = stellar_operations.ISSUER_SECRET_KEY # Loaded from config by stellar_operations
    if not app_distributor_public_key and stellar_operations.DISTRIBUTOR_PUBLIC_KEY:
        app_distributor_public_key = stellar_operations.DISTRIBUTOR_PUBLIC_KEY
        app_distributor_secret_key = stellar_operations.DISTRIBUTOR_SECRET_KEY # Loaded from config

    if not app_issuer_public_key or not app_distributor_public_key or \
       not app_issuer_secret_key or not app_distributor_secret_key:
        return jsonify({
            "status": "error",
            "message": "Accounts not initialized. Run /setup-accounts first or ensure keys are in config.py."
        }), 400

    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({"status": "error", "message": "Missing 'amount' in request body"}), 400

    amount_to_issue = data['amount']

    result = stellar_operations.issue_custom_asset(
        asset_code=ASSET_CODE,
        asset_issuer_pk=app_issuer_public_key,
        distributor_pk=app_distributor_public_key,
        distributor_sk=app_distributor_secret_key, # Pass the secret key
        issuer_sk=app_issuer_secret_key,           # Pass the secret key
        amount_to_issue=amount_to_issue
    )
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/check-balance/<account_id>', methods=['GET'])
def check_balance_route(account_id):
    """
    Endpoint to check the balance of the custom asset for a given account ID.
    """
    # Ensure issuer PK is available to define the asset
    current_issuer_pk = app_issuer_public_key or stellar_operations.ISSUER_PUBLIC_KEY
    if not current_issuer_pk:
         return jsonify({
            "status": "error",
            "message": "Issuer public key not set. Cannot identify the asset. Run /setup-accounts."
        }), 400

    result = stellar_operations.check_asset_balance(
        account_public_key=account_id,
        asset_code_to_check=ASSET_CODE,
        asset_issuer_pk=current_issuer_pk
    )
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/check-xlm-balance/<account_id>', methods=['GET'])
def check_xlm_balance_route(account_id):
    """
    Endpoint to check the XLM (native currency) balance for a given account ID.
    """
    result = stellar_operations.check_asset_balance(
        account_public_key=account_id,
        asset_code_to_check="XLM", # Special code for native asset
        asset_issuer_pk=None # Issuer is not applicable for XLM
    )
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

if __name__ == '__main__':
    # Make sure config values are loaded by stellar_operations at startup if pre-set
    # This is a bit of a workaround for the global key management.
    # In a more robust app, config loading would be more explicit.
    if stellar_operations.ISSUER_SECRET_KEY:
        app_issuer_public_key = stellar_operations.ISSUER_PUBLIC_KEY
        app_issuer_secret_key = stellar_operations.ISSUER_SECRET_KEY
    if stellar_operations.DISTRIBUTOR_SECRET_KEY:
        app_distributor_public_key = stellar_operations.DISTRIBUTOR_PUBLIC_KEY
        app_distributor_secret_key = stellar_operations.DISTRIBUTOR_SECRET_KEY

    print("Flask app starting...")
    print(f"Asset Code: {ASSET_CODE}")
    print(f"Issuer Public Key (from config/stellar_ops): {app_issuer_public_key}")
    print(f"Distributor Public Key (from config/stellar_ops): {app_distributor_public_key}")
    app.run(debug=True, port=5001)



#app = Flask(__name__)

#if __name__ == "__main__":
#    app.run(host="0.0.0.0")
