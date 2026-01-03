"""
DID++ Blockchain Service
Ethereum Sepolia integration for fully decentralized identity management.

Implements:
- DIDRegistry contract: Maps DIDs to IPFS CIDs and identity hashes
- VerificationLog contract: Records immutable verification proofs
- Event log queries for history reconstruction
"""

import json
from typing import Optional, List, Dict, Any, Tuple
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account

from app.config import config


# ============ DIDRegistry ABI ============
DID_REGISTRY_ABI = [
    # registerDID
    {
        "inputs": [
            {"name": "did", "type": "string"},
            {"name": "metadataCID", "type": "string"},
            {"name": "identityHash", "type": "bytes32"}
        ],
        "name": "registerDID",
        "outputs": [{"name": "didHash", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # updateDID
    {
        "inputs": [
            {"name": "did", "type": "string"},
            {"name": "newMetadataCID", "type": "string"},
            {"name": "newIdentityHash", "type": "bytes32"}
        ],
        "name": "updateDID",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # getMetadataCID
    {
        "inputs": [{"name": "did", "type": "string"}],
        "name": "getMetadataCID",
        "outputs": [{"name": "metadataCID", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    # getDIDRecord
    {
        "inputs": [{"name": "did", "type": "string"}],
        "name": "getDIDRecord",
        "outputs": [
            {
                "components": [
                    {"name": "metadataCID", "type": "string"},
                    {"name": "identityHash", "type": "bytes32"},
                    {"name": "registeredAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "registrar", "type": "address"},
                    {"name": "active", "type": "bool"}
                ],
                "name": "record",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # isDIDActive
    {
        "inputs": [{"name": "did", "type": "string"}],
        "name": "isDIDActive",
        "outputs": [
            {"name": "exists", "type": "bool"},
            {"name": "active", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # verifyDID
    {
        "inputs": [
            {"name": "did", "type": "string"},
            {"name": "metadataCID", "type": "string"},
            {"name": "identityHash", "type": "bytes32"}
        ],
        "name": "verifyDID",
        "outputs": [{"name": "valid", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    # totalDIDs
    {
        "inputs": [],
        "name": "totalDIDs",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # DIDRegistered event
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "didHash", "type": "bytes32"},
            {"indexed": False, "name": "did", "type": "string"},
            {"indexed": False, "name": "metadataCID", "type": "string"},
            {"indexed": False, "name": "identityHash", "type": "bytes32"},
            {"indexed": True, "name": "registrar", "type": "address"},
            {"indexed": False, "name": "timestamp", "type": "uint256"}
        ],
        "name": "DIDRegistered",
        "type": "event"
    },
    # DIDUpdated event
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "didHash", "type": "bytes32"},
            {"indexed": False, "name": "did", "type": "string"},
            {"indexed": False, "name": "newMetadataCID", "type": "string"},
            {"indexed": False, "name": "newIdentityHash", "type": "bytes32"},
            {"indexed": False, "name": "timestamp", "type": "uint256"}
        ],
        "name": "DIDUpdated",
        "type": "event"
    }
]

# ============ VerificationLog ABI ============
VERIFICATION_LOG_ABI = [
    # logVerification
    {
        "inputs": [
            {"name": "did", "type": "string"},
            {"name": "verificationHash", "type": "bytes32"},
            {"name": "metadataCID", "type": "string"},
            {"name": "confidenceLevel", "type": "uint8"},
            {"name": "success", "type": "bool"}
        ],
        "name": "logVerification",
        "outputs": [{"name": "recordHash", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # getVerificationCount
    {
        "inputs": [{"name": "did", "type": "string"}],
        "name": "getVerificationCount",
        "outputs": [{"name": "count", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # getRecentVerifications
    {
        "inputs": [
            {"name": "did", "type": "string"},
            {"name": "limit", "type": "uint256"}
        ],
        "name": "getRecentVerifications",
        "outputs": [
            {
                "components": [
                    {"name": "didHash", "type": "bytes32"},
                    {"name": "verificationHash", "type": "bytes32"},
                    {"name": "metadataCIDHash", "type": "bytes32"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "blockNumber", "type": "uint256"},
                    {"name": "verifier", "type": "address"},
                    {"name": "confidenceLevel", "type": "uint8"},
                    {"name": "success", "type": "bool"}
                ],
                "name": "records",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # totalVerifications
    {
        "inputs": [],
        "name": "totalVerifications",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # VerificationLogged event
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "didHash", "type": "bytes32"},
            {"indexed": False, "name": "did", "type": "string"},
            {"indexed": True, "name": "verificationHash", "type": "bytes32"},
            {"indexed": False, "name": "metadataCID", "type": "string"},
            {"indexed": False, "name": "confidenceLevel", "type": "uint8"},
            {"indexed": False, "name": "success", "type": "bool"},
            {"indexed": True, "name": "verifier", "type": "address"},
            {"indexed": False, "name": "timestamp", "type": "uint256"},
            {"indexed": False, "name": "blockNumber", "type": "uint256"}
        ],
        "name": "VerificationLogged",
        "type": "event"
    }
]


# Confidence level mapping
CONFIDENCE_LEVELS = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "VERY_HIGH": 3
}

CONFIDENCE_LEVELS_REVERSE = {v: k for k, v in CONFIDENCE_LEVELS.items()}


class BlockchainService:
    """
    Service for interacting with Ethereum Sepolia blockchain.
    
    Manages two contracts:
    - DIDRegistry: Registration and CID storage
    - VerificationLog: Verification event logging
    """
    
    def __init__(self):
        """Initialize blockchain service with Alchemy connection."""
        self.w3 = Web3(Web3.HTTPProvider(config.ALCHEMY_RPC_URL))
        
        # Load account from private key
        if config.PRIVATE_KEY:
            self.account = Account.from_key(config.PRIVATE_KEY)
        else:
            self.account = None
        
        # Load DIDRegistry contract
        if config.DID_REGISTRY_ADDRESS:
            self.did_registry = self.w3.eth.contract(
                address=Web3.to_checksum_address(config.DID_REGISTRY_ADDRESS),
                abi=DID_REGISTRY_ABI
            )
        else:
            self.did_registry = None
        
        # Load VerificationLog contract
        if config.VERIFICATION_LOG_ADDRESS:
            self.verification_log = self.w3.eth.contract(
                address=Web3.to_checksum_address(config.VERIFICATION_LOG_ADDRESS),
                abi=VERIFICATION_LOG_ABI
            )
        else:
            self.verification_log = None
    
    def is_connected(self) -> bool:
        """Check if connected to blockchain."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False
    
    def is_configured(self) -> bool:
        """Check if blockchain service is properly configured."""
        return (
            self.is_connected() and
            self.account is not None and
            self.did_registry is not None and
            self.verification_log is not None
        )
    
    def _send_transaction(self, function, gas_limit: int = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Send a transaction to the blockchain.
        
        Args:
            function: Contract function to call
            gas_limit: Optional custom gas limit
            
        Returns:
            Tuple of (transaction_hash, error_message)
        """
        if not self.account:
            return None, "Blockchain wallet not configured"
        
        try:
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            tx = function.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': gas_limit or config.GAS_LIMIT,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': config.CHAIN_ID
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
                # Ensure tx_hash has 0x prefix
                tx_hex = tx_hash.hex()
                if not tx_hex.startswith('0x'):
                    tx_hex = '0x' + tx_hex
                return tx_hex, None
            else:
                return None, f"Transaction reverted: {receipt}"
                
        except ContractLogicError as e:
            return None, f"Contract error: {str(e)}"
        except Exception as e:
            return None, f"Blockchain error: {str(e)}"
    
    # ============ DIDRegistry Methods ============
    
    def register_did(
        self,
        did: str,
        metadata_cid: str,
        identity_hash: bytes
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Register a new DID on the blockchain.
        
        Args:
            did: Full DID string
            metadata_cid: IPFS CID of encrypted metadata
            identity_hash: 32-byte identity hash
            
        Returns:
            Tuple of (transaction_hash, error_message)
        """
        if not self.did_registry:
            return None, "DIDRegistry contract not configured"
        
        if len(identity_hash) != 32:
            return None, "Identity hash must be 32 bytes"
        
        function = self.did_registry.functions.registerDID(
            did,
            metadata_cid,
            identity_hash
        )
        
        return self._send_transaction(function)
    
    def update_did(
        self,
        did: str,
        new_metadata_cid: str,
        new_identity_hash: bytes
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Update the metadata CID for an existing DID.
        
        Args:
            did: Full DID string
            new_metadata_cid: New IPFS CID
            new_identity_hash: New 32-byte identity hash
            
        Returns:
            Tuple of (transaction_hash, error_message)
        """
        if not self.did_registry:
            return None, "DIDRegistry contract not configured"
        
        if len(new_identity_hash) != 32:
            return None, "Identity hash must be 32 bytes"
        
        function = self.did_registry.functions.updateDID(
            did,
            new_metadata_cid,
            new_identity_hash
        )
        
        return self._send_transaction(function)
    
    def get_metadata_cid(self, did: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the IPFS CID for a DID's metadata.
        
        Args:
            did: Full DID string
            
        Returns:
            Tuple of (cid, error_message)
        """
        if not self.did_registry:
            return None, "DIDRegistry contract not configured"
        
        try:
            cid = self.did_registry.functions.getMetadataCID(did).call()
            return cid, None
        except ContractLogicError as e:
            return None, f"DID not found: {str(e)}"
        except Exception as e:
            return None, f"Error fetching CID: {str(e)}"
    
    def get_did_record(self, did: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Get the full record for a DID from the blockchain.
        
        Args:
            did: Full DID string
            
        Returns:
            Tuple of (record_dict, error_message)
        """
        if not self.did_registry:
            return None, "DIDRegistry contract not configured"
        
        try:
            record = self.did_registry.functions.getDIDRecord(did).call()
            
            return {
                "metadata_cid": record[0],
                "identity_hash": record[1].hex(),
                "registered_at": record[2],
                "updated_at": record[3],
                "registrar": record[4],
                "active": record[5]
            }, None
            
        except ContractLogicError as e:
            return None, f"DID not found: {str(e)}"
        except Exception as e:
            return None, f"Error fetching record: {str(e)}"
    
    def is_did_active(self, did: str) -> Tuple[bool, bool]:
        """
        Check if a DID exists and is active.
        
        Args:
            did: Full DID string
            
        Returns:
            Tuple of (exists, active)
        """
        if not self.did_registry:
            return False, False
        
        try:
            exists, active = self.did_registry.functions.isDIDActive(did).call()
            return exists, active
        except:
            return False, False
    
    # ============ VerificationLog Methods ============
    
    def log_verification(
        self,
        did: str,
        verification_hash: bytes,
        metadata_cid: str,
        confidence_level: str,
        success: bool
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Log a verification event on the blockchain.
        
        Args:
            did: Full DID string
            verification_hash: 32-byte verification hash
            metadata_cid: IPFS CID used for verification
            confidence_level: "LOW", "MEDIUM", "HIGH", or "VERY_HIGH"
            success: Whether verification was successful
            
        Returns:
            Tuple of (transaction_hash, error_message)
        """
        if not self.verification_log:
            return None, "VerificationLog contract not configured"
        
        if len(verification_hash) != 32:
            return None, "Verification hash must be 32 bytes"
        
        confidence_uint8 = CONFIDENCE_LEVELS.get(confidence_level, 0)
        
        function = self.verification_log.functions.logVerification(
            did,
            verification_hash,
            metadata_cid,
            confidence_uint8,
            success
        )
        
        return self._send_transaction(function)
    
    def get_verification_count(self, did: str) -> int:
        """
        Get the number of verifications for a DID.
        
        Args:
            did: Full DID string
            
        Returns:
            Verification count
        """
        if not self.verification_log:
            return 0
        
        try:
            return self.verification_log.functions.getVerificationCount(did).call()
        except:
            return 0
    
    def get_recent_verifications(
        self,
        did: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent verifications for a DID.
        
        Args:
            did: Full DID string
            limit: Maximum number of records
            
        Returns:
            List of verification records
        """
        if not self.verification_log:
            return []
        
        try:
            records = self.verification_log.functions.getRecentVerifications(
                did, limit
            ).call()
            
            result = []
            for record in records:
                result.append({
                    "did_hash": record[0].hex(),
                    "verification_hash": record[1].hex(),
                    "metadata_cid_hash": record[2].hex(),
                    "timestamp": record[3],
                    "block_number": record[4],
                    "verifier": record[5],
                    "confidence_level": CONFIDENCE_LEVELS_REVERSE.get(record[6], "UNKNOWN"),
                    "success": record[7]
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting verifications: {e}")
            return []
    
    # ============ Event Log Queries ============
    
    def get_registration_events(
        self,
        did: str = None,
        from_block: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get DIDRegistered events from blockchain logs.
        
        Args:
            did: Optional DID to filter by
            from_block: Starting block number
            
        Returns:
            List of registration events
        """
        if not self.did_registry:
            return []
        
        try:
            # Build filter
            if did:
                did_hash = Web3.keccak(text=did)
                event_filter = self.did_registry.events.DIDRegistered.create_filter(
                    fromBlock=from_block,
                    toBlock='latest',
                    argument_filters={'didHash': did_hash}
                )
            else:
                event_filter = self.did_registry.events.DIDRegistered.create_filter(
                    fromBlock=from_block,
                    toBlock='latest'
                )
            
            events = event_filter.get_all_entries()
            
            result = []
            for event in events:
                result.append({
                    "event_type": "registration",
                    "did_hash": event['args']['didHash'].hex(),
                    "did": event['args']['did'],
                    "metadata_cid": event['args']['metadataCID'],
                    "identity_hash": event['args']['identityHash'].hex(),
                    "registrar": event['args']['registrar'],
                    "timestamp": event['args']['timestamp'],
                    "block_number": event['blockNumber'],
                    "tx_hash": event['transactionHash'].hex()
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting registration events: {e}")
            return []
    
    def get_verification_events(
        self,
        did: str = None,
        from_block: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get VerificationLogged events from blockchain logs.
        
        Args:
            did: Optional DID to filter by
            from_block: Starting block number
            
        Returns:
            List of verification events
        """
        if not self.verification_log:
            return []
        
        try:
            # Build filter
            if did:
                did_hash = Web3.keccak(text=did)
                event_filter = self.verification_log.events.VerificationLogged.create_filter(
                    fromBlock=from_block,
                    toBlock='latest',
                    argument_filters={'didHash': did_hash}
                )
            else:
                event_filter = self.verification_log.events.VerificationLogged.create_filter(
                    fromBlock=from_block,
                    toBlock='latest'
                )
            
            events = event_filter.get_all_entries()
            
            result = []
            for event in events:
                result.append({
                    "event_type": "verification",
                    "did_hash": event['args']['didHash'].hex(),
                    "did": event['args']['did'],
                    "verification_hash": event['args']['verificationHash'].hex(),
                    "metadata_cid": event['args']['metadataCID'],
                    "confidence_level": CONFIDENCE_LEVELS_REVERSE.get(
                        event['args']['confidenceLevel'], "UNKNOWN"
                    ),
                    "success": event['args']['success'],
                    "verifier": event['args']['verifier'],
                    "timestamp": event['args']['timestamp'],
                    "block_number": event['args']['blockNumber'],
                    "tx_hash": event['transactionHash'].hex()
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting verification events: {e}")
            return []
    
    def get_full_timeline(self, did: str) -> List[Dict[str, Any]]:
        """
        Get full timeline of events for a DID.
        
        Combines DIDRegistered and VerificationLogged events into a
        chronological timeline.
        
        Args:
            did: Full DID string
            
        Returns:
            List of events sorted by timestamp
        """
        registrations = self.get_registration_events(did)
        verifications = self.get_verification_events(did)
        
        timeline = registrations + verifications
        timeline.sort(key=lambda x: (x['timestamp'], x['block_number']))
        
        return timeline
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get overall blockchain statistics.
        
        Returns:
            Dictionary with stats
        """
        stats = {
            "connected": self.is_connected(),
            "configured": self.is_configured(),
            "chain_id": config.CHAIN_ID,
            "total_dids": 0,
            "total_verifications": 0
        }
        
        if self.did_registry:
            try:
                stats["total_dids"] = self.did_registry.functions.totalDIDs().call()
            except:
                pass
        
        if self.verification_log:
            try:
                stats["total_verifications"] = self.verification_log.functions.totalVerifications().call()
            except:
                pass
        
        if self.account:
            stats["wallet_address"] = self.account.address
            try:
                balance_wei = self.w3.eth.get_balance(self.account.address)
                stats["wallet_balance_eth"] = float(Web3.from_wei(balance_wei, 'ether'))
            except:
                pass
        
        return stats


# Note: Global blockchain_service instance is now created in __init__.py
# using blockchain_smart.py (SimpleSmartBlockchainService) which provides
# automatic fallback between optimized and legacy services.
