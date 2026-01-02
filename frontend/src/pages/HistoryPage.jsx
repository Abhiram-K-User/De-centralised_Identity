import { useState } from 'react'

function HistoryPage() {
    const [did, setDid] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (!did.trim()) {
            setError('Short code or DID is required')
            return
        }

        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const response = await fetch(`/api/user/${encodeURIComponent(did)}`)
            const data = await response.json()

            if (response.ok) {
                setResult(data)
            } else {
                setError(data.detail || 'Failed to fetch history')
            }
        } catch (err) {
            setError('Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const getEventIcon = (eventType) => {
        return eventType === 'registration' ? '🔐' : '🔍'
    }

    const getStatusBadge = (event) => {
        if (event.event_type === 'registration') {
            return <span className="badge badge-info">Registered</span>
        }
        return event.success
            ? <span className="badge badge-success">Verified</span>
            : <span className="badge badge-error">Failed</span>
    }

    const getConfidenceBadge = (level) => {
        if (!level) return null
        const classes = {
            'VERY_HIGH': 'badge-success',
            'HIGH': 'badge-info',
            'MEDIUM': 'badge-warning',
            'LOW': 'badge-error'
        }
        return <span className={`badge ${classes[level] || 'badge-info'}`}>{level}</span>
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Identity History</h1>
                <p className="page-subtitle">View your on-chain identity activity timeline</p>
            </div>

            {/* Blockchain Query Info */}
            <div className="card" style={{ marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(255, 217, 61, 0.05) 0%, rgba(255, 107, 107, 0.05) 100%)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    <span>⛓️</span>
                    <span>All data queried directly from Ethereum Sepolia blockchain event logs</span>
                    <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>No database used</span>
                </div>
            </div>

            <div className="card" style={{ marginBottom: '2rem' }}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <input
                        type="text"
                        className="form-input"
                        placeholder="Enter short code (e.g., MZXW6YTB) or full DID..."
                        value={did}
                        onChange={(e) => setDid(e.target.value)}
                        disabled={loading}
                        style={{ 
                            flex: 1, 
                            minWidth: '200px',
                            textTransform: did.startsWith('did:') ? 'none' : 'uppercase',
                            fontFamily: 'var(--font-mono)',
                            letterSpacing: '0.05rem'
                        }}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading}
                    >
                        {loading ? <span className="loader"></span> : '🔍 Query Blockchain'}
                    </button>
                </form>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    Enter your <strong>8-character short code</strong>, custom alias, or full DID
                </div>
            </div>

            {error && (
                <div className="status status-error">
                    <p>✗ {error}</p>
                </div>
            )}

            {result && (
                <div className="animate-fade-in">
                    {/* Identity Information Card */}
                    <div className="card" style={{ marginBottom: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                            <h3 style={{ margin: 0 }}>Identity Record</h3>
                            {result.active ? (
                                <span className="badge badge-success">Active</span>
                            ) : (
                                <span className="badge badge-error">Inactive</span>
                            )}
                        </div>
                        
                        <div style={{ display: 'grid', gap: '1rem' }}>
                            {/* DID */}
                            <div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>DECENTRALIZED IDENTIFIER</div>
                                <div className="did-display">{result.did}</div>
                            </div>

                            {/* IPFS CID */}
                            <div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>IPFS METADATA CID</div>
                                <div className="did-display" style={{ background: 'rgba(118, 75, 162, 0.2)' }}>
                                    {result.metadata_cid}
                                </div>
                                <a 
                                    href={result.ipfs_gateway_url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    style={{ fontSize: '0.75rem', color: 'var(--info)' }}
                                >
                                    View encrypted metadata on IPFS →
                                </a>
                            </div>

                            {/* Identity Hash */}
                            <div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>ON-CHAIN IDENTITY HASH</div>
                                <div className="tx-hash" style={{ wordBreak: 'break-all' }}>
                                    0x{result.identity_hash}
                                </div>
                            </div>

                            {/* Stats Row */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '0.5rem' }}>
                                <div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Registered</div>
                                    <div style={{ fontWeight: 500 }}>{result.registered_at_formatted}</div>
                                </div>
                                <div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Registrar</div>
                                    <div className="tx-hash" style={{ fontSize: '0.75rem' }}>
                                        <a href={`https://sepolia.etherscan.io/address/${result.registrar}`} target="_blank" rel="noopener noreferrer">
                                            {result.registrar?.slice(0, 10)}...{result.registrar?.slice(-8)}
                                        </a>
                                    </div>
                                </div>
                                <div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Verifications</div>
                                    <div style={{ fontWeight: 500, color: 'var(--info)' }}>{result.verification_count}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Timeline */}
                    <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>⛓️</span>
                        <span>Blockchain Event Timeline</span>
                    </h3>

                    {result.timeline && result.timeline.length > 0 ? (
                        <div className="timeline">
                            {result.timeline.map((event, index) => (
                                <div key={index} className="timeline-item">
                                    <div className="timeline-content">
                                        <div className="timeline-header">
                                            <span className="timeline-title">
                                                {getEventIcon(event.event_type)} {event.event_type === 'registration' ? 'Identity Registered' : 'Verification Attempt'}
                                            </span>
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                {getStatusBadge(event)}
                                                {event.confidence_level && getConfidenceBadge(event.confidence_level)}
                                            </div>
                                        </div>
                                        <div className="timeline-time">{event.timestamp_formatted}</div>

                                        {event.event_type === 'registration' && event.metadata_cid && (
                                            <div className="timeline-body" style={{ marginTop: '0.75rem' }}>
                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>IPFS CID:</div>
                                                <div className="tx-hash">{event.metadata_cid}</div>
                                            </div>
                                        )}

                                        {event.event_type === 'verification' && (
                                            <div className="timeline-body" style={{ marginTop: '0.75rem' }}>
                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Verification Hash:</div>
                                                <div className="tx-hash" style={{ wordBreak: 'break-all' }}>
                                                    0x{event.verification_hash}
                                                </div>
                                            </div>
                                        )}

                                        {event.tx_hash && (
                                            <div style={{ marginTop: '0.75rem' }}>
                                                <p className="tx-hash">
                                                    TX: <a href={`https://sepolia.etherscan.io/tx/${event.tx_hash}`} target="_blank" rel="noopener noreferrer">
                                                        {event.tx_hash.slice(0, 20)}...{event.tx_hash.slice(-8)}
                                                    </a>
                                                </p>
                                            </div>
                                        )}

                                        {event.block_number && (
                                            <div style={{ marginTop: '0.25rem' }}>
                                                <span className="tx-hash">
                                                    Block: <a href={`https://sepolia.etherscan.io/block/${event.block_number}`} target="_blank" rel="noopener noreferrer">
                                                        #{event.block_number}
                                                    </a>
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                            <p>No blockchain events recorded yet</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default HistoryPage
