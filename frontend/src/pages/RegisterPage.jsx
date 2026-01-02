import { useState } from 'react'
import WebcamCapture from '../components/WebcamCapture'
import VoiceRecorder from '../components/VoiceRecorder'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

function RegisterPage() {
    const [files, setFiles] = useState({
        face: null,
        voice: null,
        idDoc: null
    })
    const [errors, setErrors] = useState({})
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [result, setResult] = useState(null)

    // Modal states
    const [showWebcam, setShowWebcam] = useState(false)
    const [showVoiceRecorder, setShowVoiceRecorder] = useState(false)

    const validateFile = (file, type) => {
        if (!file) return 'File is required'

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

    const handleFileChange = (field, type) => (e) => {
        const file = e.target.files[0]
        if (file) {
            const error = validateFile(file, type)
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
            face: validateFile(files.face, 'image'),
            voice: validateFile(files.voice, 'audio'),
            idDoc: validateFile(files.idDoc, 'image')
        }

        setErrors(newErrors)

        if (Object.values(newErrors).some(e => e)) {
            return
        }

        setUploading(true)
        setProgress(0)
        setResult(null)

        const formData = new FormData()
        formData.append('face', files.face)
        formData.append('voice', files.voice)
        formData.append('id_doc', files.idDoc)

        try {
            const xhr = new XMLHttpRequest()

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100)
                    setProgress(percent)
                }
            })

            xhr.onload = () => {
                setUploading(false)
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText)
                    setResult({ success: true, data: response })
                } else {
                    let errorMessage = 'Registration failed'
                    try {
                        const response = JSON.parse(xhr.responseText)
                        errorMessage = response.detail || errorMessage
                    } catch { }
                    setResult({ success: false, error: errorMessage })
                }
            }

            xhr.onerror = () => {
                setUploading(false)
                setResult({ success: false, error: 'Network error. Please try again.' })
            }

            xhr.open('POST', '/api/register')
            xhr.send(formData)

        } catch (error) {
            setUploading(false)
            setResult({ success: false, error: error.message })
        }
    }

    const formatBytes = (bytes) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Register Identity</h1>
                <p className="page-subtitle">Create your decentralized biometric identity on IPFS & Ethereum</p>
            </div>

            {/* Architecture Info Card */}
            <div className="card decentralized-info" style={{ marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <span style={{ fontSize: '2rem' }}>⬡</span>
                    <h3 style={{ margin: 0 }}>Fully Decentralized Architecture</h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', fontSize: '0.875rem' }}>
                    <div>
                        <div style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Storage</div>
                        <div style={{ fontWeight: 600 }}>IPFS (Pinata)</div>
                    </div>
                    <div>
                        <div style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>State</div>
                        <div style={{ fontWeight: 600 }}>Ethereum Sepolia</div>
                    </div>
                    <div>
                        <div style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Database</div>
                        <div style={{ fontWeight: 600, color: 'var(--success)' }}>None (Eliminated)</div>
                    </div>
                </div>
            </div>

            <div className="card">
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Face Image</label>
                        <div className={`file-upload ${files.face ? 'has-file' : ''} ${errors.face ? 'error' : ''}`}>
                            <input
                                type="file"
                                className="file-upload-input"
                                accept="image/jpeg,image/jpg"
                                onChange={handleFileChange('face', 'image')}
                                disabled={uploading}
                            />
                            <div className="file-upload-icon">📸</div>
                            <div className="file-upload-text">
                                {files.face ? files.face.name : 'Click to upload face photo'}
                            </div>
                            <div className="file-upload-hint">JPEG only, max 10MB • Extracts 512-D ArcFace embedding</div>
                        </div>
                        <div className="capture-options">
                            <button
                                type="button"
                                className={`capture-btn ${files.face ? 'active' : ''}`}
                                onClick={() => setShowWebcam(true)}
                                disabled={uploading}
                            >
                                📷 Live Capture
                            </button>
                        </div>
                        {errors.face && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.face}</p>}
                    </div>

                    <div className="form-group">
                        <label className="form-label">Voice Sample</label>
                        <div className={`file-upload ${files.voice ? 'has-file' : ''} ${errors.voice ? 'error' : ''}`}>
                            <input
                                type="file"
                                className="file-upload-input"
                                accept="audio/*"
                                onChange={handleFileChange('voice', 'audio')}
                                disabled={uploading}
                            />
                            <div className="file-upload-icon">🎤</div>
                            <div className="file-upload-text">
                                {files.voice ? files.voice.name : 'Click to upload voice recording'}
                            </div>
                            <div className="file-upload-hint">Audio file, max 10MB • Extracts 192-D ECAPA-TDNN embedding</div>
                        </div>
                        <div className="capture-options">
                            <button
                                type="button"
                                className={`capture-btn ${files.voice ? 'active' : ''}`}
                                onClick={() => setShowVoiceRecorder(true)}
                                disabled={uploading}
                            >
                                🎙️ Record Voice
                            </button>
                        </div>
                        {errors.voice && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.voice}</p>}
                    </div>

                    <div className="form-group">
                        <label className="form-label">ID Document</label>
                        <div className={`file-upload ${files.idDoc ? 'has-file' : ''} ${errors.idDoc ? 'error' : ''}`}>
                            <input
                                type="file"
                                className="file-upload-input"
                                accept="image/jpeg,image/jpg"
                                onChange={handleFileChange('idDoc', 'image')}
                                disabled={uploading}
                            />
                            <div className="file-upload-icon">🪪</div>
                            <div className="file-upload-text">
                                {files.idDoc ? files.idDoc.name : 'Click to upload ID document'}
                            </div>
                            <div className="file-upload-hint">JPEG only, max 10MB • Extracts 640-D embedding + OCR text</div>
                        </div>
                        {errors.idDoc && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.idDoc}</p>}
                    </div>

                    {uploading && (
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                <span>Processing biometrics → Encrypting → Uploading to IPFS...</span>
                                <span>{progress}%</span>
                            </div>
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                            </div>
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary btn-full"
                        disabled={uploading}
                    >
                        {uploading ? (
                            <>
                                <span className="loader"></span>
                                Processing & Anchoring on Blockchain...
                            </>
                        ) : (
                            '⬡ Register Decentralized Identity'
                        )}
                    </button>
                </form>

                {result && (
                    <div className={`status ${result.success ? 'status-success' : 'status-error'}`}>
                        {result.success ? (
                            <div>
                                <p style={{ fontWeight: 600, marginBottom: '1rem', fontSize: '1.25rem' }}>✓ Registration Successful!</p>
                                
                                {/* Short Code - Prominently displayed */}
                                {result.data.short_code && (
                                    <div style={{ marginBottom: '1.5rem', padding: '1.5rem', background: 'linear-gradient(135deg, rgba(56, 239, 125, 0.2) 0%, rgba(102, 126, 234, 0.2) 100%)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                                        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.5rem' }}>YOUR SHORT CODE (Easy to Remember!)</div>
                                        <div style={{ 
                                            fontSize: '2.5rem', 
                                            fontWeight: 700, 
                                            fontFamily: 'var(--font-mono)', 
                                            letterSpacing: '0.3rem',
                                            background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
                                            WebkitBackgroundClip: 'text',
                                            WebkitTextFillColor: 'transparent'
                                        }}>
                                            {result.data.short_code.toUpperCase()}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                                            Use this instead of your long DID for verification!
                                        </div>
                                    </div>
                                )}

                                {/* DID */}
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>FULL DECENTRALIZED IDENTIFIER (DID)</div>
                                    <div className="did-display" style={{ fontSize: '0.7rem' }}>{result.data.did}</div>
                                </div>

                                {/* IPFS CID */}
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>IPFS CONTENT IDENTIFIER (CID)</div>
                                    <div className="did-display" style={{ background: 'rgba(118, 75, 162, 0.2)' }}>
                                        {result.data.ipfs_cid}
                                    </div>
                                    <a 
                                        href={result.data.ipfs_gateway_url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        style={{ fontSize: '0.75rem', color: 'var(--info)' }}
                                    >
                                        View on IPFS Gateway →
                                    </a>
                                </div>

                                {/* Identity Hash */}
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>IDENTITY HASH (32 bytes on-chain)</div>
                                    <div className="tx-hash" style={{ wordBreak: 'break-all' }}>
                                        0x{result.data.identity_hash}
                                    </div>
                                </div>

                                {/* Data Reduction Stats */}
                                {result.data.data_reduction && (
                                    <div style={{ marginBottom: '1rem' }}>
                                        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.5rem' }}>DATA REDUCTION PIPELINE</div>
                                        <div className="score-display">
                                            <div className="score-item">
                                                <div className="score-value">{result.data.data_reduction.raw_total_mb} MB</div>
                                                <div className="score-label">Raw Input</div>
                                            </div>
                                            <div className="score-item">
                                                <div className="score-value">{result.data.data_reduction.encrypted_metadata_kb} KB</div>
                                                <div className="score-label">IPFS Metadata</div>
                                            </div>
                                            <div className="score-item">
                                                <div className="score-value">{result.data.data_reduction.blockchain_hash_bytes} B</div>
                                                <div className="score-label">Blockchain Hash</div>
                                            </div>
                                            <div className="score-item" style={{ background: 'rgba(56, 239, 125, 0.1)' }}>
                                                <div className="score-value" style={{ color: 'var(--success)', WebkitTextFillColor: 'var(--success)' }}>
                                                    {result.data.data_reduction.reduction_raw_to_blockchain}
                                                </div>
                                                <div className="score-label">Total Reduction</div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Transaction Hash */}
                                {result.data.tx_hash && (
                                    <div style={{ marginTop: '1rem' }}>
                                        <p className="tx-hash">
                                            Blockchain TX: <a href={`https://sepolia.etherscan.io/tx/${result.data.tx_hash}`} target="_blank" rel="noopener noreferrer">
                                                {result.data.tx_hash}
                                            </a>
                                        </p>
                                    </div>
                                )}

                                {!result.data.tx_hash && (
                                    <div style={{ marginTop: '1rem', padding: '0.5rem', background: 'rgba(255, 217, 61, 0.1)', borderRadius: 'var(--radius-sm)', fontSize: '0.875rem', color: 'var(--warning)' }}>
                                        ⚠ Blockchain not configured - identity stored on IPFS only
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

export default RegisterPage
