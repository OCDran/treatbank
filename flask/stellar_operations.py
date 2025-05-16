# stellar_operations.py

import requests
from stellar_sdk import (
    Server,
    Keypair,
    TransactionBuilder,
    Network,
    Asset,
    Operation,
)
from config import (
    HORIZON_URL,
    STELLAR_NETWORK,
    FRIENDBOT_URL,
    ASSET_CODE,
    ISSUER_PUBLIC_KEY, # This will be set after generation
    ISSUER_SECRET_KEY, # This will be set after generation
    DISTRIBUTOR_PUBLIC_KEY, # This will be set after generation
    DISTRIBUTOR_SECRET_KEY, # This will be set after generation
)

# Global variables to store generated keys if not pre-configured
# This is for demonstration; in a real app, manage keys more robustly.
generated_issuer_keypair = None
generated_distributor_keypair = None

def get_network_passphrase():
    """Returns the network passphrase based on the STELLAR_NETWORK setting."""
    if STELLAR_NETWORK == "TESTNET":
        return Network.TESTNET_NETWORK_PASSPHRASE
    elif STELLAR_NETWORK == "PUBLIC":
        return Network.PUBLIC_NETWORK_PASSPHRASE
    else:
        raise ValueError("Invalid STELLAR_NETWORK configured.")

def generate_keypair():
    """Generates a new Stellar keypair."""
    return Keypair.random()

def fund_account_friendbot(public_key):
    """Funds a Testnet account using Friendbot."""
    if STELLAR_NETWORK != "TESTNET":
        return {"status": "error", "message": "Friendbot can only be used on Testnet."}
    try:
        response = requests.get(FRIENDBOT_URL, params={"addr": public_key})
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        if response.status_code == 200:
            return {"status": "success", "message": f"Account {public_key} funded successfully."}
        else:
            return {"status": "error", "message": f"Friendbot request failed: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Friendbot request error: {e}"}

def setup_stellar_accounts():
    """
    Generates and funds issuer and distributor accounts if they are not already configured.
    This is a simplified setup for demonstration.
    """
    global generated_issuer_keypair, generated_distributor_keypair
    global ISSUER_PUBLIC_KEY, ISSUER_SECRET_KEY, DISTRIBUTOR_PUBLIC_KEY, DISTRIBUTOR_SECRET_KEY

    results = {}

    # Setup Issuer Account
    if not ISSUER_SECRET_KEY:
        print("Generating Issuer Keypair...")
        generated_issuer_keypair = generate_keypair()
        ISSUER_PUBLIC_KEY = generated_issuer_keypair.public_key
        ISSUER_SECRET_KEY = generated_issuer_keypair.secret_key
        results["issuer_public_key"] = ISSUER_PUBLIC_KEY
        results["issuer_secret_key"] = ISSUER_SECRET_KEY # For demo purposes, normally don't expose
        print(f"Issuer Account: {ISSUER_PUBLIC_KEY}")
        if STELLAR_NETWORK == "TESTNET":
            fund_result = fund_account_friendbot(ISSUER_PUBLIC_KEY)
            results["issuer_funding"] = fund_result
            print(f"Funding Issuer Account: {fund_result}")
            if fund_result["status"] == "error":
                 return {"status": "error", "message": f"Failed to fund issuer: {fund_result['message']}"}
        else:
            results["issuer_funding"] = "Manual funding required for Public network."
    else:
        results["issuer_public_key"] = ISSUER_PUBLIC_KEY
        results["issuer_funding"] = "Issuer account pre-configured."
        generated_issuer_keypair = Keypair.from_secret(ISSUER_SECRET_KEY)


    # Setup Distributor Account
    if not DISTRIBUTOR_SECRET_KEY:
        print("Generating Distributor Keypair...")
        generated_distributor_keypair = generate_keypair()
        DISTRIBUTOR_PUBLIC_KEY = generated_distributor_keypair.public_key
        DISTRIBUTOR_SECRET_KEY = generated_distributor_keypair.secret_key
        results["distributor_public_key"] = DISTRIBUTOR_PUBLIC_KEY
        results["distributor_secret_key"] = DISTRIBUTOR_SECRET_KEY # For demo
        print(f"Distributor Account: {DISTRIBUTOR_PUBLIC_KEY}")
        if STELLAR_NETWORK == "TESTNET":
            fund_result = fund_account_friendbot(DISTRIBUTOR_PUBLIC_KEY)
            results["distributor_funding"] = fund_result
            print(f"Funding Distributor Account: {fund_result}")
            if fund_result["status"] == "error":
                 return {"status": "error", "message": f"Failed to fund distributor: {fund_result['message']}"}
        else:
            results["distributor_funding"] = "Manual funding required for Public network."
    else:
        results["distributor_public_key"] = DISTRIBUTOR_PUBLIC_KEY
        results["distributor_funding"] = "Distributor account pre-configured."
        generated_distributor_keypair = Keypair.from_secret(DISTRIBUTOR_SECRET_KEY)

    if not ISSUER_PUBLIC_KEY or not DISTRIBUTOR_PUBLIC_KEY:
        return {"status": "error", "message": "Account keys are not properly set up."}

    results["status"] = "success"
    return results


