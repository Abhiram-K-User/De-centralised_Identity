import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * WebcamCapture component for live image capture
 * Uses browser MediaDevices API to access webcam
 * Includes real-time brightness detection with user recommendations
 */
function WebcamCapture({ onCapture, onClose }) {
    const videoRef = useRef(null)
    const canvasRef = useRef(null)
    const brightnessCanvasRef = useRef(null)
    const brightnessIntervalRef = useRef(null)

    const [stream, setStream] = useState(null)
    const [error, setError] = useState(null)
    const [isReady, setIsReady] = useState(false)
    const [countdown, setCountdown] = useState(null)

    // Brightness detection state
    const [brightness, setBrightness] = useState(50)
    const [brightnessStatus, setBrightnessStatus] = useState('good') // 'good' | 'warning' | 'critical'

    // Brightness thresholds
    const BRIGHTNESS_GOOD = 40
    const BRIGHTNESS_WARNING = 25

    /**
     * Calculate average brightness from video frame
     * Uses luminance formula: 0.299*R + 0.587*G + 0.114*B
     * Samples pixels for performance (every 10th pixel)
     */
    const calculateBrightness = useCallback(() => {
        if (!videoRef.current || !brightnessCanvasRef.current || !isReady) return

        const video = videoRef.current
        const canvas = brightnessCanvasRef.current
        const context = canvas.getContext('2d', { willReadFrequently: true })

        // Use smaller canvas for performance
        const sampleWidth = 160
        const sampleHeight = 90
        canvas.width = sampleWidth
        canvas.height = sampleHeight

        try {
            // Draw scaled down video frame
            context.drawImage(video, 0, 0, sampleWidth, sampleHeight)

            // Get pixel data
            const imageData = context.getImageData(0, 0, sampleWidth, sampleHeight)
            const pixels = imageData.data

            let totalLuminance = 0
            let pixelCount = 0

            // Sample every 4th pixel for speed
            for (let i = 0; i < pixels.length; i += 16) {
                const r = pixels[i]
                const g = pixels[i + 1]
                const b = pixels[i + 2]

                // Calculate luminance using standard formula
                const luminance = 0.299 * r + 0.587 * g + 0.114 * b
                totalLuminance += luminance
                pixelCount++
            }

            // Convert to 0-100 scale (255 max luminance)
            const avgLuminance = totalLuminance / pixelCount
            const brightnessPercent = Math.round((avgLuminance / 255) * 100)

            setBrightness(brightnessPercent)

            // Determine status
            if (brightnessPercent >= BRIGHTNESS_GOOD) {
                setBrightnessStatus('good')
            } else if (brightnessPercent >= BRIGHTNESS_WARNING) {
                setBrightnessStatus('warning')
            } else {
                setBrightnessStatus('critical')
            }
        } catch (err) {
            console.warn('Brightness calculation error:', err)
        }
    }, [isReady])

    // Start webcam on mount
    useEffect(() => {
        startWebcam()
        return () => stopWebcam()
    }, [])

    // Start brightness monitoring when video is ready
    useEffect(() => {
        if (isReady) {
            // Calculate brightness every 200ms
            brightnessIntervalRef.current = setInterval(calculateBrightness, 200)
        }

        return () => {
            if (brightnessIntervalRef.current) {
                clearInterval(brightnessIntervalRef.current)
            }
        }
    }, [isReady, calculateBrightness])

    const startWebcam = async () => {
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            })

            setStream(mediaStream)

            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream
                videoRef.current.onloadedmetadata = () => {
                    videoRef.current.play()
                    setIsReady(true)
                }
            }
        } catch (err) {
            console.error('Webcam error:', err)
            setError('Unable to access webcam. Please allow camera permissions.')
        }
    }

    const stopWebcam = () => {
        if (brightnessIntervalRef.current) {
            clearInterval(brightnessIntervalRef.current)
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop())
            setStream(null)
        }
    }

    const captureImage = useCallback(() => {
        if (!videoRef.current || !canvasRef.current || !isReady) return

        const video = videoRef.current
        const canvas = canvasRef.current
        const context = canvas.getContext('2d')

        // Set canvas size to video size
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight

        // Draw video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height)

        // Convert to blob (JPEG)
        canvas.toBlob((blob) => {
            if (blob) {
                // Create File object
                const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' })
                onCapture(file)
                stopWebcam()
            }
        }, 'image/jpeg', 0.95)
    }, [isReady, onCapture])

    const handleCapture = () => {
        // 3-second countdown
        setCountdown(3)
        let count = 3
        const interval = setInterval(() => {
            count--
            if (count === 0) {
                clearInterval(interval)
                setCountdown(null)
                captureImage()
            } else {
                setCountdown(count)
            }
        }, 1000)
    }

    // Get brightness indicator color
    const getBrightnessColor = () => {
        switch (brightnessStatus) {
            case 'good': return 'var(--success)'
            case 'warning': return 'var(--warning)'
            case 'critical': return 'var(--error)'
            default: return 'var(--text-muted)'
        }
    }

    // Get brightness status message
    const getBrightnessMessage = () => {
        switch (brightnessStatus) {
            case 'good':
                return { icon: '✓', text: 'Lighting: Good' }
            case 'warning':
                return { icon: '⚠️', text: 'Low light - consider moving to a brighter area' }
            case 'critical':
                return { icon: '❌', text: 'Too dark - please move to a brighter area' }
            default:
                return { icon: '◯', text: 'Checking lighting...' }
        }
    }

    const brightnessMessage = getBrightnessMessage()
    const canCapture = isReady && countdown === null && brightnessStatus !== 'critical'

    if (error) {
        return (
            <div className="webcam-modal">
                <div className="webcam-container">
                    <div className="webcam-error">
                        <p>📷 {error}</p>
                        <button className="btn btn-secondary" onClick={onClose}>Close</button>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="webcam-modal">
            <div className="webcam-container">
                <div className="webcam-header">
                    <h3>📸 Live Face Capture</h3>
                    <button className="webcam-close" onClick={() => { stopWebcam(); onClose(); }}>✕</button>
                </div>

                <div className="webcam-video-wrapper">
                    <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        muted
                        className="webcam-video"
                    />
                    {countdown && (
                        <div className="webcam-countdown">
                            {countdown}
                        </div>
                    )}
                    {/* Hidden canvases for image capture and brightness calculation */}
                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                    <canvas ref={brightnessCanvasRef} style={{ display: 'none' }} />
                </div>

                {/* Brightness Indicator */}
                <div className="brightness-indicator">
                    <div className="brightness-header">
                        <span className="brightness-icon" style={{ color: getBrightnessColor() }}>
                            {brightnessMessage.icon}
                        </span>
                        <span
                            className="brightness-text"
                            style={{ color: getBrightnessColor() }}
                        >
                            {brightnessMessage.text}
                        </span>
                    </div>
                    <div className="brightness-meter">
                        <div
                            className="brightness-bar"
                            style={{
                                width: `${brightness}%`,
                                background: getBrightnessColor()
                            }}
                        />
                        <div className="brightness-thresholds">
                            <div
                                className="brightness-threshold critical"
                                style={{ left: `${BRIGHTNESS_WARNING}%` }}
                            />
                            <div
                                className="brightness-threshold warning"
                                style={{ left: `${BRIGHTNESS_GOOD}%` }}
                            />
                        </div>
                    </div>
                    <div className="brightness-labels">
                        <span>Dark</span>
                        <span>Bright</span>
                    </div>
                </div>

                <div className="webcam-guide">
                    <p>Position your face in the center of the frame</p>
                </div>

                <div className="webcam-actions">
                    <button
                        className="btn btn-primary btn-full"
                        onClick={handleCapture}
                        disabled={!canCapture}
                    >
                        {countdown !== null
                            ? `Capturing in ${countdown}...`
                            : brightnessStatus === 'critical'
                                ? '💡 Improve Lighting to Capture'
                                : '📷 Capture Photo'
                        }
                    </button>
                </div>
            </div>
        </div>
    )
}

export default WebcamCapture
