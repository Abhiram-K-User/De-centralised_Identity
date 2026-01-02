import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * WebcamCapture component for live image capture
 * Uses browser MediaDevices API to access webcam
 */
function WebcamCapture({ onCapture, onClose }) {
    const videoRef = useRef(null)
    const canvasRef = useRef(null)
    const [stream, setStream] = useState(null)
    const [error, setError] = useState(null)
    const [isReady, setIsReady] = useState(false)
    const [countdown, setCountdown] = useState(null)

    // Start webcam on mount
    useEffect(() => {
        startWebcam()
        return () => stopWebcam()
    }, [])

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
                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                </div>

                <div className="webcam-guide">
                    <p>Position your face in the center of the frame</p>
                </div>

                <div className="webcam-actions">
                    <button
                        className="btn btn-primary btn-full"
                        onClick={handleCapture}
                        disabled={!isReady || countdown !== null}
                    >
                        {countdown !== null ? `Capturing in ${countdown}...` : '📷 Capture Photo'}
                    </button>
                </div>
            </div>
        </div>
    )
}

export default WebcamCapture