def issue_custom_asset(asset_code, asset_issuer_pk, distributor_pk, distributor_sk, issuer_sk, amount_to_issue):
    """
    Issues a custom asset. This involves:
    1. Distributor creates a trustline to the Issuer for the asset.
    2. Issuer makes a payment of the custom asset to the Distributor.

    This function simulates the "deployment" of our basic "smart contract" (the custom asset).
    """
    if not asset_issuer_pk or not distributor_pk or not distributor_sk or not issuer_sk:
        return {"status": "error", "message": "Account keys are not set. Run setup first."}

    server = Server(horizon_url=HORIZON_URL)
    network_passphrase = get_network_passphrase()

    issuer_keypair = Keypair.from_secret(issuer_sk)
    distributor_keypair = Keypair.from_secret(distributor_sk)

    custom_asset = Asset(asset_code, asset_issuer_pk)

    # Step 1: Distributor creates a trustline to the Issuer for the asset.
    try:
        distributor_account = server.load_account(distributor_pk)
        print(f"Building trustline transaction for {distributor_pk} to trust {asset_code}:{asset_issuer_pk}")

        tx_trust = (
            TransactionBuilder(
                source_account=distributor_account,
                network_passphrase=network_passphrase,
                base_fee=server.fetch_base_fee(), # Fetches the current minimum base fee
            )
            .append_change_trust_op(asset=custom_asset) # No limit, trusts up to max
            .build()
        )
        tx_trust.sign(distributor_keypair)
        response_trust = server.submit_transaction(tx_trust)
        print(f"Trustline transaction submitted: {response_trust['hash']}")

    except Exception as e:
        print(f"Error creating trustline: {e}")
        return {"status": "error", "message": f"Error creating trustline: {e}"}

    # Step 2: Issuer makes a payment of the custom asset to the Distributor.
    try:
        issuer_account = server.load_account(asset_issuer_pk)
        print(f"Building payment transaction from {asset_issuer_pk} to {distributor_pk} for {amount_to_issue} {asset_code}")

        tx_payment = (
            TransactionBuilder(
                source_account=issuer_account,
                network_passphrase=network_passphrase,
                base_fee=server.fetch_base_fee(),
            )
            .append_payment_op(
                destination=distributor_pk,
                asset=custom_asset,
                amount=str(amount_to_issue),
            )
            .build()
        )
        tx_payment.sign(issuer_keypair)
        response_payment = server.submit_transaction(tx_payment)
        print(f"Payment transaction submitted: {response_payment['hash']}")
        return {
            "status": "success",
            "message": f"Asset {asset_code} issued and {amount_to_issue} sent to {distributor_pk}.",
            "trustline_tx": response_trust['hash'],
            "payment_tx": response_payment['hash'],
        }
    except Exception as e:
        print(f"Error issuing asset: {e}")
        return {"status": "error", "message": f"Error issuing asset: {e}"}

