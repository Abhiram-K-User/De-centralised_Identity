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

        // Accept more audio formats for better browser compatibility
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

        // Validate all fields
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
            <div className="page-header">
                <h1 className="page-title">Register Identity</h1>
                <p className="page-subtitle">Create your decentralized biometric identity</p>
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
                            <div className="file-upload-hint">JPEG only, max 10MB</div>
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
                            <div className="file-upload-hint">Audio file, max 10MB</div>
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
                            <div className="file-upload-hint">JPEG only, max 10MB</div>
                        </div>
                        {errors.idDoc && <p className="status status-error" style={{ marginTop: '0.5rem', padding: '0.5rem' }}>{errors.idDoc}</p>}
                    </div>

                    {uploading && (
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                <span>Uploading & Processing...</span>
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
                                Processing Biometrics...
                            </>
                        ) : (
                            'Register Identity'
                        )}
                    </button>
                </form>

                {result && (
                    <div className={`status ${result.success ? 'status-success' : 'status-error'}`}>
                        {result.success ? (
                            <div>
                                <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>✓ Registration Successful!</p>
                                <p style={{ marginBottom: '0.5rem' }}>Your DID:</p>
                                <div className="did-display">{result.data.did}</div>
                                {result.data.tx_hash && (
                                    <div style={{ marginTop: '1rem' }}>
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

export default RegisterPage
