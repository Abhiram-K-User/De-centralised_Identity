"""
DID++ Blockchain Service
Ethereum Sepolia integration via Alchemy for DID registration and verification logging.
"""

import json
import time
from typing import Optional, List, Dict, Any
from web3 import Web3
from eth_account import Account

from app.config import config


# Smart contract ABI - minimal interface for DID operations
CONTRACT_ABI = [
    {
        "inputs": [{"name": "identityHash", "type": "bytes32"}],
        "name": "registerDID",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "verificationHash", "type": "bytes32"}],
        "name": "logVerification",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "did", "type": "string"}],
        "name": "getVerifications",
        "outputs": [
            {
                "components": [
                    {"name": "verificationHash", "type": "bytes32"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "blockNumber", "type": "uint256"}
                ],
                "name": "",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "did", "type": "string"},
            {"indexed": False, "name": "identityHash", "type": "bytes32"},
            {"indexed": False, "name": "timestamp", "type": "uint256"}
        ],
        "name": "DIDRegistered",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "did", "type": "string"},
            {"indexed": False, "name": "verificationHash", "type": "bytes32"},
            {"indexed": False, "name": "timestamp", "type": "uint256"}
        ],
        "name": "VerificationLogged",
        "type": "event"
    }
]


class BlockchainService:
    """Service for interacting with Ethereum Sepolia blockchain."""
    
    def __init__(self):
        """Initialize blockchain service with Alchemy connection."""
        self.w3 = Web3(Web3.HTTPProvider(config.ALCHEMY_RPC_URL))
        
        # Load account from private key
        if config.PRIVATE_KEY:
            self.account = Account.from_key(config.PRIVATE_KEY)
        else:
            self.account = None
        
        # Load contract
        if config.CONTRACT_ADDRESS:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(config.CONTRACT_ADDRESS),
                abi=CONTRACT_ABI
            )
        else:
            self.contract = None
    
    def is_connected(self) -> bool:
        """Check if connected to blockchain."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False
    
    def _send_transaction(self, function) -> Optional[str]:
        """
        Send a transaction to the blockchain.
        
        Args:
            function: Contract function to call
            
        Returns:
            Transaction hash or None on failure
        """
        if not self.account or not self.contract:
            print("Blockchain not configured properly")
            return None
        
        try:
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            tx = function.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 11155111  # Sepolia chain ID
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx, private_key=config.PRIVATE_KEY
            )
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return tx_hash.hex()
            else:
                print(f"Transaction failed: {receipt}")
                return None
                
        except Exception as e:
            print(f"Blockchain transaction error: {e}")
            return None
    
    def register_did(self, identity_hash: bytes, did: str = None) -> Optional[str]:
        """
        Register DID on blockchain.
        
        Args:
            identity_hash: 32-byte identity hash
            did: Optional DID string for event indexing
            
        Returns:
            Transaction hash or None on failure
        """
        if len(identity_hash) != 32:
            raise ValueError("Identity hash must be 32 bytes")
        
        function = self.contract.functions.registerDID(identity_hash)
        return self._send_transaction(function)
    
    def log_verification(self, verification_hash: bytes, did: str = None) -> Optional[str]:
        """
        Log verification on blockchain.
        
        Args:
            verification_hash: 32-byte verification hash
            did: Optional DID string for event indexing
            
        Returns:
            Transaction hash or None on failure
        """
        if len(verification_hash) != 32:
            raise ValueError("Verification hash must be 32 bytes")
        
        function = self.contract.functions.logVerification(verification_hash)
        return self._send_transaction(function)
    
    def get_verifications(self, did: str) -> List[Dict[str, Any]]:
        """
        Get verification history for a DID from blockchain.
        
        Args:
            did: DID string to query
            
        Returns:
            List of verification records
        """
        if not self.contract:
            return []
        
        try:
            results = self.contract.functions.getVerifications(did).call()
            
            verifications = []
            for result in results:
                verifications.append({
                    'verification_hash': result[0].hex(),
                    'timestamp': result[1],
                    'block_number': result[2]
                })
            
            return verifications
            
        except Exception as e:
            print(f"Error getting verifications: {e}")
            return []
    
    def get_registration_events(self, did: str = None) -> List[Dict[str, Any]]:
        """
        Get registration events from blockchain logs.
        
        Args:
            did: Optional DID to filter by
            
        Returns:
            List of registration events
        """
        if not self.contract:
            return []
        
        try:
            # Get DIDRegistered events
            event_filter = self.contract.events.DIDRegistered.create_filter(
                fromBlock=0,
                toBlock='latest'
            )
            events = event_filter.get_all_entries()
            
            registrations = []
            for event in events:
                if did is None or event['args']['did'] == did:
                    registrations.append({
                        'did': event['args']['did'],
                        'identity_hash': event['args']['identityHash'].hex(),
                        'timestamp': event['args']['timestamp'],
                        'block_number': event['blockNumber'],
                        'tx_hash': event['transactionHash'].hex()
                    })
            
            return registrations
            
        except Exception as e:
            print(f"Error getting registration events: {e}")
            return []


# Global blockchain service instance
blockchain_service = BlockchainService()