def check_asset_balance(account_public_key, asset_code_to_check, asset_issuer_pk):
    """Checks the balance of a specific asset for a given account."""
    if not account_public_key or not asset_issuer_pk:
        return {"status": "error", "message": "Account public key or asset issuer PK missing."}

    server = Server(horizon_url=HORIZON_URL)
    try:
        account = server.load_account(account_public_key)
        for balance in account.balances:
            if balance.asset_type == "native":
                if asset_code_to_check.upper() == "XLM": # Native asset
                    return {
                        "status": "success",
                        "asset_code": "XLM",
                        "balance": balance.balance
                    }
            elif balance.asset_code == asset_code_to_check and balance.asset_issuer == asset_issuer_pk:
                return {
                    "status": "success",
                    "asset_code": balance.asset_code,
                    "balance": balance.balance,
                    "issuer": balance.asset_issuer
                }
        return {
            "status": "success",
            "asset_code": asset_code_to_check,
            "balance": "0.0000000", # Not found or zero balance
            "message": f"Asset {asset_code_to_check} not found or balance is zero for account {account_public_key}."
        }
    except Exception as e:
        print(f"Error checking balance: {e}")
        return {"status": "error", "message": f"Error checking balance: {e}"}

# Example of how to use these functions (optional, for direct script execution)
if __name__ == "__main__":
    print("Stellar Operations Module")
    print(f"Using Horizon Server: {HORIZON_URL}")
    print(f"Network: {STELLAR_NETWORK}")

    # --- This part is for testing the module directly ---
    # 1. Setup accounts (generates new ones if not in config.py and funds from friendbot if testnet)
    # Important: For this to work, config.py ISSUER_SECRET_KEY and DISTRIBUTOR_SECRET_KEY should be None
    # or valid keys for the chosen network.
    # For a fresh run, set them to None.
    
    # config.ISSUER_SECRET_KEY = None # Uncomment to force regeneration
    # config.DISTRIBUTOR_SECRET_KEY = None # Uncomment to force regeneration
    
    setup_result = setup_stellar_accounts()
    print("\n--- Account Setup Result ---")
    print(setup_result)

    if setup_result.get("status") == "success" or (ISSUER_SECRET_KEY and DISTRIBUTOR_SECRET_KEY):
        # Ensure keys are available globally for the rest of the script if generated
        current_issuer_pk = ISSUER_PUBLIC_KEY
        current_issuer_sk = ISSUER_SECRET_KEY
        current_distributor_pk = DISTRIBUTOR_PUBLIC_KEY
        current_distributor_sk = DISTRIBUTOR_SECRET_KEY

        if not current_issuer_pk or not current_distributor_pk:
            print("Issuer or Distributor keys are missing after setup. Exiting.")
        else:
            # 2. Issue Custom Asset
            print(f"\n--- Issuing Custom Asset ({ASSET_CODE}) ---")
            # The issuer public key is now available from the setup_stellar_accounts or config
            issue_result = issue_custom_asset(
                asset_code=ASSET_CODE,
                asset_issuer_pk=current_issuer_pk,
                distributor_pk=current_distributor_pk,
                distributor_sk=current_distributor_sk,
                issuer_sk=current_issuer_sk,
                amount_to_issue="1000" # Issue 1000 tokens
            )
            print(issue_result)

            if issue_result.get("status") == "success":
                # 3. Check Distributor's Balance of the Custom Asset
                print(f"\n--- Checking {ASSET_CODE} Balance for Distributor ({current_distributor_pk}) ---")
                balance_result = check_asset_balance(
                    account_public_key=current_distributor_pk,
                    asset_code_to_check=ASSET_CODE,
                    asset_issuer_pk=current_issuer_pk
                )
                print(balance_result)

                print(f"\n--- Checking XLM Balance for Distributor ({current_distributor_pk}) ---")
                xlm_balance_result = check_asset_balance(
                    account_public_key=current_distributor_pk,
                    asset_code_to_check="XLM", # Special case for native asset
                    asset_issuer_pk=None # Issuer is not applicable for XLM
                )
                print(xlm_balance_result)
    else:
        print("Account setup failed. Cannot proceed with asset issuance.")

