// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title VerificationLog
 * @notice Immutable log of identity verification events for DID++ System
 * @dev Records permanent, auditable proofs of successful identity verifications
 * 
 * Design Principles:
 * - Append-only: Verification records cannot be modified or deleted
 * - Gas-efficient: Uses events for historical queries, minimal on-chain storage
 * - Trustless: Anyone can verify the authenticity of verification claims
 */
contract VerificationLog {
    
    // ============ State Variables ============
    
    /// @notice Owner of the contract
    address public owner;
    
    /// @notice Reference to the DID Registry contract
    address public didRegistry;
    
    /// @notice Total number of verifications logged
    uint256 public totalVerifications;
    
    /// @notice Mapping from DID hash to verification count
    mapping(bytes32 => uint256) public verificationCounts;
    
    /// @notice Mapping from verification hash to existence check
    mapping(bytes32 => bool) public verificationExists;
    
    /// @notice Mapping from DID hash to list of verification hashes
    mapping(bytes32 => bytes32[]) public didVerifications;
    
    // ============ Structs ============
    
    /// @notice Verification record structure
    struct VerificationRecord {
        bytes32 didHash;           // Hash of the DID that was verified
        bytes32 verificationHash;  // SHA-256 hash of verification payload
        bytes32 metadataCIDHash;   // Hash of the IPFS CID used for verification
        uint256 timestamp;         // Block timestamp of verification
        uint256 blockNumber;       // Block number for reference
        address verifier;          // Address that performed verification
        uint8 confidenceLevel;     // 0=LOW, 1=MEDIUM, 2=HIGH, 3=VERY_HIGH
        bool success;              // Whether verification was successful
    }
    
    /// @notice Input struct for logging verification (reduces stack depth)
    struct VerificationInput {
        string did;
        bytes32 verificationHash;
        string metadataCID;
        uint8 confidenceLevel;
        bool success;
    }
    
    /// @notice Mapping from verification hash to record
    mapping(bytes32 => VerificationRecord) public verificationRecords;
    
    // ============ Events ============
    
    /// @notice Emitted when a verification is logged
    event VerificationLogged(
        bytes32 indexed didHash,
        string did,
        bytes32 indexed verificationHash,
        string metadataCID,
        uint8 confidenceLevel,
        bool success,
        address indexed verifier,
        uint256 timestamp,
        uint256 blockNumber
    );
    
    /// @notice Emitted when a batch of verifications is logged
    event BatchVerificationLogged(
        uint256 count,
        uint256 timestamp
    );
    
    // ============ Modifiers ============
    
    modifier onlyOwner() {
        require(msg.sender == owner, "VerificationLog: caller is not owner");
        _;
    }
    
    // ============ Constructor ============
    
    constructor(address _didRegistry) {
        owner = msg.sender;
        didRegistry = _didRegistry;
    }
    
    // ============ External Functions ============
    
    /**
     * @notice Log a successful identity verification
     * @param did The full DID string that was verified
     * @param verificationHash SHA-256 hash of the verification payload
     * @param metadataCID IPFS CID that was used for verification
     * @param confidenceLevel Confidence level (0=LOW, 1=MEDIUM, 2=HIGH, 3=VERY_HIGH)
     * @param success Whether the verification was successful
     * @return recordHash The unique hash identifying this verification record
     */
    function logVerification(
        string calldata did,
        bytes32 verificationHash,
        string calldata metadataCID,
        uint8 confidenceLevel,
        bool success
    ) external returns (bytes32 recordHash) {
        require(bytes(did).length > 0, "VerificationLog: DID cannot be empty");
        require(verificationHash != bytes32(0), "VerificationLog: hash cannot be zero");
        require(confidenceLevel <= 3, "VerificationLog: invalid confidence level");
        
        bytes32 didHash = keccak256(bytes(did));
        bytes32 metadataCIDHash = keccak256(bytes(metadataCID));
        
        // Create unique record hash
        recordHash = keccak256(abi.encodePacked(
            didHash,
            verificationHash,
            block.timestamp,
            msg.sender
        ));
        
        require(!verificationExists[recordHash], "VerificationLog: duplicate record");
        
        // Store record
        _storeRecord(
            recordHash,
            didHash,
            verificationHash,
            metadataCIDHash,
            confidenceLevel,
            success
        );
        
        emit VerificationLogged(
            didHash,
            did,
            verificationHash,
            metadataCID,
            confidenceLevel,
            success,
            msg.sender,
            block.timestamp,
            block.number
        );
        
        return recordHash;
    }
    
    /**
     * @notice Internal function to store verification record (reduces stack depth)
     */
    function _storeRecord(
        bytes32 recordHash,
        bytes32 didHash,
        bytes32 verificationHash,
        bytes32 metadataCIDHash,
        uint8 confidenceLevel,
        bool success
    ) internal {
        verificationRecords[recordHash] = VerificationRecord({
            didHash: didHash,
            verificationHash: verificationHash,
            metadataCIDHash: metadataCIDHash,
            timestamp: block.timestamp,
            blockNumber: block.number,
            verifier: msg.sender,
            confidenceLevel: confidenceLevel,
            success: success
        });
        
        verificationExists[recordHash] = true;
        didVerifications[didHash].push(recordHash);
        verificationCounts[didHash]++;
        totalVerifications++;
    }
    
    /**
     * @notice Log verification using struct input (gas efficient alternative)
     * @param input VerificationInput struct containing all parameters
     * @return recordHash The unique hash identifying this verification record
     */
    function logVerificationStruct(
        VerificationInput calldata input
    ) external returns (bytes32 recordHash) {
        require(bytes(input.did).length > 0, "VerificationLog: DID cannot be empty");
        require(input.verificationHash != bytes32(0), "VerificationLog: hash cannot be zero");
        require(input.confidenceLevel <= 3, "VerificationLog: invalid confidence level");
        
        bytes32 didHash = keccak256(bytes(input.did));
        bytes32 metadataCIDHash = keccak256(bytes(input.metadataCID));
        
        recordHash = keccak256(abi.encodePacked(
            didHash,
            input.verificationHash,
            block.timestamp,
            msg.sender
        ));
        
        require(!verificationExists[recordHash], "VerificationLog: duplicate record");
        
        _storeRecord(
            recordHash,
            didHash,
            input.verificationHash,
            metadataCIDHash,
            input.confidenceLevel,
            input.success
        );
        
        emit VerificationLogged(
            didHash,
            input.did,
            input.verificationHash,
            input.metadataCID,
            input.confidenceLevel,
            input.success,
            msg.sender,
            block.timestamp,
            block.number
        );
        
        return recordHash;
    }
    
    /**
     * @notice Log multiple verifications in a single transaction (gas efficient)
     * @param inputs Array of VerificationInput structs
     */
    function batchLogVerifications(
        VerificationInput[] calldata inputs
    ) external {
        require(inputs.length <= 50, "VerificationLog: batch too large");
        
        uint256 count = 0;
        
        for (uint256 i = 0; i < inputs.length; i++) {
            if (_processVerification(inputs[i])) {
                count++;
            }
        }
        
        emit BatchVerificationLogged(count, block.timestamp);
    }
    
    /**
     * @notice Internal function to process a single verification in batch
     * @param input The verification input
     * @return success Whether the verification was processed
     */
    function _processVerification(
        VerificationInput calldata input
    ) internal returns (bool) {
        if (bytes(input.did).length == 0) return false;
        if (input.verificationHash == bytes32(0)) return false;
        if (input.confidenceLevel > 3) return false;
        
        bytes32 didHash = keccak256(bytes(input.did));
        bytes32 metadataCIDHash = keccak256(bytes(input.metadataCID));
        
        bytes32 recordHash = keccak256(abi.encodePacked(
            didHash,
            input.verificationHash,
            block.timestamp,
            msg.sender,
            totalVerifications // Use counter to ensure uniqueness in batch
        ));
        
        if (verificationExists[recordHash]) return false;
        
        _storeRecord(
            recordHash,
            didHash,
            input.verificationHash,
            metadataCIDHash,
            input.confidenceLevel,
            input.success
        );
        
        emit VerificationLogged(
            didHash,
            input.did,
            input.verificationHash,
            input.metadataCID,
            input.confidenceLevel,
            input.success,
            msg.sender,
            block.timestamp,
            block.number
        );
        
        return true;
    }
    
    // ============ View Functions ============
    
    /**
     * @notice Get verification count for a DID
     * @param did The full DID string
     * @return count Number of verifications for this DID
     */
    function getVerificationCount(string calldata did) 
        external 
        view 
        returns (uint256 count) 
    {
        bytes32 didHash = keccak256(bytes(did));
        return verificationCounts[didHash];
    }
    
    /**
     * @notice Get all verification record hashes for a DID
     * @param did The full DID string
     * @return recordHashes Array of verification record hashes
     */
    function getVerificationHashes(string calldata did) 
        external 
        view 
        returns (bytes32[] memory recordHashes) 
    {
        bytes32 didHash = keccak256(bytes(did));
        return didVerifications[didHash];
    }
    
    /**
     * @notice Get a specific verification record
     * @param recordHash The unique record hash
     * @return record The verification record
     */
    function getVerificationRecord(bytes32 recordHash) 
        external 
        view 
        returns (VerificationRecord memory record) 
    {
        require(verificationExists[recordHash], "VerificationLog: record not found");
        return verificationRecords[recordHash];
    }
    
    /**
     * @notice Get recent verifications for a DID
     * @param did The full DID string
     * @param limit Maximum number of records to return
     * @return records Array of verification records
     */
    function getRecentVerifications(string calldata did, uint256 limit) 
        external 
        view 
        returns (VerificationRecord[] memory records) 
    {
        bytes32 didHash = keccak256(bytes(did));
        bytes32[] storage hashes = didVerifications[didHash];
        
        uint256 count = hashes.length < limit ? hashes.length : limit;
        records = new VerificationRecord[](count);
        
        // Return most recent first
        for (uint256 i = 0; i < count; i++) {
            uint256 idx = hashes.length - 1 - i;
            records[i] = verificationRecords[hashes[idx]];
        }
        
        return records;
    }
    
    /**
     * @notice Verify that a verification record is authentic
     * @param recordHash The record hash to verify
     * @param did The expected DID
     * @param verificationHash The expected verification hash
     * @return valid Whether the record is authentic
     */
    function verifyRecord(
        bytes32 recordHash,
        string calldata did,
        bytes32 verificationHash
    ) external view returns (bool valid) {
        if (!verificationExists[recordHash]) {
            return false;
        }
        
        VerificationRecord storage record = verificationRecords[recordHash];
        bytes32 expectedDidHash = keccak256(bytes(did));
        
        return record.didHash == expectedDidHash &&
               record.verificationHash == verificationHash;
    }
    
    // ============ Admin Functions ============
    
    /**
     * @notice Update the DID Registry address
     * @param _didRegistry New registry address
     */
    function setDIDRegistry(address _didRegistry) external onlyOwner {
        didRegistry = _didRegistry;
    }
    
    /**
     * @notice Transfer ownership
     * @param newOwner The new owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}
