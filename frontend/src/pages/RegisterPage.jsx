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

    return (
        <div className="page">
            {/* Hero Header */}
            <div className="page-header">
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    marginBottom: '1rem',
                    padding: '0.5rem 1rem',
                    background: 'rgba(99, 102, 241, 0.1)',
                    borderRadius: 'var(--radius-full)',
                    border: '1px solid rgba(99, 102, 241, 0.2)'
                }}>
                    <span style={{ fontSize: '1.25rem' }}>🔐</span>
                    <span style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--primary-light)',
                        fontWeight: '600',
                        letterSpacing: '1px',
                        textTransform: 'uppercase'
                    }}>Create Your Identity</span>
                </div>
                <h1 className="page-title">Register Identity</h1>
                <p className="page-subtitle">Create your decentralized biometric identity secured by IPFS & Ethereum blockchain</p>
            </div>

            {/* Architecture Info Card */}
            <div className="card decentralized-info" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                    <span style={{
                        fontSize: '1.75rem',
                        filter: 'drop-shadow(0 0 10px rgba(99, 102, 241, 0.5))'
                    }}>⬡</span>
                    <div>
                        <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: '700' }}>Fully Decentralized Architecture</h3>
                        <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>No central database • All data on-chain</p>
                    </div>
                </div>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '1rem',
                    fontSize: '0.875rem',
                    borderTop: '1px solid var(--border-color)',
                    paddingTop: '1rem'
                }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{
                            fontSize: '1.5rem',
                            marginBottom: '0.25rem'
                        }}>📦</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Storage</div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>IPFS</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{
                            fontSize: '1.5rem',
                            marginBottom: '0.25rem'
                        }}>⛓️</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Blockchain</div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Ethereum</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{
                            fontSize: '1.5rem',
                            marginBottom: '0.25rem'
                        }}>🚫</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Database</div>
                        <div style={{ fontWeight: 600, color: 'var(--success)' }}>None</div>
                    </div>
                </div>
            </div>

            {/* Main Registration Card */}
            <div className="card">
                <form onSubmit={handleSubmit}>
                    {/* Step Indicator */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        marginBottom: '2rem',
                        padding: '1rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)'
                    }}>
                        {[
                            { icon: '📸', label: 'Face', active: files.face },
                            { icon: '🎤', label: 'Voice', active: files.voice },
                            { icon: '🪪', label: 'ID Doc', active: files.idDoc }
                        ].map((step, index) => (
                            <div key={step.label} style={{
                                display: 'contents'
                            }}>
                                {/* Step icon and label */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    flexShrink: 0
                                }}>
                                    <div style={{
                                        width: '36px',
                                        height: '36px',
                                        borderRadius: '50%',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        background: step.active
                                            ? 'linear-gradient(135deg, var(--success) 0%, #22d3ee 100%)'
                                            : 'rgba(255, 255, 255, 0.05)',
                                        border: step.active
                                            ? 'none'
                                            : '1px solid var(--border-color)',
                                        fontSize: step.active ? '0.9rem' : '1rem',
                                        transition: 'all 0.3s ease',
                                        boxShadow: step.active ? '0 4px 15px rgba(34, 197, 94, 0.4)' : 'none'
                                    }}>
                                        {step.active ? '✓' : step.icon}
                                    </div>
                                    <span style={{
                                        fontSize: 'var(--font-size-xs)',
                                        color: step.active ? 'var(--success-light)' : 'var(--text-muted)',
                                        fontWeight: step.active ? '600' : '400'
                                    }}>{step.label}</span>
                                </div>
                                {/* Connector line */}
                                {index < 2 && (
                                    <div style={{
                                        flex: 1,
                                        height: '2px',
                                        background: files.face && index === 0 || files.voice && index === 1
                                            ? 'var(--primary-gradient)'
                                            : 'var(--border-color)',
                                        margin: '0 1rem',
                                        borderRadius: '1px'
                                    }} />
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Face Upload */}
                    <div className="form-group">
                        <label className="form-label">
                            <span>📸</span>
                            <span>Face Image</span>
                            <span style={{
                                marginLeft: 'auto',
                                fontSize: 'var(--font-size-xs)',
                                color: 'var(--text-muted)',
                                fontWeight: '400'
                            }}>512-D FaceNet</span>
                        </label>
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
                                {files.face ? files.face.name : 'Click to upload or drag and drop'}
                            </div>
                            <div className="file-upload-hint">JPEG format • Max 10MB</div>
                        </div>
                        <div className="capture-options">
                            <button
                                type="button"
                                className={`capture-btn ${files.face ? 'active' : ''}`}
                                onClick={() => setShowWebcam(true)}
                                disabled={uploading}
                            >
                                📷 Use Camera
                            </button>
                        </div>
                        {errors.face && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.75rem' }}>{errors.face}</p>}
                    </div>

                    {/* Voice Upload */}
                    <div className="form-group">
                        <label className="form-label">
                            <span>🎤</span>
                            <span>Voice Sample</span>
                            <span style={{
                                marginLeft: 'auto',
                                fontSize: 'var(--font-size-xs)',
                                color: 'var(--text-muted)',
                                fontWeight: '400'
                            }}>192-D ECAPA-TDNN</span>
                        </label>
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
                                {files.voice ? files.voice.name : 'Click to upload or drag and drop'}
                            </div>
                            <div className="file-upload-hint">Any audio format • Max 10MB</div>
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
                        {errors.voice && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.75rem' }}>{errors.voice}</p>}
                    </div>

                    {/* ID Document Upload */}
                    <div className="form-group">
                        <label className="form-label">
                            <span>🪪</span>
                            <span>ID Document</span>
                            <span style={{
                                marginLeft: 'auto',
                                fontSize: 'var(--font-size-xs)',
                                color: 'var(--text-muted)',
                                fontWeight: '400'
                            }}>640-D + OCR</span>
                        </label>
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
                                {files.idDoc ? files.idDoc.name : 'Click to upload or drag and drop'}
                            </div>
                            <div className="file-upload-hint">JPEG format • Max 10MB</div>
                        </div>
                        {errors.idDoc && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.75rem' }}>{errors.idDoc}</p>}
                    </div>

                    {/* Progress Bar */}
                    {uploading && (
                        <div style={{ marginBottom: '1.5rem' }}>
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                marginBottom: '0.5rem',
                                fontSize: 'var(--font-size-sm)'
                            }}>
                                <span style={{ color: 'var(--text-secondary)' }}>
                                    Processing biometrics → IPFS upload...
                                </span>
                                <span style={{
                                    fontWeight: '600',
                                    color: 'var(--primary-light)'
                                }}>{progress}%</span>
                            </div>
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                            </div>
                        </div>
                    )}

                    {/* Submit Button */}
                    <button
                        type="submit"
                        className="btn btn-primary btn-full"
                        disabled={uploading}
                    >
                        {uploading ? (
                            <>
                                <span className="loader"></span>
                                Anchoring on Blockchain...
                            </>
                        ) : (
                            <>
                                <span style={{ fontSize: '1.1rem' }}>⬡</span>
                                Create Decentralized Identity
                            </>
                        )}
                    </button>
                </form>

                {/* Result Display */}
                {result && (
                    <div className={`status ${result.success ? 'status-success' : 'status-error'}`}>
                        {result.success ? (
                            <div>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    marginBottom: '1.5rem'
                                }}>
                                    <div style={{
                                        width: '48px',
                                        height: '48px',
                                        borderRadius: '50%',
                                        background: 'linear-gradient(135deg, var(--success) 0%, #22d3ee 100%)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '1.5rem',
                                        boxShadow: '0 4px 20px rgba(34, 197, 94, 0.4)'
                                    }}>✓</div>
                                    <div>
                                        <p style={{ fontWeight: 700, fontSize: '1.25rem', margin: 0 }}>Registration Successful!</p>
                                        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 0 }}>Your identity is now on the blockchain</p>
                                    </div>
                                </div>

                                {/* Short Code - Prominently displayed */}
                                {result.data.short_code && (
                                    <div style={{
                                        marginBottom: '1.5rem',
                                        padding: '1.5rem',
                                        background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%)',
                                        borderRadius: 'var(--radius-lg)',
                                        textAlign: 'center',
                                        border: '1px solid rgba(34, 197, 94, 0.3)'
                                    }}>
                                        <div style={{
                                            color: 'var(--text-muted)',
                                            fontSize: '0.7rem',
                                            marginBottom: '0.5rem',
                                            textTransform: 'uppercase',
                                            letterSpacing: '1px'
                                        }}>Your Short Code</div>
                                        <div style={{
                                            fontSize: '2.5rem',
                                            fontWeight: 800,
                                            fontFamily: 'var(--font-mono)',
                                            letterSpacing: '0.4rem',
                                            background: 'linear-gradient(135deg, var(--success-light) 0%, var(--primary-light) 100%)',
                                            WebkitBackgroundClip: 'text',
                                            WebkitTextFillColor: 'transparent'
                                        }}>
                                            {result.data.short_code.toUpperCase()}
                                        </div>
                                        <div style={{
                                            fontSize: 'var(--font-size-sm)',
                                            color: 'var(--text-secondary)',
                                            marginTop: '0.75rem'
                                        }}>
                                            Use this for quick verification
                                        </div>
                                    </div>
                                )}

                                {/* DID */}
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{
                                        color: 'var(--text-muted)',
                                        fontSize: '0.65rem',
                                        marginBottom: '0.5rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.5px'
                                    }}>Decentralized Identifier (DID)</div>
                                    <div className="did-display" style={{ fontSize: '0.7rem' }}>{result.data.did}</div>
                                </div>

                                {/* IPFS CID */}
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{
                                        color: 'var(--text-muted)',
                                        fontSize: '0.65rem',
                                        marginBottom: '0.5rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.5px'
                                    }}>IPFS Content Identifier</div>
                                    <div className="did-display" style={{ background: 'rgba(139, 92, 246, 0.1)', borderColor: 'rgba(139, 92, 246, 0.3)' }}>
                                        {result.data.ipfs_cid}
                                    </div>
                                    <a
                                        href={result.data.ipfs_gateway_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{
                                            fontSize: '0.75rem',
                                            color: 'var(--info-light)',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            marginTop: '0.5rem'
                                        }}
                                    >
                                        View on IPFS Gateway <span>→</span>
                                    </a>
                                </div>

                                {/* Data Reduction Stats */}
                                {result.data.data_reduction && (
                                    <div style={{ marginBottom: '1rem' }}>
                                        <div style={{
                                            color: 'var(--text-muted)',
                                            fontSize: '0.65rem',
                                            marginBottom: '0.75rem',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>Data Reduction</div>
                                        <div className="score-display">
                                            <div className="score-item">
                                                <div className="score-value">{result.data.data_reduction.raw_total_mb} MB</div>
                                                <div className="score-label">Raw Input</div>
                                            </div>
                                            <div className="score-item">
                                                <div className="score-value">{result.data.data_reduction.encrypted_metadata_kb} KB</div>
                                                <div className="score-label">IPFS Data</div>
                                            </div>
                                            <div className="score-item">
                                                <div className="score-value">{result.data.data_reduction.blockchain_hash_bytes} B</div>
                                                <div className="score-label">On-Chain</div>
                                            </div>
                                            <div className="score-item" style={{
                                                background: 'rgba(34, 197, 94, 0.1)',
                                                borderColor: 'rgba(34, 197, 94, 0.3)'
                                            }}>
                                                <div className="score-value" style={{
                                                    color: 'var(--success-light)',
                                                    WebkitTextFillColor: 'var(--success-light)'
                                                }}>
                                                    {result.data.data_reduction.reduction_raw_to_blockchain}
                                                </div>
                                                <div className="score-label">Reduction</div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Transaction Hash */}
                                {result.data.tx_hash && (
                                    <div style={{
                                        marginTop: '1rem',
                                        padding: '1rem',
                                        background: 'rgba(34, 197, 94, 0.08)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid rgba(34, 197, 94, 0.2)'
                                    }}>
                                        <div style={{
                                            fontSize: '0.65rem',
                                            color: 'var(--success-light)',
                                            marginBottom: '0.5rem',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>Blockchain Transaction</div>
                                        <p className="tx-hash">
                                            <a href={`https://sepolia.etherscan.io/tx/${result.data.tx_hash}`} target="_blank" rel="noopener noreferrer">
                                                {result.data.tx_hash}
                                            </a>
                                        </p>
                                    </div>
                                )}

                                {!result.data.tx_hash && (
                                    <div style={{
                                        marginTop: '1rem',
                                        padding: '1rem',
                                        background: 'rgba(245, 158, 11, 0.1)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid rgba(245, 158, 11, 0.3)',
                                        fontSize: '0.875rem',
                                        color: 'var(--warning-light)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem'
                                    }}>
                                        <span>⚠️</span>
                                        Blockchain not configured - identity stored on IPFS only
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span style={{ fontSize: '1.5rem' }}>❌</span>
                                <p style={{ margin: 0 }}>{result.error}</p>
                            </div>
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
