import { useState } from 'react'

function HistoryPage() {
    const [did, setDid] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (!did.trim()) {
            setError('DID is required')
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

    const formatTimestamp = (timestamp) => {
        try {
            return new Date(timestamp).toLocaleString()
        } catch {
            return timestamp
        }
    }

    const getEventIcon = (eventType) => {
        return eventType === 'registration' ? '🔐' : '🔍'
    }

    const getStatusBadge = (event) => {
        if (event.event_type === 'registration') {
            return <span className="badge badge-info">Registered</span>
        }
        return event.verified
            ? <span className="badge badge-success">Verified</span>
            : <span className="badge badge-error">Failed</span>
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Verification History</h1>
                <p className="page-subtitle">View your identity activity timeline</p>
            </div>

            <div className="card" style={{ marginBottom: '2rem' }}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem' }}>
                    <input
                        type="text"
                        className="form-input"
                        placeholder="Enter DID to lookup..."
                        value={did}
                        onChange={(e) => setDid(e.target.value)}
                        disabled={loading}
                        style={{ flex: 1 }}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading}
                    >
                        {loading ? <span className="loader"></span> : 'Search'}
                    </button>
                </form>
            </div>

            {error && (
                <div className="status status-error">
                    <p>✗ {error}</p>
                </div>
            )}

            {result && (
                <div className="animate-fade-in">
                    <div className="card" style={{ marginBottom: '2rem' }}>
                        <h3 style={{ marginBottom: '1rem' }}>Identity Information</h3>
                        <div style={{ display: 'grid', gap: '0.5rem' }}>
                            <div>
                                <span style={{ color: 'var(--text-secondary)' }}>DID:</span>
                                <div className="did-display" style={{ marginTop: '0.5rem' }}>{result.did}</div>
                            </div>
                            <div style={{ marginTop: '1rem' }}>
                                <span style={{ color: 'var(--text-secondary)' }}>User ID:</span>
                                <span style={{ marginLeft: '0.5rem' }}>{result.user_id}</span>
                            </div>
                            <div>
                                <span style={{ color: 'var(--text-secondary)' }}>Registered:</span>
                                <span style={{ marginLeft: '0.5rem' }}>{formatTimestamp(result.created_at)}</span>
                            </div>
                            {result.registration_tx_hash && (
                                <div style={{ marginTop: '0.5rem' }}>
                                    <p className="tx-hash">
                                        Registration TX: <a href={`https://sepolia.etherscan.io/tx/${result.registration_tx_hash}`} target="_blank" rel="noopener noreferrer">
                                            {result.registration_tx_hash}
                                        </a>
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    <h3 style={{ marginBottom: '1rem' }}>Activity Timeline</h3>

                    {result.timeline && result.timeline.length > 0 ? (
                        <div className="timeline">
                            {result.timeline.map((event, index) => (
                                <div key={index} className="timeline-item">
                                    <div className="timeline-content">
                                        <div className="timeline-header">
                                            <span className="timeline-title">
                                                {getEventIcon(event.event_type)} {event.event_type === 'registration' ? 'Identity Registered' : 'Verification Attempt'}
                                            </span>
                                            {getStatusBadge(event)}
                                        </div>
                                        <div className="timeline-time">{formatTimestamp(event.timestamp)}</div>

                                        {event.event_type === 'verification' && (
                                            <div className="timeline-body" style={{ marginTop: '1rem' }}>
                                                <div className="score-display" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                                                    <div className="score-item" style={{ padding: '0.75rem' }}>
                                                        <div className="score-value" style={{ fontSize: '1rem' }}>{(event.score * 100).toFixed(1)}%</div>
                                                        <div className="score-label">Final</div>
                                                    </div>
                                                    <div className="score-item" style={{ padding: '0.75rem' }}>
                                                        <div className="score-value" style={{ fontSize: '1rem' }}>{(event.face_score * 100).toFixed(1)}%</div>
                                                        <div className="score-label">Face</div>
                                                    </div>
                                                    <div className="score-item" style={{ padding: '0.75rem' }}>
                                                        <div className="score-value" style={{ fontSize: '1rem' }}>{(event.voice_score * 100).toFixed(1)}%</div>
                                                        <div className="score-label">Voice</div>
                                                    </div>
                                                    <div className="score-item" style={{ padding: '0.75rem' }}>
                                                        <div className="score-value" style={{ fontSize: '1rem' }}>{(event.doc_score * 100).toFixed(1)}%</div>
                                                        <div className="score-label">Document</div>
                                                    </div>
                                                </div>

                                                {event.confidence_level && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        <span style={{ color: 'var(--text-muted)' }}>Confidence: </span>
                                                        <span className={`badge ${event.confidence_level === 'VERY_HIGH' ? 'badge-success' : event.confidence_level === 'HIGH' ? 'badge-info' : 'badge-warning'}`}>
                                                            {event.confidence_level}
                                                        </span>
                                                    </div>
                                                )}
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
                                            <div>
                                                <span className="tx-hash">Block: #{event.block_number}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                            <p>No activity recorded yet</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default HistoryPage
