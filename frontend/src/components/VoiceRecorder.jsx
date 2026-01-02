import { useState, useRef, useEffect } from 'react'

/**
 * VoiceRecorder component for live audio capture
 * Uses browser MediaRecorder API with proper format handling
 */
function VoiceRecorder({ onCapture, onClose }) {
    const mediaRecorderRef = useRef(null)
    const audioChunksRef = useRef([])
    const streamRef = useRef(null)
    const [error, setError] = useState(null)
    const [isRecording, setIsRecording] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const [audioLevel, setAudioLevel] = useState(0)
    const analyserRef = useRef(null)
    const animationRef = useRef(null)
    const timerRef = useRef(null)
    const audioContextRef = useRef(null)

    useEffect(() => {
        return () => {
            cleanup()
        }
    }, [])

    const cleanup = () => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
        }
        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current)
        }
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => { })
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop())
        }
    }

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            })

            streamRef.current = stream

            // Set up audio analyser for visualization
            const audioContext = new (window.AudioContext || window.webkitAudioContext)()
            audioContextRef.current = audioContext
            const source = audioContext.createMediaStreamSource(stream)
            const analyser = audioContext.createAnalyser()
            analyser.fftSize = 256
            source.connect(analyser)
            analyserRef.current = analyser

            // Start visualization
            const updateLevel = () => {
                if (analyserRef.current) {
                    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
                    analyserRef.current.getByteFrequencyData(dataArray)
                    const average = dataArray.reduce((a, b) => a + b) / dataArray.length
                    setAudioLevel(average / 255)
                }
                animationRef.current = requestAnimationFrame(updateLevel)
            }
            updateLevel()

            // Determine best supported format
            let mimeType = 'audio/webm'
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                mimeType = 'audio/webm;codecs=opus'
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                mimeType = 'audio/mp4'
            } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
                mimeType = 'audio/ogg'
            }

            // Create MediaRecorder
            const mediaRecorder = new MediaRecorder(stream, { mimeType })

            audioChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

            mediaRecorder.onstop = async () => {
                try {
                    const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })

                    // Convert to WAV for backend compatibility
                    const wavBlob = await convertToWav(audioBlob)
                    const file = new File([wavBlob], 'recording.wav', { type: 'audio/wav' })
                    onCapture(file)
                } catch (err) {
                    console.error('Audio processing error:', err)
                    // If WAV conversion fails, send original format
                    const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
                    const ext = mimeType.includes('webm') ? 'webm' : 'mp4'
                    const file = new File([audioBlob], `recording.${ext}`, { type: mimeType })
                    onCapture(file)
                }
            }

            mediaRecorderRef.current = mediaRecorder
            mediaRecorder.start(100) // Collect data every 100ms
            setIsRecording(true)
            setRecordingTime(0)

            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1)
            }, 1000)

            // Auto-stop after 10 seconds
            setTimeout(() => {
                if (mediaRecorderRef.current?.state === 'recording') {
                    stopRecording()
                }
            }, 10000)

        } catch (err) {
            console.error('Microphone error:', err)
            setError('Unable to access microphone. Please allow audio permissions.')
        }
    }

    const stopRecording = () => {
        if (mediaRecorderRef.current?.state === 'recording') {
            mediaRecorderRef.current.stop()
        }
        if (timerRef.current) {
            clearInterval(timerRef.current)
        }
        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current)
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop())
        }
        setIsRecording(false)
        setAudioLevel(0)
    }

    // Convert audio blob to WAV format
    const convertToWav = async (audioBlob) => {
        return new Promise(async (resolve, reject) => {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 16000
                })

                const arrayBuffer = await audioBlob.arrayBuffer()
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)

                // Convert to WAV
                const wavBuffer = audioBufferToWav(audioBuffer)
                resolve(new Blob([wavBuffer], { type: 'audio/wav' }))

                audioContext.close()
            } catch (err) {
                reject(err)
            }
        })
    }

    // Audio buffer to WAV conversion
    const audioBufferToWav = (buffer) => {
        const numChannels = 1
        const sampleRate = buffer.sampleRate
        const format = 1 // PCM
        const bitDepth = 16

        // Get mono channel data
        let data
        if (buffer.numberOfChannels > 1) {
            // Mix down to mono
            const left = buffer.getChannelData(0)
            const right = buffer.getChannelData(1)
            data = new Float32Array(left.length)
            for (let i = 0; i < left.length; i++) {
                data[i] = (left[i] + right[i]) / 2
            }
        } else {
            data = buffer.getChannelData(0)
        }

        const length = data.length * 2
        const arrayBuffer = new ArrayBuffer(44 + length)
        const view = new DataView(arrayBuffer)

        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i))
            }
        }

        writeString(0, 'RIFF')
        view.setUint32(4, 36 + length, true)
        writeString(8, 'WAVE')
        writeString(12, 'fmt ')
        view.setUint32(16, 16, true)
        view.setUint16(20, format, true)
        view.setUint16(22, numChannels, true)
        view.setUint32(24, sampleRate, true)
        view.setUint32(28, sampleRate * numChannels * bitDepth / 8, true)
        view.setUint16(32, numChannels * bitDepth / 8, true)
        view.setUint16(34, bitDepth, true)
        writeString(36, 'data')
        view.setUint32(40, length, true)

        // Audio data
        let offset = 44
        for (let i = 0; i < data.length; i++) {
            const sample = Math.max(-1, Math.min(1, data[i]))
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
            offset += 2
        }

        return arrayBuffer
    }

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const handleClose = () => {
        cleanup()
        onClose()
    }

    if (error) {
        return (
            <div className="webcam-modal">
                <div className="webcam-container">
                    <div className="webcam-error">
                        <p>🎤 {error}</p>
                        <button className="btn btn-secondary" onClick={handleClose}>Close</button>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="webcam-modal">
            <div className="webcam-container" style={{ maxWidth: '400px' }}>
                <div className="webcam-header">
                    <h3>🎤 Voice Recording</h3>
                    <button className="webcam-close" onClick={handleClose}>✕</button>
                </div>

                <div className="voice-recorder-display">
                    <div className="voice-visualizer">
                        <div
                            className="voice-level-bar"
                            style={{ transform: `scaleY(${0.2 + audioLevel * 0.8})` }}
                        />
                    </div>
                    <div className="voice-timer">
                        {formatTime(recordingTime)}
                    </div>
                    {isRecording && (
                        <div className="voice-recording-indicator">
                            <span className="recording-dot"></span>
                            Recording... (max 10s)
                        </div>
                    )}
                </div>

                <div className="webcam-guide">
                    <p>Speak clearly for 3-10 seconds</p>
                </div>

                <div className="webcam-actions">
                    {!isRecording ? (
                        <button
                            className="btn btn-primary btn-full"
                            onClick={startRecording}
                        >
                            🎤 Start Recording
                        </button>
                    ) : (
                        <button
                            className="btn btn-full"
                            onClick={stopRecording}
                            style={{ background: 'var(--error)', color: 'white' }}
                        >
                            ⏹ Stop Recording ({10 - recordingTime}s left)
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default VoiceRecorder
