import { useState } from 'react'
import WebcamCapture from '../components/WebcamCapture'
import VoiceRecorder from '../components/VoiceRecorder'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

function VerifyPage() {
    const [did, setDid] = useState('')
    const [files, setFiles] = useState({
        face: null,
        voice: null,
        idDoc: null
    })
    const [errors, setErrors] = useState({})
    const [verifying, setVerifying] = useState(false)
    const [result, setResult] = useState(null)

    // Modal states
    const [showWebcam, setShowWebcam] = useState(false)
    const [showVoiceRecorder, setShowVoiceRecorder] = useState(false)

    const validateFile = (file, type, required = true) => {
        if (!file) return required ? 'File is required' : null

        if (file.size > MAX_FILE_SIZE) {
            return 'File size must be under 10MB'
        }

        if (type === 'image' && !['image/jpeg', 'image/jpg'].includes(file.type)) {
            return 'File must be JPEG format'
        }

        if (type === 'audio') {
            const validTypes = ['audio/wav', 'audio/wave', 'audio/x-wav', 'audio/webm', 'audio/mpeg', 'audio/mp4', 'audio/ogg']
            if (!validTypes.includes(file.type)) {
                return 'Invalid audio format'
            }
        }

        return null
    }

    const handleFileChange = (field, type, required = true) => (e) => {
        const file = e.target.files[0]
        if (file) {
            const error = validateFile(file, type, required)
            setErrors(prev => ({ ...prev, [field]: error }))
            setFiles(prev => ({ ...prev, [field]: error ? null : file }))
        }
    }

    const handleWebcamCapture = (file) => {
        setFiles(prev => ({ ...prev, face: file }))
        setErrors(prev => ({ ...prev, face: null }))
        setShowWebcam(false)
    }

    const handleVoiceCapture = (file) => {
        setFiles(prev => ({ ...prev, voice: file }))
        setErrors(prev => ({ ...prev, voice: null }))
        setShowVoiceRecorder(false)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()

        const newErrors = {
            did: !did ? 'Short code or DID is required' : null,
            face: validateFile(files.face, 'image', true),
            voice: validateFile(files.voice, 'audio', true),
            idDoc: validateFile(files.idDoc, 'image', false)
        }

        setErrors(newErrors)

        if (newErrors.did || newErrors.face || newErrors.voice) {
            return
        }

        setVerifying(true)
        setResult(null)

        const formData = new FormData()
        formData.append('did', did)
        formData.append('face', files.face)
        formData.append('voice', files.voice)
        if (files.idDoc) {
            formData.append('id_doc', files.idDoc)
        }

        try {
            const response = await fetch('/api/verify', {
                method: 'POST',
                body: formData
            })

            const data = await response.json()

            if (response.ok) {
                setResult({ success: true, data })
            } else {
                setResult({ success: false, error: data.detail || 'Verification failed' })
            }
        } catch (error) {
            setResult({ success: false, error: 'Network error. Please try again.' })
        } finally {
            setVerifying(false)
        }
    }

    const getConfidenceBadgeClass = (level) => {
        switch (level) {
            case 'VERY_HIGH': return 'badge badge-success'
            case 'HIGH': return 'badge badge-info'
            case 'MEDIUM': return 'badge badge-warning'
            default: return 'badge badge-error'
        }
    }

    const formatScore = (score) => {
        return (score * 100).toFixed(1) + '%'
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Verify Identity</h1>
                <p className="page-subtitle">Authenticate using decentralized biometric retrieval</p>
            </div>

            {/* Verification Flow Info */}
            <div className="card" style={{ marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(56, 239, 125, 0.05) 0%, rgba(77, 171, 247, 0.05) 100%)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    <span>Blockchain</span>
                    <span style={{ color: 'var(--text-muted)' }}>→</span>
                    <span>IPFS Fetch</span>
                    <span style={{ color: 'var(--text-muted)' }}>→</span>
                    <span>In-Memory Decrypt</span>
                    <span style={{ color: 'var(--text-muted)' }}>→</span>
                    <span>Compare</span>
                    <span style={{ color: 'var(--text-muted)' }}>→</span>
                    <span style={{ color: 'var(--success)' }}>Blockchain Proof</span>
                </div>
            </div>

            <div className="card">
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="did">Identity Code or DID</label>
                        <input
                            id="did"
                            type="text"
                            className="form-input"
                            placeholder="Enter short code (e.g., MZXW6YTB) or full DID"
                            value={did}
                            onChange={(e) => setDid(e.target.value)}
                            disabled={verifying}
                            style={{ 
                                textTransform: did.startsWith('did:') ? 'none' : 'uppercase',
                                fontFamily: 'var(--font-mono)',
                                letterSpacing: '0.1rem'
                            }}
                        />
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                            Enter your <strong>8-character short code</strong>, custom alias, or full DID
                        </div>
                        {errors.did && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.did}</p>}
                    </div>

                    <div className="form-group">
                        <label className="form-label">Live Face Image *</label>
                        <div className={`file-upload ${files.face ? 'has-file' : ''} ${errors.face ? 'error' : ''}`}>
                            <input
                                type="file"
                                className="file-upload-input"
                                accept="image/jpeg,image/jpg"
                                onChange={handleFileChange('face', 'image', true)}
                                disabled={verifying}
                            />
                            <div className="file-upload-icon">📸</div>
                            <div className="file-upload-text">
                                {files.face ? files.face.name : 'Click to upload live face photo'}
                            </div>
                            <div className="file-upload-hint">JPEG only, max 10MB</div>
                        </div>
                        <div className="capture-options">
                            <button
                                type="button"
                                className={`capture-btn ${files.face ? 'active' : ''}`}
                                onClick={() => setShowWebcam(true)}
                                disabled={verifying}
                            >
                                📷 Live Capture
                            </button>
                        </div>
                        {errors.face && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.face}</p>}
                    </div>

                    <div className="form-group">
                        <label className="form-label">Live Voice Sample *</label>
                        <div className={`file-upload ${files.voice ? 'has-file' : ''} ${errors.voice ? 'error' : ''}`}>
                            <input
                                type="file"
                                className="file-upload-input"
                                accept="audio/*"
                                onChange={handleFileChange('voice', 'audio', true)}
                                disabled={verifying}
                            />
                            <div className="file-upload-icon">🎤</div>
                            <div className="file-upload-text">
                                {files.voice ? files.voice.name : 'Click to upload live voice recording'}
                            </div>
                            <div className="file-upload-hint">Audio file, max 10MB</div>
                        </div>
                        <div className="capture-options">
                            <button
                                type="button"
                                className={`capture-btn ${files.voice ? 'active' : ''}`}
                                onClick={() => setShowVoiceRecorder(true)}
                                disabled={verifying}
                            >
                                🎙️ Record Voice
                            </button>
                        </div>
                        {errors.voice && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.voice}</p>}
                    </div>

                    <div className="form-group">
                        <label className="form-label">ID Document (Optional - for enhanced verification)</label>
                        <div className={`file-upload ${files.idDoc ? 'has-file' : ''} ${errors.idDoc ? 'error' : ''}`}>
                            <input
                                type="file"
                                className="file-upload-input"
                                accept="image/jpeg,image/jpg"
                                onChange={handleFileChange('idDoc', 'image', false)}
                                disabled={verifying}
                            />
                            <div className="file-upload-icon">🪪</div>
                            <div className="file-upload-text">
                                {files.idDoc ? files.idDoc.name : 'Click to upload ID document for OCR verification'}
                            </div>
                            <div className="file-upload-hint">JPEG only, max 10MB • Compares OCR text with registered document</div>
                        </div>
                        {errors.idDoc && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.idDoc}</p>}
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-full"
                        disabled={verifying}
                    >
                        {verifying ? (
                            <>
                                <span className="loader"></span>
                                Fetching from IPFS & Verifying...
                            </>
                        ) : (
                            '🔍 Verify Identity'
                        )}
                    </button>
                </form>

                {result && (
                    <div className={`status ${result.success && result.data.verified ? 'status-success' : 'status-error'}`}>
                        {result.success ? (
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                                    <p style={{ fontWeight: 600, fontSize: '1.25rem', margin: 0 }}>
                                        {result.data.verified ? '✓ Identity Verified' : '✗ Verification Failed'}
                                    </p>
                                    <span className={getConfidenceBadgeClass(result.data.confidence_level)}>
                                        {result.data.confidence_level}
                                    </span>
                                </div>

                                {/* IPFS CID Used */}
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>IPFS CID RETRIEVED FROM BLOCKCHAIN</div>
                                    <div className="tx-hash" style={{ wordBreak: 'break-all' }}>
                                        {result.data.metadata_cid}
                                    </div>
                                </div>

                                <div className="score-display">
                                    <div className="score-item">
                                        <div className="score-value">{formatScore(result.data.final_score)}</div>
                                        <div className="score-label">Final Score</div>
                                    </div>
                                    <div className="score-item">
                                        <div className="score-value">{formatScore(result.data.face_score)}</div>
                                        <div className="score-label">Face (40%)</div>
                                    </div>
                                    <div className="score-item">
                                        <div className="score-value">{formatScore(result.data.voice_score)}</div>
                                        <div className="score-label">Voice (35%)</div>
                                    </div>
                                    <div className="score-item">
                                        <div className="score-value">{formatScore(result.data.doc_score)}</div>
                                        <div className="score-label">Document (25%)</div>
                                    </div>
                                </div>

                                {/* Detailed Document Scores */}
                                {(result.data.doc_text_score !== undefined || result.data.doc_face_score !== undefined) && (
                                    <div className="score-display" style={{ marginTop: '0.5rem' }}>
                                        <div className="score-item" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                                            <div className="score-value">{formatScore(result.data.doc_text_score || 0)}</div>
                                            <div className="score-label">OCR Text Match</div>
                                        </div>
                                        <div className="score-item" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                                            <div className="score-value">{formatScore(result.data.doc_face_score || 0)}</div>
                                            <div className="score-label">Doc Face Match</div>
                                        </div>
                                    </div>
                                )}

                                {result.data.tx_hash && (
                                    <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(56, 239, 125, 0.1)', borderRadius: 'var(--radius-sm)' }}>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--success)', marginBottom: '0.25rem' }}>VERIFICATION PROOF LOGGED ON BLOCKCHAIN</div>
                                        <p className="tx-hash">
                                            TX: <a href={`https://sepolia.etherscan.io/tx/${result.data.tx_hash}`} target="_blank" rel="noopener noreferrer">
                                                {result.data.tx_hash}
                                            </a>
                                        </p>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <p>✗ {result.error}</p>
                        )}
                    </div>
                )}
            </div>

            {/* Webcam Modal */}
            {showWebcam && (
                <WebcamCapture
                    onCapture={handleWebcamCapture}
                    onClose={() => setShowWebcam(false)}
                />
            )}

            {/* Voice Recorder Modal */}
            {showVoiceRecorder && (
                <VoiceRecorder
                    onCapture={handleVoiceCapture}
                    onClose={() => setShowVoiceRecorder(false)}
                />
            )}
        </div>
    )
}

export default VerifyPage
