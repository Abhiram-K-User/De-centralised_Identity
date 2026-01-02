// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title DIDRegistry
 * @notice Decentralized Identity Registry for DID++ System
 * @dev Maps DIDs to IPFS CIDs and identity hashes for fully decentralized storage
 * 
 * Architecture:
 * - DIDs are stored as keccak256 hashes for gas efficiency
 * - CIDs are stored as strings (IPFS Content Identifiers)
 * - Identity hashes are 32-byte SHA-256 hashes of registration payloads
 * - Events enable full history reconstruction without additional storage
 */
contract DIDRegistry {
    
    // ============ State Variables ============
    
    /// @notice Owner of the contract (can be set to address(0) for full decentralization)
    address public owner;
    
    /// @notice Mapping from DID hash to registration data
    mapping(bytes32 => DIDRecord) public didRecords;
    
    /// @notice Mapping from DID hash to existence check
    mapping(bytes32 => bool) public didExists;
    
    /// @notice Total number of registered DIDs
    uint256 public totalDIDs;
    
    // ============ Structs ============
    
    /// @notice Registration record for a DID
    struct DIDRecord {
        string metadataCID;      // IPFS CID containing encrypted biometric metadata
        bytes32 identityHash;    // SHA-256 hash of registration payload (32 bytes)
        uint256 registeredAt;    // Block timestamp of registration
        uint256 updatedAt;       // Block timestamp of last update
        address registrar;       // Address that registered this DID
        bool active;             // Whether the DID is active
    }
    
    // ============ Events ============
    
    /// @notice Emitted when a new DID is registered
    event DIDRegistered(
        bytes32 indexed didHash,
        string did,
        string metadataCID,
        bytes32 identityHash,
        address indexed registrar,
        uint256 timestamp
    );
    
    /// @notice Emitted when a DID's metadata is updated
    event DIDUpdated(
        bytes32 indexed didHash,
        string did,
        string newMetadataCID,
        bytes32 newIdentityHash,
        uint256 timestamp
    );
    
    /// @notice Emitted when a DID is deactivated
    event DIDDeactivated(
        bytes32 indexed didHash,
        string did,
        uint256 timestamp
    );
    
    /// @notice Emitted when a DID is reactivated
    event DIDReactivated(
        bytes32 indexed didHash,
        string did,
        uint256 timestamp
    );
    
    // ============ Modifiers ============
    
    modifier onlyOwner() {
        require(msg.sender == owner, "DIDRegistry: caller is not owner");
        _;
    }
    
    modifier didMustExist(bytes32 didHash) {
        require(didExists[didHash], "DIDRegistry: DID does not exist");
        _;
    }
    
    modifier didMustNotExist(bytes32 didHash) {
        require(!didExists[didHash], "DIDRegistry: DID already exists");
        _;
    }
    
    // ============ Constructor ============
    
    constructor() {
        owner = msg.sender;
    }
    
    // ============ External Functions ============
    
    /**
     * @notice Register a new DID with IPFS metadata
     * @param did The full DID string (e.g., "did:eth:sepolia:user_abc123:xyz")
     * @param metadataCID IPFS CID of the encrypted biometric metadata JSON
     * @param identityHash 32-byte SHA-256 hash of the registration payload
     * @return didHash The keccak256 hash of the DID string
     */
    function registerDID(
        string calldata did,
        string calldata metadataCID,
        bytes32 identityHash
    ) external didMustNotExist(keccak256(bytes(did))) returns (bytes32 didHash) {
        require(bytes(did).length > 0, "DIDRegistry: DID cannot be empty");
        require(bytes(metadataCID).length > 0, "DIDRegistry: CID cannot be empty");
        require(identityHash != bytes32(0), "DIDRegistry: identity hash cannot be zero");
        
        didHash = keccak256(bytes(did));
        
        didRecords[didHash] = DIDRecord({
            metadataCID: metadataCID,
            identityHash: identityHash,
            registeredAt: block.timestamp,
            updatedAt: block.timestamp,
            registrar: msg.sender,
            active: true
        });
        
        didExists[didHash] = true;
        totalDIDs++;
        
        emit DIDRegistered(
            didHash,
            did,
            metadataCID,
            identityHash,
            msg.sender,
            block.timestamp
        );
        
        return didHash;
    }
    
    /**
     * @notice Update the metadata CID for an existing DID
     * @param did The full DID string
     * @param newMetadataCID New IPFS CID of the encrypted metadata
     * @param newIdentityHash New identity hash
     */
    function updateDID(
        string calldata did,
        string calldata newMetadataCID,
        bytes32 newIdentityHash
    ) external didMustExist(keccak256(bytes(did))) {
        bytes32 didHash = keccak256(bytes(did));
        DIDRecord storage record = didRecords[didHash];
        
        require(
            record.registrar == msg.sender || msg.sender == owner,
            "DIDRegistry: not authorized"
        );
        require(record.active, "DIDRegistry: DID is deactivated");
        require(bytes(newMetadataCID).length > 0, "DIDRegistry: CID cannot be empty");
        require(newIdentityHash != bytes32(0), "DIDRegistry: identity hash cannot be zero");
        
        record.metadataCID = newMetadataCID;
        record.identityHash = newIdentityHash;
        record.updatedAt = block.timestamp;
        
        emit DIDUpdated(
            didHash,
            did,
            newMetadataCID,
            newIdentityHash,
            block.timestamp
        );
    }
    
    /**
     * @notice Deactivate a DID (soft delete)
     * @param did The full DID string
     */
    function deactivateDID(string calldata did) 
        external 
        didMustExist(keccak256(bytes(did))) 
    {
        bytes32 didHash = keccak256(bytes(did));
        DIDRecord storage record = didRecords[didHash];
        
        require(
            record.registrar == msg.sender || msg.sender == owner,
            "DIDRegistry: not authorized"
        );
        require(record.active, "DIDRegistry: DID already deactivated");
        
        record.active = false;
        record.updatedAt = block.timestamp;
        
        emit DIDDeactivated(didHash, did, block.timestamp);
    }
    
    /**
     * @notice Reactivate a deactivated DID
     * @param did The full DID string
     */
    function reactivateDID(string calldata did) 
        external 
        didMustExist(keccak256(bytes(did))) 
    {
        bytes32 didHash = keccak256(bytes(did));
        DIDRecord storage record = didRecords[didHash];
        
        require(
            record.registrar == msg.sender || msg.sender == owner,
            "DIDRegistry: not authorized"
        );
        require(!record.active, "DIDRegistry: DID already active");
        
        record.active = true;
        record.updatedAt = block.timestamp;
        
        emit DIDReactivated(didHash, did, block.timestamp);
    }
    
    // ============ View Functions ============
    
    /**
     * @notice Get the metadata CID for a DID
     * @param did The full DID string
     * @return metadataCID The IPFS CID of the encrypted metadata
     */
    function getMetadataCID(string calldata did) 
        external 
        view 
        didMustExist(keccak256(bytes(did))) 
        returns (string memory metadataCID) 
    {
        bytes32 didHash = keccak256(bytes(did));
        return didRecords[didHash].metadataCID;
    }
    
    /**
     * @notice Get the full record for a DID
     * @param did The full DID string
     * @return record The full DID record
     */
    function getDIDRecord(string calldata did) 
        external 
        view 
        didMustExist(keccak256(bytes(did))) 
        returns (DIDRecord memory record) 
    {
        bytes32 didHash = keccak256(bytes(did));
        return didRecords[didHash];
    }
    
    /**
     * @notice Check if a DID exists and is active
     * @param did The full DID string
     * @return exists Whether the DID exists
     * @return active Whether the DID is active
     */
    function isDIDActive(string calldata did) 
        external 
        view 
        returns (bool exists, bool active) 
    {
        bytes32 didHash = keccak256(bytes(did));
        exists = didExists[didHash];
        active = exists && didRecords[didHash].active;
    }
    
    /**
     * @notice Verify that a given CID and hash match the stored values
     * @param did The full DID string
     * @param metadataCID The CID to verify
     * @param identityHash The identity hash to verify
     * @return valid Whether the provided values match
     */
    function verifyDID(
        string calldata did,
        string calldata metadataCID,
        bytes32 identityHash
    ) external view didMustExist(keccak256(bytes(did))) returns (bool valid) {
        bytes32 didHash = keccak256(bytes(did));
        DIDRecord memory record = didRecords[didHash];
        
        return record.active &&
               keccak256(bytes(record.metadataCID)) == keccak256(bytes(metadataCID)) &&
               record.identityHash == identityHash;
    }
    
    // ============ Admin Functions ============
    
    /**
     * @notice Transfer ownership (or renounce by setting to address(0))
     * @param newOwner The new owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}

